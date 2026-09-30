import wx
import os
from core.paths import APP_DIR
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
        return True

if __name__ == '__main__':
    # المجلدات تُنشأ بجانب البرنامج مهما كان المجلد الذي تم التشغيل منه
    for folder in ("models", "output", "logs"):
        os.makedirs(os.path.join(APP_DIR, folder), exist_ok=True)
    app = TranscriptionApp(False)
    app.MainLoop()
