"""
تسجيل الانهيارات الحقيقية فقط في logs/crash.log.

كنا نستخدم faulthandler.enable، لكنه على ويندوز يسجّل كل استثناء على مستوى النظام لحظة حدوثه، قبل أن يُعرف
هل سيُعالَج أم لا. فكان الملف يمتلئ بأسطر «Windows fatal exception» لاستثناءات يعالجها ويندوز نفسه
(مثل 0x8001010d و0x80010108 من اتصالات COM مع قارئ الشاشة والحافظة) والبرنامج يعمل بلا مشكلة.

الآن نسجّل من مرشّح الاستثناءات غير المعالَجة (SetUnhandledExceptionFilter): لا يُستدعى إلا لاستثناء لم يعالجه
أحد، أي انهيار سيغلق البرنامج فعلاً. نكتب رمزه وعنوانه ومكان كل خيط في كود بايثون، ثم نترك ويندوز يكمل كالمعتاد.
"""
import ctypes
import faulthandler
import os
import time
from ctypes import wintypes

EXCEPTION_CONTINUE_SEARCH = 0


class EXCEPTION_RECORD(ctypes.Structure):
    _fields_ = [("ExceptionCode", wintypes.DWORD), ("ExceptionFlags", wintypes.DWORD),
                ("ExceptionRecord", ctypes.c_void_p), ("ExceptionAddress", ctypes.c_void_p),
                ("NumberParameters", wintypes.DWORD), ("ExceptionInformation", ctypes.c_size_t * 15)]


class EXCEPTION_POINTERS(ctypes.Structure):
    _fields_ = [("ExceptionRecord", ctypes.POINTER(EXCEPTION_RECORD)), ("ContextRecord", ctypes.c_void_p)]


FILTER_FUNC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.POINTER(EXCEPTION_POINTERS))

# مرجع دائم للمرشّح: لو حذفه جامع النفايات يستدعي ويندوز عنواناً لم يعد موجوداً
_filter = None


def install(log_path):
    """تفعيل تسجيل الانهيارات في log_path. لا يرمي خطأ أبداً: التسجيل ميزة مساعدة"""
    global _filter

    def on_crash(pointers):
        try:
            record = pointers.contents.ExceptionRecord.contents
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{time.strftime('%Y-%m-%d %H:%M:%S')} Unhandled exception 0x{record.ExceptionCode:08X} "
                        f"at 0x{record.ExceptionAddress or 0:X}\n")
                f.flush()
                faulthandler.dump_traceback(f, all_threads=True)
        except Exception:
            pass
        # نترك ويندوز يكمل معالجته المعتادة (إغلاق البرنامج وتقرير الأخطاء)
        return EXCEPTION_CONTINUE_SEARCH

    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        _filter = FILTER_FUNC(on_crash)
        kernel32 = ctypes.windll.kernel32
        kernel32.SetUnhandledExceptionFilter.restype = ctypes.c_void_p
        kernel32.SetUnhandledExceptionFilter.argtypes = [ctypes.c_void_p]
        kernel32.SetUnhandledExceptionFilter(ctypes.cast(_filter, ctypes.c_void_p))
    except (OSError, AttributeError):
        pass
