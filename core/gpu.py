"""
كرت الشاشة NVIDIA للتفريغ (CUDA).

محرّك التفريغ (CTranslate2 4.x) يحتاج على كرت NVIDIA مكتبتين من NVIDIA غير مضمّنتين مع البرنامج:
cuBLAS (CUDA 12) وcuDNN 9. وغيابهما لا يظهر عند تحميل النموذج دائماً، بل قد يُغلق البرنامج فجأة عند أول تفريغ،
فنتأكد من وجودهما قبل اختيار الكرت، ونرجع للمعالج إن لم يكن الكرت جاهزاً.
"""
import ctypes

# أسماء ملفات المكتبات على ويندوز للإصدارات التي يحتاجها CTranslate2 4.x
REQUIRED_DLLS = ("cublas64_12.dll", "cudnn64_9.dll")

AVAILABLE, NO_GPU, MISSING_LIBS = "available", "no_gpu", "missing_libs"
# قيم الإعداد «device»
DEVICES = ("auto", "cpu", "cuda")


def _loadable(name):
    try:
        ctypes.WinDLL(name)
        return True
    except OSError:
        return False


def status():
    """(الحالة، تفاصيل): AVAILABLE، أو NO_GPU، أو MISSING_LIBS مع أسماء المكتبات الناقصة"""
    try:
        import ctranslate2
        count = ctranslate2.get_cuda_device_count()
    except Exception:
        count = 0
    if count <= 0:
        return NO_GPU, []
    missing = [name for name in REQUIRED_DLLS if not _loadable(name)]
    if missing:
        return MISSING_LIBS, missing
    return AVAILABLE, []


def resolve(setting):
    """الجهاز الفعلي للتفريغ من الإعداد: «auto» و«cuda» يستخدمان الكرت فقط لو كان جاهزاً، وإلا المعالج"""
    if setting in ("auto", "cuda") and status()[0] == AVAILABLE:
        return "cuda"
    return "cpu"


def compute_type_for(device, requested):
    """
    int8 على الكرت أبطأ وأقل دقة من int8_float16، فنستخدمها بدلاً منه.
    والقيم الخاصة بالكرت (float16) لا تعمل على المعالج، فنرجع فيه إلى int8.
    """
    if device == "cuda" and requested == "int8":
        return "int8_float16"
    if device == "cpu" and requested in ("float16", "int8_float16"):
        return "int8"
    return requested
