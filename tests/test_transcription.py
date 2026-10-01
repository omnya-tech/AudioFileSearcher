"""
اختبار تفريغ حقيقي بالنموذج المثبت على الجهاز (بطيء: حوالي دقيقة).
يُتخطى تلقائياً لو النموذج غير موجود أو لو ويندوز لا يستطيع توليد صوت منطوق.
"""
import subprocess
import sys
import time

import pytest
import wx

from core.model_manager import ModelManager

MODEL = "deepdml/faster-whisper-large-v3-turbo-ct2"
SENTENCE = "Hello, this is a short test of the transcription program. The weather is nice today."

pytestmark = pytest.mark.skipif(ModelManager.find_local_model(MODEL) is None, reason="model not installed")


@pytest.fixture(scope="module")
def speech_wav(tmp_path_factory):
    if sys.platform != "win32":
        pytest.skip("speech synthesis test needs Windows")
    path = tmp_path_factory.mktemp("speech") / "speech.wav"
    script = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.SetOutputToWaveFile('{path}'); $s.Speak('{SENTENCE}'); $s.Dispose()")
    result = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True)
    if result.returncode != 0 or not path.exists():
        pytest.skip("Windows speech synthesis unavailable")
    return str(path)


def wait_until_idle(win, timeout=600):
    t0 = time.time()
    while (win.transcription_thread is not None or win.processing_dialog is not None) and time.time() - t0 < timeout:
        wx.Yield()
        time.sleep(0.05)


def test_real_transcription_with_dictionary_cancel_and_rerun(main_window, settings, speech_wav, tmp_path, monkeypatch):
    from gui.report_dialog import ReportDialog
    reports = []
    monkeypatch.setattr(ReportDialog, "ShowModal", lambda self: reports.append(self.report) or wx.ID_OK)

    settings.update({"user_mode": "advanced", "transcription_language": "en", "model_size": MODEL,
                     "use_local_model": True, "dictionaries": {"test": {"corrections": {"weather": "WEATHER"}, "terms": []}},
                     "active_dictionary": "test",
                     "auto_save": True, "output_directory": str(tmp_path), "default_export_format": "srt",
                     "open_folder_after_save": False})

    main_window.set_single_file(speech_wav)
    main_window.on_process(None)
    wait_until_idle(main_window)

    text = " ".join(s[1] for s in main_window.all_segments)
    assert "WEATHER" in text, main_window.messages
    assert "transcription" in text.lower()
    assert reports and reports[0]["segment_details"]
    assert (tmp_path / "speech.srt").is_file()

    # إلغاء ثم تشغيل جديد فوراً
    main_window.on_process(None)
    wx.Yield(); time.sleep(0.2)
    main_window.cancel_processing()
    assert main_window.btn_process.IsEnabled() and main_window.processing_dialog is None
    main_window.on_process(None)
    wait_until_idle(main_window)
    assert main_window.all_segments and len(reports) == 2


def test_resume_continues_after_saved_part(main_window, settings, speech_wav, tmp_path, monkeypatch):
    """الاستكمال: المقاطع المحفوظة تبقى كما هي، والتفريغ يبدأ من نهاية آخر مقطع محفوظ"""
    from core import recovery
    from gui.report_dialog import ReportDialog
    monkeypatch.setattr(ReportDialog, "ShowModal", lambda self: wx.ID_OK)
    settings.update({"user_mode": "advanced", "transcription_language": "en", "model_size": MODEL,
                     "use_local_model": True, "dictionaries": {"test": {"corrections": {}, "terms": []}},
                     "active_dictionary": "test", "auto_save": False})

    previous = [("00:00 - 00:02", "PREVIOUS PART", 0.0, 2.0, [])]
    recovery.save(speech_wav, previous, 0)
    main_window.set_single_file(speech_wav)
    main_window._resume_confirmed = True
    main_window.on_process(None)
    wait_until_idle(main_window)

    segs = main_window.all_segments
    assert segs[0][1] == "PREVIOUS PART"
    assert len(segs) > 1 and all(s[2] >= 2.0 - 0.5 for s in segs[1:])
    assert "weather" in " ".join(s[1] for s in segs).lower()
    # اكتمل الملف، فلا يبقى ملف استرجاع
    assert recovery.load(speech_wav) is None
