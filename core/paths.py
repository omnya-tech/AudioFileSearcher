"""
مسارات البرنامج في مكان واحد.
- APP_DIR: مجلد البرنامج نفسه (قد يكون للقراءة فقط، مثل Program Files).
- RESOURCE_DIR: الملفات المضمَّنة مع البرنامج (ملفات اللغة). في نسخة exe هي مجلد _internal.
- DATA_DIR: مكان الإعدادات والسجلات والنماذج المحمّلة. يكون بجانب البرنامج لو المجلد قابل للكتابة
  (نسخة محمولة أو التشغيل من الكود)، وإلا في مجلد المستخدم: %APPDATA%\\AudioTranscriber.
"""
import os
import sys
import tempfile

APP_NAME = "AudioTranscriber"

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
    RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RESOURCE_DIR = APP_DIR


def is_writable_dir(path):
    """التجربة الفعلية أدق من os.access في ويندوز (الصلاحيات وحماية Program Files)"""
    try:
        os.makedirs(path, exist_ok=True)
        fd, probe = tempfile.mkstemp(prefix=".write_test_", dir=path)
        os.close(fd)
        os.remove(probe)
        return True
    except OSError:
        return False


def _user_data_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME)


DATA_DIR = APP_DIR if is_writable_dir(APP_DIR) else _user_data_dir()

LOCALES_DIR = os.path.join(RESOURCE_DIR, "locales")
MODELS_DIR = os.path.join(DATA_DIR, "models")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
RECOVERY_DIR = os.path.join(DATA_DIR, "recovery")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# نماذج موضوعة يدوياً بجانب البرنامج (مثلاً نُسخت مع نسخة exe) تُستخدم حتى لو كانت البيانات في AppData
EXTRA_MODEL_DIRS = [d for d in (os.path.join(APP_DIR, "models"),) if os.path.normcase(d) != os.path.normcase(MODELS_DIR)]


def ensure_dir(path):
    """إنشاء مجلد بدون إيقاف البرنامج لو فشل الإنشاء. ترجع True لو المجلد موجود"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError:
        return False


def ensure_std_streams():
    """
    عند التشغيل بدون نافذة سوداء (exe أو pythonw) تكون sys.stdout و sys.stderr فارغة (None)،
    وأي مكتبة تطبع شيئاً (مثل شريط تقدم تحميل النموذج) تنهار. نوجّههما لملف في مجلد السجلات.
    """
    if sys.stdout is not None and sys.stderr is not None:
        return
    stream = None
    if ensure_dir(LOGS_DIR):
        try:
            stream = open(os.path.join(LOGS_DIR, "console.log"), "a", encoding="utf-8", buffering=1)
        except OSError:
            stream = None
    if stream is None:
        stream = open(os.devnull, "w", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream
