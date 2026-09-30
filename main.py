import os
import sys

# أولاً وقبل أي مكتبة أخرى: بدون نافذة سوداء تكون مخرجات الطباعة فارغة، وأي مكتبة تطبع شيئاً تنهار
from core.paths import DATA_DIR, LOGS_DIR, MODELS_DIR, ensure_dir, ensure_std_streams
ensure_std_streams()

import wx
from core.i18n import LocalizationManager
from core.settings import SettingsManager
from gui.main_window import MainWindow

class TranscriptionApp(wx.App):
    def OnInit(self):
        self.settings = SettingsManager()
        lang = self.settings.get("language", "ar")
        self.i18n = LocalizationManager(lang)

        self.main_window = MainWindow(self.i18n, self.settings, None)
        self.main_window.Show()

        # فتح ملف من سطر الأوامر أو من "فتح باستخدام" في ويندوز: يبدأ التفريغ مباشرة
        paths = [p for p in sys.argv[1:] if os.path.exists(p)]
        if paths:
            wx.CallAfter(self.main_window.on_files_dropped, paths)
        else:
            # تفريغ لم يكتمل في المرة السابقة (إغلاق مفاجئ أو انقطاع كهرباء): نعرض استكماله
            wx.CallAfter(self.main_window.check_pending_recovery)
        return True

if __name__ == '__main__':
    for folder in (DATA_DIR, LOGS_DIR, MODELS_DIR):
        ensure_dir(folder)
    app = TranscriptionApp(False)
    app.MainLoop()
