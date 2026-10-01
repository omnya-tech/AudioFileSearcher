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
    import gui.main.results as results
    monkeypatch.setattr(results, "EditSegmentDialog", FakeDialog)
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


def test_shortcuts_help_lists_menu_shortcuts(main_window):
    text = main_window.shortcuts_text()
    for key in ("Ctrl+O", "Ctrl+P", "Ctrl+F", "F2", "F3", "F1"):
        assert key in text
    from gui.text_dialog import TextDialog
    TextDialog(main_window, main_window.i18n, "x", text).Destroy()


def test_progress_row_announces_every_ten_percent(main_window, i18n):
    from gui.processing_dialog import ProcessingDialog
    dlg = ProcessingDialog(main_window, i18n)
    names = []
    for pct in (0, 3, 7, 12, 25, 29):
        dlg.update_progress(pct, 100, "جاري استخراج وتحليل النصوص...", "a.mp3")
        names.append(dlg.list_ctrl.GetItemText(1))
    # يتغير اسم السطر (فيُنطق) عند كل عشرة جديدة فقط
    assert len(dict.fromkeys(names)) == 3
    dlg.Destroy()


def test_live_append_respects_filter(main_window):
    main_window.all_segments = []
    main_window.update_list()
    main_window.append_segment(("", "بسم الله", 0.0, 1.0, []))
    main_window.txt_filter.ChangeValue("الحمد")
    main_window.append_segment(("", "الحمد لله", 1.0, 2.0, []))
    main_window.append_segment(("", "رب العالمين", 2.0, 3.0, []))
    assert len(main_window.all_segments) == 3
    assert main_window.result_list.GetItemCount() == 2       # السطر الذي لا يطابق البحث لا يُعرض
    assert main_window.result_list.GetItemData(1) == 1


def test_cancel_saves_partial_and_resume_prompt(main_window, tmp_path, monkeypatch):
    from core import recovery
    audio = tmp_path / "long.mp3"
    audio.write_bytes(b"x" * 10)
    main_window.set_single_file(str(audio))
    main_window.all_segments = list(SEGMENTS)
    main_window._audio_duration = 3600
    main_window.cancel_processing()
    assert recovery.load(str(audio))["last_end"] == 6.0
    assert main_window.all_segments and main_window.btn_process.IsEnabled()

    # استكمال
    monkeypatch.setattr(wx.MessageDialog, "ShowModal", lambda self: wx.ID_YES)
    proceed, segs = main_window._ask_resume(str(audio))
    assert proceed and len(segs) == 2
    # البدء من جديد يحذف التقدم المحفوظ
    monkeypatch.setattr(wx.MessageDialog, "ShowModal", lambda self: wx.ID_NO)
    proceed, segs = main_window._ask_resume(str(audio))
    assert proceed and segs is None and recovery.load(str(audio)) is None


def test_eta_estimate(main_window, i18n, monkeypatch):
    import gui.processing_dialog as pd
    clock = [1000.0]
    monkeypatch.setattr(pd.time, "time", lambda: clock[0])
    dlg = pd.ProcessingDialog(main_window, i18n)
    dlg.update_progress(10, 100, "x", "a.mp3")          # نقطة البداية
    clock[0] += 60
    dlg.update_progress(20, 100, "x", "a.mp3")          # 10% في دقيقة => 80% في 8 دقائق
    assert dlg._estimate_remaining(20, "a.mp3") == pytest.approx(480)
    assert "8 دقائق" in dlg.list_ctrl.GetItemText(1)
    assert dlg.format_eta(30) == i18n.get("eta_less_than_minute")
    # صيغ الجمع العربية: مثنى، جمع (3-10)، ومفرد بعد 10
    assert dlg.format_eta(120) == "باقي حوالي دقيقتين"
    assert dlg.format_eta(3 * 3600 + 5 * 60) == "باقي حوالي 3 ساعات و5 دقائق"
    assert dlg.format_eta(25 * 60) == "باقي حوالي 25 دقيقة"
    dlg.Destroy()


def test_report_speed_tip(main_window, i18n):
    from gui.report_dialog import ReportDialog
    slow = {"audio_info": {"duration_seconds": 3600}, "processing_time": {"total_seconds": 7200}}
    fast = {"audio_info": {"duration_seconds": 3600}, "processing_time": {"total_seconds": 1800}}
    tip_start = i18n.get("report_speed_tip", factor="X")[:15]
    assert tip_start in ReportDialog(main_window, i18n, slow)._summary_text()
    assert tip_start not in ReportDialog(main_window, i18n, fast)._summary_text()


@pytest.mark.parametrize("fmt", ["srt", "txt", "vtt"])
def test_text_exports_have_bom(main_window, tmp_path, fmt):
    load_segments(main_window)
    path = tmp_path / f"out.{fmt}"
    main_window.save_as(str(path), fmt, show_msg=False)
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")


def test_window_geometry_saved_and_restored(main_window, settings, i18n):
    import gui.main_window as mw
    main_window.SetSize(100, 80, 820, 560)
    main_window.save_window_geometry()
    geo = settings.get("window_geometry")
    assert (geo["w"], geo["h"]) == (820, 560) and geo["maximized"] is False
    second = mw.MainWindow(i18n, settings, None)
    try:
        assert tuple(second.GetSize()) == (820, 560)
    finally:
        second.Destroy()


def test_screen_scaling(main_window, monkeypatch):
    """على شاشة مكبّرة 150%: الأيقونات أكبر، ومقاس النافذة يُضرب في النسبة ثم لا يتجاوز الشاشة"""
    from gui import icons, widgets
    monkeypatch.setattr(icons, "scale", lambda: 1.5)
    assert icons.px(16) == 24
    assert icons.get("save", 16, theme="light").GetWidth() == 24

    frame = wx.Frame(None, size=(400, 300))
    monkeypatch.setattr(frame, "FromDIP", lambda v: wx.Size(int(v[0] * 1.5), int(v[1] * 1.5)) if not isinstance(v, int) else int(v * 1.5))
    widgets.fit_to_screen(frame)
    assert tuple(frame.GetSize()) == (600, 450)

    huge = wx.Frame(None, size=(5000, 5000))
    widgets.fit_to_screen(huge)
    area = wx.Display(0).GetClientArea()
    assert huge.GetSize().width <= area.width and huge.GetSize().height <= area.height
    frame.Destroy(); huge.Destroy()


def test_no_model_guides_user_instead_of_silent_download(main_window, monkeypatch, tmp_path):
    from core.model_manager import ModelManager
    assert ModelManager.recommend_model(16) == ModelManager.RECOMMENDED
    assert ModelManager.recommend_model(3) == "small"

    monkeypatch.setattr(ModelManager, "has_usable_model", staticmethod(lambda s: False))
    opened = []
    monkeypatch.setattr(main_window, "on_open_download_dialog", lambda e, preselect=None: opened.append(preselect))
    answers = iter([wx.ID_NO, wx.ID_YES])
    monkeypatch.setattr(wx.MessageDialog, "ShowModal", lambda self: next(answers))

    audio = tmp_path / "a.mp3"; audio.write_bytes(b"x")
    main_window.set_single_file(str(audio))
    main_window.on_process(None)                     # "لاحقاً": لا تفريغ ولا تحميل صامت
    assert main_window.transcription_thread is None and opened == []
    main_window.on_process(None)                     # "فتح مدير النماذج" بالنموذج المقترح
    assert main_window.transcription_thread is None and opened == [ModelManager.recommend_model()]


def test_merge_and_split_in_window(main_window, monkeypatch):
    import gui.main.results as results
    load_segments(main_window)
    main_window.result_list.Select(0); main_window.result_list.Focus(0)
    main_window.on_merge_next(None)
    assert len(main_window.all_segments) == 1 and main_window.unsaved_edits
    assert main_window.all_segments[0][1] == "بسم الله الرحمن الرحيم ولا الظالم"

    class SplitDialog:
        def __init__(self, *a, **k):
            self.txt = type("T", (), {"GetValue": lambda s: "بسم الله الرحمن الرحيم ولا الظالم"})()
            self.split_pos = len("بسم الله الرحمن الرحيم ")
        def ShowModal(self): return results.ID_SPLIT
        def Destroy(self): pass
    monkeypatch.setattr(results, "EditSegmentDialog", SplitDialog)
    main_window.result_list.Select(0)
    main_window.on_edit_segment(None)
    assert [s[1] for s in main_window.all_segments] == ["بسم الله الرحمن الرحيم", "ولا الظالم"]
    # بيانات الاختبار فيها توقيتات لبعض الكلمات فقط، فيُقدَّر الوقت بنسبة طول النص (الحالة بتوقيتات كاملة مختبرة في test_core)
    first, second = main_window.all_segments
    assert first[3] == second[2] and 0.0 < second[2] < 6.0


def test_player_stops_at_sentence_end(main_window, tmp_path, monkeypatch):
    """تشغيل جملة واحدة: توقف مؤقت عند نهايتها"""
    player = main_window.audio_player
    src = tmp_path / "tone.wav"
    tone = (np.sin(np.linspace(0, 440 * 2 * np.pi * 4, 16000 * 4)) * 8000).astype(np.int16)
    with wave.open(str(src), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(tone.tobytes())
    ok, err = player.load_and_play(str(src), 1.0, 2.0)
    if not ok:
        pytest.skip(f"no audio device: {err}")
    assert player.duration == pytest.approx(4.0, abs=0.1) and player.slider.GetMax() == 4
    monkeypatch.setattr(player, "position", lambda: 2.05)
    player._on_tick(None)
    assert not player.is_playing and player._stop_at is None
    player.on_stop(None)


def _controls(win):
    for child in win.GetChildren():
        yield child
        yield from _controls(child)


@pytest.mark.parametrize("lang", ["ar", "en"])
def test_no_control_is_cut_off(main_window, i18n, settings, lang):
    """كل زر وخانة ظاهرة بالكامل داخل نافذتها، في اللغتين (النصوص الإنجليزية أطول أحياناً)"""
    from gui.settings_dialog import SettingsDialog
    from gui.custom_dict_dialog import CustomDictDialog
    from gui.history_dialog import HistoryDialog
    from gui.edit_segment_dialog import EditSegmentDialog
    from gui.processing_dialog import ProcessingDialog
    from gui.about_dialog import AboutDialog
    from gui.report_dialog import ReportDialog
    i18n.set_language(lang)
    windows = [SettingsDialog(main_window, i18n, settings), CustomDictDialog(main_window, i18n, settings),
               HistoryDialog(main_window, i18n), EditSegmentDialog(main_window, i18n, "00:00 - 00:02", "نص", lambda: None),
               ProcessingDialog(main_window, i18n), AboutDialog(main_window, i18n), ReportDialog(main_window, i18n, {})]
    problems = []
    try:
        for win in [main_window] + windows:
            win.Show(); win.Layout(); wx.Yield()
            # مستطيل النافذة ومستطيلات عناصرها بنفس الطريقة (ClientToScreen ينعكس في النوافذ من اليمين لليسار)
            area = win.GetScreenRect()
            for c in _controls(win):
                if isinstance(c, (wx.Button, wx.CheckBox, wx.Choice)) and c.IsShownOnScreen():
                    r = c.GetScreenRect()
                    if not area.Contains(r):
                        problems.append(f"{type(win).__name__}: {c.GetLabel() or type(c).__name__}")
                    if isinstance(c, (wx.Button, wx.CheckBox)) and r.width + 2 < c.GetBestSize().width:
                        problems.append(f"{type(win).__name__}: cut text «{c.GetLabel()}»")
    finally:
        for w in windows:
            w.Destroy()
        i18n.set_language("ar")
    assert problems == []


FATIHA = [("", "سراط الذين أنعمت عليهم", 0.0, 3.0, []), ("", "اهدنا السراط المستقيم", 3.0, 6.0, []),
          ("", "سراط الذين أنعمت عليهم غير المغضوب", 6.0, 9.0, [])]


def test_learn_from_edit_ask_mode(main_window, settings, monkeypatch):
    main_window.all_segments = list(FATIHA); main_window.update_list()
    main_window.audio_path = "x.mp3"
    settings.set("learn_mode", "ask")
    monkeypatch.setattr(wx.MessageDialog, "ShowModal", lambda self: wx.ID_YES)   # "تعلّم وطبّق على باقي النص"
    main_window.all_segments[0] = ("", "صراط الذين أنعمت عليهم", 0.0, 3.0, [])
    main_window.learn_from_edit(0, "سراط الذين أنعمت عليهم", "صراط الذين أنعمت عليهم")
    assert settings.get("custom_dictionary") == {"سراط": "صراط"}
    assert main_window.all_segments[2][1] == "صراط الذين أنعمت عليهم غير المغضوب"   # طُبق على باقي النص
    # المستوى المتوسط يلتقط الكلمة مع "ال" الملتصقة بها: السراط ← الصراط
    assert main_window.all_segments[1][1] == "اهدنا الصراط المستقيم"
    assert main_window.learning.count("سراط", "صراط") == 1


def test_learn_auto_mode_needs_repetition(main_window, settings):
    main_window.all_segments = list(FATIHA); main_window.update_list()
    main_window.audio_path = "x.mp3"
    settings.set("learn_mode", "auto")
    main_window.learn_from_edit(0, "سراط الذين", "صراط الذين")
    assert not settings.get("custom_dictionary")                     # مرة واحدة: لا يتعلم بعد
    main_window.learn_from_edit(0, "سراط الذين", "صراط الذين")
    assert settings.get("custom_dictionary") == {"سراط": "صراط"}     # بعد التكرار: يتعلم ويطبّق
    assert main_window.all_segments[2][1].startswith("صراط")


def test_learn_off_and_apply_dictionary_menu(main_window, settings):
    main_window.all_segments = list(FATIHA); main_window.update_list()
    settings.set("learn_mode", "off")
    main_window.learn_from_edit(0, "سراط", "صراط")
    assert not settings.get("custom_dictionary") and not main_window.learning.samples()
    settings.set("custom_dictionary", {"سراط": "صراط", "السراط": "الصراط"})
    main_window.on_apply_dictionary(None)
    assert [s[1].split()[0] for s in main_window.all_segments] == ["صراط", "اهدنا", "صراط"]
    assert "الصراط" in main_window.all_segments[1][1] and main_window.unsaved_edits
