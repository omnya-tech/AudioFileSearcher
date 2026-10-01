"""
التعلم من تصحيحات المستخدم.

عندما يعدّل المستخدم نص جملة، نقارن النص القديم بالجديد كلمة بكلمة لنستخرج ما صحّحه
(مثل «سراط» ← «صراط»). هذه التصحيحات:
  1) تُضاف للقاموس المخصص فتُصحَّح تلقائياً في كل تفريغ قادم،
  2) وتُعطى للنموذج كتلميحات أثناء التفريغ (hotwords) فيصبح أميل لكتابتها صحيحة من البداية،
  3) وتُحفظ مع موضعها في الملف الصوتي كبيانات تدريب، لو أراد المستخدم يوماً إعادة تدريب النموذج نفسه.
"""
import difflib
import json
import os
import re
import time

from core.paths import DATA_DIR, ensure_dir

LEARNING_FILE = os.path.join(DATA_DIR, "learning.json")
# أقصى عدد كلمات في طرف التصحيح الواحد: تعديل أطول من ذلك إعادة صياغة وليس تصحيح كلمة
MAX_PHRASE_WORDS = 3
# أقصى عدد للتلميحات التي تُعطى للنموذج (النموذج يقبل عدداً محدوداً من الكلمات في التلميح)
MAX_HOTWORDS = 40

_PUNCT = re.compile(r"^[\s.,،؛;:!?؟\"'«»()\[\]{}…\-]+|[\s.,،؛;:!?؟\"'«»()\[\]{}…\-]+$")


def _clean(word):
    """الكلمة بدون علامات الترقيم في أولها وآخرها (تغيير الترقيم وحده ليس تصحيحاً لكلمة)"""
    return _PUNCT.sub("", word)


def extract_corrections(original, edited):
    """
    التصحيحات بين نصين: قائمة (الخطأ، الصحيح). نقارن الكلمات بالترتيب ونأخذ فقط الاستبدالات القصيرة،
    ونتجاهل الإضافة والحذف وتغيير الترقيم وإعادة الصياغة الطويلة.
    """
    a = [_clean(w) for w in (original or "").split()]
    b = [_clean(w) for w in (edited or "").split()]
    pairs = []
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op != "replace":
            continue
        if (i2 - i1) == (j2 - j1):
            # نفس عدد الكلمات: كل كلمة تصحيح مستقل (أعم من تصحيح العبارة كاملة)
            pairs += [(w, r) for w, r in zip(a[i1:i2], b[j1:j2]) if w and r and w != r]
            continue
        wrong = " ".join(w for w in a[i1:i2] if w)
        right = " ".join(w for w in b[j1:j2] if w)
        if not wrong or not right or wrong == right:
            continue
        if (i2 - i1) > MAX_PHRASE_WORDS or (j2 - j1) > MAX_PHRASE_WORDS:
            continue
        pairs.append((wrong, right))
    return pairs


class LearningStore:
    """ما تعلّمه البرنامج: كل تصحيح وعدد مرات تكراره، وأمثلة التدريب (موضع الجملة في الصوت + النص قبل وبعد)"""

    def __init__(self, path=None):
        self.path = path or LEARNING_FILE
        self.data = {"corrections": {}, "samples": []}
        self._load()

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self.data["corrections"] = dict(data.get("corrections", {}))
                self.data["samples"] = list(data.get("samples", []))
        except (OSError, ValueError):
            pass

    def save(self):
        if not ensure_dir(os.path.dirname(self.path)):
            return
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def record_edit(self, audio_path, start, end, original, edited):
        """تسجيل تعديل واحد. ترجع التصحيحات المستخرجة منه (قد تكون فارغة)"""
        self.data["samples"].append({
            "audio": os.path.abspath(audio_path) if audio_path else "",
            "start": round(float(start), 3), "end": round(float(end), 3),
            "original": original, "corrected": edited, "time": int(time.time()),
        })
        pairs = extract_corrections(original, edited)
        for wrong, right in pairs:
            key = f"{wrong}→{right}"
            entry = self.data["corrections"].setdefault(key, {"wrong": wrong, "right": right, "count": 0})
            entry["count"] += 1
            entry["last"] = int(time.time())
        self.save()
        return pairs

    def count(self, wrong, right):
        return self.data["corrections"].get(f"{wrong}→{right}", {}).get("count", 0)

    def corrections(self):
        """كل التصحيحات المتعلَّمة، الأكثر تكراراً ثم الأحدث أولاً"""
        return sorted(self.data["corrections"].values(), key=lambda e: (e.get("count", 0), e.get("last", 0)), reverse=True)

    def samples(self):
        return list(self.data["samples"])

    def forget(self, wrong):
        """عند حذف كلمة من القاموس: ننسى تصحيحاتها أيضاً"""
        self.data["corrections"] = {k: v for k, v in self.data["corrections"].items() if v.get("wrong") != wrong}
        self.save()


def hotwords_for_model(dictionary, store=None, limit=MAX_HOTWORDS, terms=None):
    """
    الكلمات الصحيحة التي تُعطى للنموذج كتلميح أثناء التفريغ: المصطلحات والأسماء التي كتبها المستخدم أولاً،
    ثم الأكثر تصحيحاً، ثم باقي القاموس، بلا تكرار، وبحد أقصى (النموذج يقبل تلميحاً محدود الطول ويقص الزائد).
    """
    ordered = list(terms or [])
    if store is not None:
        ordered += [e["right"] for e in store.corrections() if e.get("right") in (dictionary or {}).values()]
    ordered += list((dictionary or {}).values())
    unique = list(dict.fromkeys(w.strip() for w in ordered if w and w.strip()))
    return ", ".join(unique[:limit]) if unique else None


def export_dataset(samples, out_dir):
    """
    تصدير أمثلة التدريب بالصيغة المعتادة لإعادة تدريب نماذج Whisper (مجلد صوت + metadata.csv):
    لكل تصحيح: مقطع الصوت نفسه (wav) والنص الصحيح. ترجع (عدد المصدَّر، عدد المتخطَّى لأن ملفه الصوتي غير موجود)
    """
    import csv
    import wave
    import numpy as np
    from faster_whisper.audio import decode_audio

    rate = 16000
    os.makedirs(out_dir, exist_ok=True)
    decoded, exported, skipped = {}, 0, 0
    rows = []
    for sample in samples:
        audio = sample.get("audio")
        if not audio or not os.path.isfile(audio):
            skipped += 1
            continue
        if audio not in decoded:
            decoded[audio] = decode_audio(audio, sampling_rate=rate)
        pcm = decoded[audio][int(sample["start"] * rate):int(sample["end"] * rate)]
        if len(pcm) == 0:
            skipped += 1
            continue
        exported += 1
        name = f"clip_{exported:05d}.wav"
        with wave.open(os.path.join(out_dir, name), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
            w.writeframes((np.clip(pcm, -1, 1) * 32767).astype(np.int16).tobytes())
        rows.append({"file_name": name, "transcription": sample["corrected"], "original": sample["original"]})
    with open(os.path.join(out_dir, "metadata.csv"), "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["file_name", "transcription", "original"])
        writer.writeheader()
        writer.writerows(rows)
    return exported, skipped
