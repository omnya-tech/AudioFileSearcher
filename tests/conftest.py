import os
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    """سجل العمليات يُكتب في مجلد مؤقت، حتى لا تمتلئ بيانات المستخدم الحقيقية ببيانات الاختبار"""
    import core.transcription_logger as tl
    original_init = tl.TranscriptionLogger.__init__

    def init(self, i18n=None):
        original_init(self, i18n)
        self.history_file = str(tmp_path / "history.json")
        self.history = []

    monkeypatch.setattr(tl.TranscriptionLogger, "__init__", init)
    # ملفات استرجاع التفريغ كذلك في مجلد مؤقت
    import core.recovery as rec
    monkeypatch.setattr(rec, "RECOVERY_DIR", str(tmp_path / "recovery"))
    # وسجل الأخطاء أيضاً، حتى لا تظهر أخطاء الاختبارات في سجل المستخدم الحقيقي
    import core.logger as lg
    monkeypatch.setattr(lg._logger_instance, "log_file", str(tmp_path / "app.log"))
    # وما يتعلمه البرنامج من التعديلات
    import core.learning as learning
    monkeypatch.setattr(learning, "LEARNING_FILE", str(tmp_path / "learning.json"))


@pytest.fixture(scope="session")
def wx_app():
    import wx
    app = wx.App(False)
    yield app
    app.Destroy()


@pytest.fixture
def settings(tmp_path):
    from core.settings import SettingsManager
    s = SettingsManager(str(tmp_path / "config.json"))
    # سؤال "تحب البرنامج يتعلّم؟" يوقف الاختبارات، فالتعلم متوقف إلا في اختباراته
    s.set("learn_mode", "off")
    return s


@pytest.fixture
def i18n():
    from core.i18n import LocalizationManager
    return LocalizationManager("ar")


@pytest.fixture
def main_window(wx_app, settings, i18n, monkeypatch):
    import wx
    import gui.main_window as mw
    # الرسائل المنبثقة توقف الاختبار، فنسجلها بدلاً من عرضها
    messages = []
    monkeypatch.setattr(mw.wx, "MessageBox", lambda *a, **k: messages.append(a[0]))
    win = mw.MainWindow(i18n, settings, None)
    win.messages = messages
    yield win
    win.unsaved_edits = False
    win.Destroy()
    wx.Yield()
