"""
مسارات البرنامج في مكان واحد.
- APP_DIR: مجلد البرنامج نفسه (قد يكون للقراءة فقط، مثل Program Files).
- RESOURCE_DIR: الملفات المضمَّنة مع البرنامج (ملفات اللغة). في نسخة exe هي مجلد _internal.
- DATA_DIR: مكان الإعدادات والقواميس والسجلات والنماذج المحمّلة.
  في النسخة المثبتة (exe): دائماً في مجلد المستخدم %APPDATA%\\MediaSearcher، والبرنامج نفسه في Program Files.
  عند التشغيل من الكود: بجانب الكود لو كان المجلد قابلاً للكتابة، وإلا في مجلد المستخدم.
"""
import os
import sys
import tempfile

APP_NAME = "MediaSearcher"
# الأسماء التقنية السابقة، الأحدث أولاً (تُنقل بياناتها للاسم الحالي تلقائياً)
LEGACY_APP_NAMES = ("AudioFileSearcher", "AudioTranscriber")
# بيانات البرنامج التي تُنقل من مجلد التثبيت القديم (الإصدارات التي كانت تُثبَّت للمستخدم وتحفظ بياناتها بجانبها)
DATA_ITEMS = ("config.json", "learning.json", "models", "logs", "recovery")

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


def _old_install_dirs():
    """مجلدات التثبيت للمستخدم في الإصدارات السابقة (%LOCALAPPDATA%\\Programs\\<الاسم>)"""
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        return []
    return [os.path.join(base, "Programs", name) for name in (APP_NAME,) + LEGACY_APP_NAMES]


def _move_old_install_data(path):
    """
    نقل بيانات التثبيت القديم (بجانب البرنامج) إلى مجلد المستخدم. كل عنصر يُنقل مرة واحدة ولا يُستبدل
    عنصر موجود، فلو انقطع النقل في المنتصف يكمل في التشغيل التالي.
    """
    for old in _old_install_dirs():
        for item in DATA_ITEMS:
            _move_missing(os.path.join(old, item), os.path.join(path, item))


def _move_missing(source, target):
    """
    نقل ملف أو مجلد إن لم يكن موجوداً في الهدف. المجلد الموجود في الهدف (مثل models) يُدمج محتوى بمحتوى،
    حتى لا يبقى نموذج قديم مختبئاً في مجلد التثبيت القديم لأن مجلد النماذج الجديد أُنشئ قبله.
    """
    import shutil
    if not os.path.exists(source):
        return
    try:
        if not os.path.exists(target):
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.move(source, target)
        elif os.path.isdir(source) and os.path.isdir(target):
            for name in os.listdir(source):
                _move_missing(os.path.join(source, name), os.path.join(target, name))
            try:
                os.rmdir(source)  # يُحذف فقط لو فرغ
            except OSError:
                pass
    except OSError:
        pass


def _user_data_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    # بيانات الإصدارات السابقة (بأحد الأسماء القديمة) تُنقل مرة واحدة، وإن تعذر النقل نستخدمها في مكانها
    for name in LEGACY_APP_NAMES:
        legacy = os.path.join(base, name)
        if not os.path.exists(path) and os.path.isdir(legacy):
            try:
                os.rename(legacy, path)
            except OSError:
                return legacy
    _move_old_install_data(path)
    return path


# متغير البيئة يسمح بتشغيل البرنامج ببيانات منفصلة (للتجربة والاختبارات) دون لمس إعدادات المستخدم
DATA_DIR = (os.environ.get("MEDIA_SEARCHER_DATA_DIR")
            or (_user_data_dir() if getattr(sys, "frozen", False)
                else APP_DIR if is_writable_dir(APP_DIR) else _user_data_dir()))

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
