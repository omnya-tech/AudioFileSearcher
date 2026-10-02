"""
قواميس المجالات: لكل نوع تسجيلات قاموسه (قرآن، محاضرات، اجتماعات...)، حتى لا يفسد تصحيحُ مجالٍ مجالاً آخر
(مثلاً «الظالم ← الضالين» صحيح في الفاتحة وخطأ في محاضرة عن الظلم).

كل قاموس فيه:
  - corrections: تصحيحات «كلمة خطأ ← كلمة صحيحة» تُطبَّق على النص بعد التفريغ.
  - terms: مصطلحات وأسماء صحيحة فقط (بدون معرفة الخطأ)، تُعطى للنموذج كتلميح فيكتبها صحيحة من البداية.

يُحفظ في الإعدادات: "dictionaries" = {الاسم: {"corrections": {...}, "terms": [...]}}, و"active_dictionary" = الاسم.
"""
import csv
import json
import os

FILE_FORMAT = "media-searcher-dictionary"
# ملفات صدّرتها الإصدارات السابقة تُستورد كما هي
LEGACY_FILE_FORMATS = ("audio-file-searcher-dictionary", "audio-transcriber-dictionary")
FILE_VERSION = 1
DEFAULT_NAMES = {"ar": "عام", "en": "General"}


def empty():
    return {"corrections": {}, "terms": []}


def _normalize(profile):
    """قاموس سليم الشكل مهما كان مصدره (ملف مستورد أو إعدادات قديمة)"""
    corrections = {str(k).strip(): str(v).strip() for k, v in dict((profile or {}).get("corrections", {}) or {}).items()
                   if str(k).strip() and str(v).strip() and str(k).strip() != str(v).strip()}
    terms = list(dict.fromkeys(str(t).strip() for t in (profile or {}).get("terms", []) or [] if str(t).strip()))
    return {"corrections": corrections, "terms": terms}


def ensure(settings):
    """
    التأكد من وجود قاموس واحد على الأقل. الإعدادات القديمة (قاموس واحد "custom_dictionary")
    تُنقل تلقائياً لقاموس اسمه "عام" بدون أن يضيع منها شيء.
    """
    profiles = settings.get("dictionaries")
    if isinstance(profiles, dict) and profiles:
        if settings.get("active_dictionary") not in profiles:
            settings.set("active_dictionary", next(iter(profiles)))
        return
    name = DEFAULT_NAMES.get(settings.get("language", "ar"), DEFAULT_NAMES["ar"])
    legacy = settings.get("custom_dictionary", {}) or {}
    settings.update({"dictionaries": {name: _normalize({"corrections": legacy})}, "active_dictionary": name})


def all_profiles(settings):
    ensure(settings)
    return {name: _normalize(p) for name, p in settings.get("dictionaries").items()}


def names(settings):
    return list(all_profiles(settings))


def active_name(settings):
    ensure(settings)
    return settings.get("active_dictionary")


def set_active(settings, name):
    if name in all_profiles(settings):
        settings.set("active_dictionary", name)


def get(settings, name=None):
    return all_profiles(settings).get(name or active_name(settings), empty())


def save_all(settings, profiles, active=None):
    """حفظ كل القواميس مرة واحدة (من نافذة إدارة القواميس)"""
    profiles = {name: _normalize(p) for name, p in profiles.items() if name.strip()}
    if not profiles:
        profiles = {DEFAULT_NAMES["ar"]: empty()}
    active = active if active in profiles else next(iter(profiles))
    settings.update({"dictionaries": profiles, "active_dictionary": active})


def active_corrections(settings):
    return dict(get(settings)["corrections"])


def active_terms(settings):
    return list(get(settings)["terms"])


def add_corrections(settings, pairs, name=None):
    """إضافة تصحيحات (مثلاً مما تعلّمه البرنامج من تعديلات المستخدم) للقاموس النشط"""
    profiles = all_profiles(settings)
    name = name or active_name(settings)
    profile = profiles.setdefault(name, empty())
    for wrong, right in pairs:
        profile["corrections"][wrong] = right
    save_all(settings, profiles, active_name(settings))


def merge(base, extra):
    """دمج قاموس مستورد في قاموس موجود: تصحيحات المستورد تغلب عند التعارض، والمصطلحات بلا تكرار"""
    base, extra = _normalize(base), _normalize(extra)
    corrections = dict(base["corrections"]); corrections.update(extra["corrections"])
    return {"corrections": corrections, "terms": list(dict.fromkeys(base["terms"] + extra["terms"]))}


# ------------------------------------------------------------------ الاستيراد والتصدير
def export_file(path, name, profile):
    """ملف JSON واحد فيه التصحيحات والمصطلحات، يمكن مشاركته أو نقله لجهاز آخر"""
    data = {"format": FILE_FORMAT, "version": FILE_VERSION, "name": name, **_normalize(profile)}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def import_file(path):
    """
    قراءة قاموس من ملف. ترجع (الاسم المقترح، القاموس). الصيغ المقبولة:
      - .json: ملف صدّره البرنامج (أو قاموس بسيط {"خطأ": "صحيح"}).
      - .csv: عمودان (خطأ، صحيح) = تصحيحات، أو عمود واحد = مصطلحات.
      - .txt: كل سطر مصطلح، أو تصحيح بالشكل "خطأ ← صحيح" (أو = أو -> أو =>).
    ValueError لو الملف غير صالح.
    """
    name = os.path.splitext(os.path.basename(path))[0]
    ext = os.path.splitext(path)[1].lower()
    profile = empty()
    with open(path, encoding="utf-8-sig") as f:
        if ext == ".json":
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("unsupported JSON")
            if data.get("format") in (FILE_FORMAT,) + LEGACY_FILE_FORMATS:
                name = data.get("name") or name
                profile = data
            else:
                profile = {"corrections": data}
        elif ext == ".csv":
            for row in csv.reader(f):
                cells = [c.strip() for c in row if c.strip()]
                if len(cells) >= 2:
                    profile["corrections"][cells[0]] = cells[1]
                elif len(cells) == 1:
                    profile["terms"].append(cells[0])
        else:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # الخطأ أولاً دائماً، بنفس طريقة عرض البرنامج: «سراط» ← «صراط»
                for sep in ("=>", "->", "←", "→", "=", "\t"):
                    if sep in line:
                        wrong, right = (p.strip() for p in line.split(sep, 1))
                        if wrong and right:
                            profile["corrections"][wrong] = right
                        break
                else:
                    profile["terms"].append(line)
    profile = _normalize(profile)
    if not profile["corrections"] and not profile["terms"]:
        raise ValueError("empty dictionary file")
    return name, profile
