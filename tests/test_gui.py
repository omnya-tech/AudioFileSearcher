import json
import os
import wave

import numpy as np
import pytest
import wx

SEGMENTS = [
    ("", "بسم الله الرحمن الرحيم", 0.0, 2.5, [{"word": "بسم", "start": 0, "end": 1, "probability": 0.99}]),
    ("", "ولا الظالم", 2.5, 6.0, [{"word": "ولا", "start": 2.5, "end": 3, "probability": 0.99},
                                  {"word": "الظالم", "start": 3, "end": 6, "probability": 0.65}]),
]


def load_segments(win):
    win.all_segments = list(SEGMENTS)
    win.update_list()


def test_window_opens_rtl_and_switches_language(main_window, i18n):
    assert main_window.GetLayoutDirection() == wx.Layout_RightToLeft
    i18n.set_language("en")
    assert main_window.btn_process.GetLabel() == i18n.get("btn_process")
    assert main_window.GetLayoutDirection() == wx.Layout_LeftToRight
    # شريط التبويبات يبقى من اليسار لليمين حتى لا تظهر الحروف مقلوبة
    assert main_window.notebook.GetLayoutDirection() == wx.Layout_LeftToRight
    i18n.set_language("ar")
    assert main_window.GetLayoutDirection() == wx.Layout_RightToLeft


def test_dialogs_open(main_window, i18n, settings):
    from gui.settings_dialog import SettingsDialog
    from gui.history_dialog import HistoryDialog
    from gui.custom_dict_dialog import CustomDictDialog
    from gui.report_dialog import ReportDialog
    from gui.about_dialog import AboutDialog
    from gui.edit_segment_dialog import EditSegmentDialog
    for dlg in (SettingsDialog(main_window, i18n, settings), HistoryDialog(main_window, i18n),
                CustomDictDialog(main_window, i18n, settings), AboutDialog(main_window, i18n),
                ReportDialog(main_window, i18n, {"file_name": "a.wav", "segment_details": [
                    {"time": "00:00 - 00:02", "status": "x", "confidence": "80%", "flagged": True}]}),
                EditSegmentDialog(main_window, i18n, "00:00 - 00:02", "نص", None)):
        dlg.Destroy()


def test_weak_segments_highlighted(main_window):
    load_segments(main_window)
    assert not main_window._is_weak(SEGMENTS[0])
    assert main_window._is_weak(SEGMENTS[1])
    assert main_window.result_list.GetItemTextColour(1) == wx.Colour(200, 40, 40)


def test_edit_segment_while_filtered(main_window, monkeypatch):
    import gui.main_window as mw
    load_segments(main_window)
    # البحث يُظهر السطر الثاني فقط، والتعديل يجب أن يصيب المقطع الصحيح
    main_window.txt_filter.SetValue("الظالم")
    assert main_window.result_list.GetItemCount() == 1
    main_window.result_list.Select(0)

    class FakeDialog:
        def __init__(self, *a, **k): pass
        def ShowModal(self): return wx.ID_OK
        def get_text(self): return "ولا الضالين"
        def Destroy(self): pass
    monkeypatch.setattr(mw, "EditSegmentDialog", FakeDialog)
    main_window.on_edit_segment(None)

    assert main_window.all_segments[1][1] == "ولا الضالين"
    assert main_window.all_segments[0][1] == SEGMENTS[0][1]
    assert main_window.unsaved_edits
    # بعد المراجعة البشرية لا يبقى المقطع معلَّماً كمشكوك فيه
    assert not main_window._is_weak(main_window.all_segments[1])


def test_unsaved_edits_prompt(main_window, monkeypatch):
    load_segments(main_window)
    main_window.unsaved_edits = True
    answers = iter([wx.ID_CANCEL, wx.ID_NO])
    monkeypatch.setattr(wx.MessageDialog, "ShowModal", lambda self: next(answers))
    assert main_window.confirm_discard_edits() is False   # تراجع
    assert main_window.unsaved_edits
    assert main_window.confirm_discard_edits() is True    # تجاهل التعديلات
    assert not main_window.unsaved_edits


@pytest.mark.parametrize("fmt", ["srt", "txt", "vtt", "json", "docx"])
def test_export_formats(main_window, tmp_path, fmt):
    load_segments(main_window)
    main_window.unsaved_edits = True
    path = tmp_path / f"out.{fmt}"
    assert main_window.save_as(str(path), fmt, show_msg=False)
    assert path.stat().st_size > 0
    assert not main_window.unsaved_edits


def test_export_then_reload_srt(main_window, tmp_path):
    load_segments(main_window)
    path = tmp_path / "out.srt"
    main_window.save_as(str(path), "srt", show_msg=False)
    main_window.load_srt_file(str(path))
    assert [s[1] for s in main_window.all_segments] == [s[1] for s in SEGMENTS]
    assert main_window.all_segments[1][2] == 2.5


@pytest.mark.parametrize("model_id, tags, expected", [
    ("guillaumekln/faster-whisper-large-v2", ["ar", "en", "fr", "de", "es"], False),  # متعدد اللغات
    ("OdyAsh/faster-whisper-base-ar-quran", [], True),
    ("x/faster-whisper-small-egyptian-arabic", [], True),
    ("x/faster-whisper-large-v3-turbo", [], False),
    ("x/some-model", ["ar"], True),
])
def test_arabic_model_filter(model_id, tags, expected):
    from gui.download_dialog import HFSearchThread
    assert HFSearchThread.is_arabic_model(model_id.lower(), tags) is expected


def test_model_list_failure_is_readable(main_window, i18n, monkeypatch):
    """عند فشل جلب النماذج، سبب الفشل يظهر في نفس القائمة التي يقرأها قارئ الشاشة، ويُسجَّل في ملف السجل"""
    import time
    import httpx
    import gui.download_dialog as dd
    logged = []
    monkeypatch.setattr(dd, "log_error", logged.append)

    def boom(*a, **k):
        raise httpx.ConnectError("Max retries exceeded")
    monkeypatch.setattr(dd.HfApi, "list_models", boom)

    dlg = dd.DownloadDialog(main_window, i18n)
    dlg.cb_category.SetSelection(1)
    dlg.on_category_select(None)
    t0 = time.time()
    while i18n.get("dl_msg_fetching") in dlg.cb_model.GetString(0) and time.time() - t0 < 10:
        wx.Yield(); time.sleep(0.05)

    text = dlg.cb_model.GetString(0)
    assert i18n.get("dl_msg_fetch_failed") in text
    assert i18n.get("dl_msg_conn_failed") in text
    assert logged and "Max retries exceeded" in logged[0]
    assert not dlg.btn_start.IsEnabled()
    dlg.cleanup_and_destroy()


def test_playable_copy_converts_audio(main_window, tmp_path):
    src = tmp_path / "tone.wav"
    tone = (np.sin(np.linspace(0, 440 * 2 * np.pi, 16000)) * 12000).astype(np.int16)
    with wave.open(str(src), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(tone.tobytes())
    out = main_window.audio_player._playable_copy(str(src))
    with wave.open(out, "rb") as w:
        assert w.getnframes() > 20000   # ثانية واحدة بمعدل 22050
    assert main_window.audio_player._playable_copy(str(src)) == out   # يُعاد استخدام النسخة
