"""
نسخة واحدة فقط من البرنامج: كل نسخة تحمّل النموذج في الذاكرة (قرابة 1.5 جيجابايت)،
فلو فُتح ملف والبرنامج مفتوح بالفعل، تُرسل النسخة الجديدة الملف للنسخة المفتوحة ثم تُغلق.
التواصل عبر ملفات صغيرة في مجلد "inbox" تقرؤها النسخة المفتوحة كل أقل من ثانية.
"""
import json
import os
import time
import uuid

from core.paths import DATA_DIR, ensure_dir

INBOX_DIR = os.path.join(DATA_DIR, "inbox")
# طلبات أقدم من هذا تُهمل (مثلاً من نسخة انتهت قبل أن تُقرأ رسالتها)
MAX_REQUEST_AGE = 60


def send_request(paths):
    """ترسلها النسخة الجديدة: الملفات المطلوب فتحها (أو قائمة فارغة لإظهار النافذة فقط)"""
    if not ensure_dir(INBOX_DIR):
        return False
    target = os.path.join(INBOX_DIR, f"{time.time():.3f}-{uuid.uuid4().hex}.json")
    tmp = target + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"paths": [os.path.abspath(p) for p in paths], "time": time.time()}, f, ensure_ascii=False)
        os.replace(tmp, target)
        return True
    except OSError:
        return False


def take_requests():
    """تقرؤها النسخة المفتوحة: كل الطلبات الجديدة بالترتيب، مع حذفها بعد القراءة"""
    if not os.path.isdir(INBOX_DIR):
        return []
    requests = []
    for name in sorted(os.listdir(INBOX_DIR)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(INBOX_DIR, name)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            os.remove(path)
        except (OSError, ValueError):
            continue
        if time.time() - data.get("time", 0) <= MAX_REQUEST_AGE:
            requests.append(data.get("paths", []))
    return requests


def clear_inbox():
    """عند بدء النسخة الأساسية: حذف طلبات قديمة متبقية من تشغيل سابق"""
    take_requests()
