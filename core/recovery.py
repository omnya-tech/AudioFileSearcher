"""
حفظ التقدم أثناء التفريغ حتى لا يضيع الشغل.
لكل ملف صوتي ملف استرجاع فيه المقاطع التي تم تفريغها وآخر ثانية وصل لها،
فلو أُلغي التفريغ أو أُغلق البرنامج أو توقف الجهاز يمكن الاستكمال من نفس النقطة.
"""
import hashlib
import json
import os
import time

from core.paths import RECOVERY_DIR, ensure_dir

VERSION = 1


def _path_for(audio_path):
    key = hashlib.md5(os.path.normcase(os.path.abspath(audio_path)).encode("utf-8")).hexdigest()
    return os.path.join(RECOVERY_DIR, f"{key}.json")


def _fingerprint(audio_path):
    """الحجم وتاريخ التعديل: لو تغيّر الملف الصوتي لا نستكمل تفريغاً قديماً لا يطابقه"""
    st = os.stat(audio_path)
    return {"size": st.st_size, "mtime": int(st.st_mtime)}


def save(audio_path, segments, duration):
    """حفظ ذري (ملف مؤقت ثم استبدال) حتى لا يتلف ملف الاسترجاع لو انقطع الحفظ في منتصفه"""
    if not segments or not ensure_dir(RECOVERY_DIR):
        return False
    data = {
        "version": VERSION,
        "audio_path": os.path.abspath(audio_path),
        "fingerprint": _fingerprint(audio_path),
        "duration": duration,
        "last_end": segments[-1][3],
        "saved_at": time.time(),
        "segments": [list(s) for s in segments],
    }
    target = _path_for(audio_path)
    tmp = target + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, target)
        return True
    except OSError:
        return False


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("version") != VERSION or not data.get("segments"):
            return None
        audio = data["audio_path"]
        if not os.path.isfile(audio) or _fingerprint(audio) != data.get("fingerprint"):
            return None
        data["segments"] = [tuple(s) for s in data["segments"]]
        return data
    except (OSError, ValueError, KeyError, TypeError):
        return None


def load(audio_path):
    """التقدم المحفوظ لهذا الملف، أو None لو لا يوجد أو لم يعد صالحاً"""
    if not os.path.isfile(audio_path):
        return None
    return _read(_path_for(audio_path))


def delete(audio_path):
    try:
        os.remove(_path_for(audio_path))
    except OSError:
        pass


def list_pending():
    """كل التفريغات غير المكتملة التي ما زال ملفها الصوتي موجوداً، الأحدث أولاً"""
    if not os.path.isdir(RECOVERY_DIR):
        return []
    pending = []
    for name in os.listdir(RECOVERY_DIR):
        if name.endswith(".json"):
            data = _read(os.path.join(RECOVERY_DIR, name))
            if data:
                pending.append(data)
    return sorted(pending, key=lambda d: d.get("saved_at", 0), reverse=True)
