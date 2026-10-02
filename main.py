import os
import sys
import getpass

# أولاً وقبل أي مكتبة أخرى: بدون نافذة سوداء تكون مخرجات الطباعة فارغة، وأي مكتبة تطبع شيئاً تنهار
from core.paths import DATA_DIR, LOGS_DIR, MODELS_DIR, ensure_dir, ensure_std_streams
ensure_std_streams()

# وضوح النصوص على الشاشات المكبّرة (125% و150%...): نعلن لويندوز أن البرنامج يضبط نفسه لكل شاشة،
# وإلا يكبّره ويندوز كصورة فيظهر مشوشاً. يجب أن يحدث هذا قبل إنشاء أي نافذة
import ctypes
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # لكل شاشة على حدة (الإصدار 2)
except (AttributeError, OSError):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass

# تسجيل أي انهيار منخفض المستوى (في مكتبات الصوت أو النموذج) حتى لو لم يترك خطأ بايثون
from core import crash_log
crash_log.install(os.path.join(LOGS_DIR, "crash.log"))

import wx
from core.i18n import LocalizationManager
from core.settings import SettingsManager
from core import single_instance
from gui.main_window import MainWindow

class TranscriptionApp(wx.App):
    def OnInit(self):
        paths = [p for p in sys.argv[1:] if os.path.exists(p)]

        # نسخة واحدة فقط: لو البرنامج مفتوح، نرسل له الملفات ونخرج بدلاً من تحميل النموذج مرة ثانية
        self.instance_checker = wx.SingleInstanceChecker(f"MediaSearcher-{getpass.getuser()}")
        if self.instance_checker.IsAnotherRunning():
            single_instance.send_request(paths)
            return False
        single_instance.clear_inbox()

        self.settings = SettingsManager()
        self.settings.apply_installer_language()
        if self.settings.get("theme", "light") == "dark":
            # المظهر الداكن الأصلي في ويندوز: يشمل كل النوافذ والقوائم وخانات الاختيار وشريط العنوان.
            # يجب تفعيله قبل إنشاء أي نافذة، لذلك تغيير المظهر يكتمل بعد إعادة تشغيل البرنامج
            from gui import icons
            icons.native_dark = self.MSWEnableDarkMode(wx.App.DarkMode_Always)
        lang = self.settings.get("language", "ar")
        self.i18n = LocalizationManager(lang)

        self.main_window = MainWindow(self.i18n, self.settings, None)
        self.main_window.Show()

        self.main_window.start_instance_inbox()

        # فتح ملف من سطر الأوامر أو من "فتح باستخدام" في ويندوز: يبدأ التفريغ مباشرة
        if paths:
            wx.CallAfter(self.main_window.on_files_dropped, paths)
        else:
            # تفريغ لم يكتمل في المرة السابقة (إغلاق مفاجئ أو انقطاع كهرباء): نعرض استكماله
            wx.CallAfter(self.startup_checks)
        return True

    def startup_checks(self):
        # أول تشغيل بدون نموذج: إرشاد لمدير النماذج. وإلا: عرض استكمال أي تفريغ لم يكتمل
        if self.main_window.ensure_model_ready(at_startup=True):
            self.main_window.check_pending_recovery()

if __name__ == '__main__':
    for folder in (DATA_DIR, LOGS_DIR, MODELS_DIR):
        ensure_dir(folder)
    app = TranscriptionApp(False)
    app.MainLoop()
