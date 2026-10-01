import json
import os

import pytest

from core.text_corrector import TextCorrector
from core.model_manager import ModelManager
from core.cross_file_search import parse_subtitles, CrossFileSearcher, find_audio_for
from core.time_utils import format_srt_time, format_range, format_clock
from core.settings import SettingsManager
from core.paths import RESOURCE_DIR as BASE_DIR

DICT = {"المدرسه": "المدرسة", "كورونا": "كوفيد", "ذكاء": "الذكاء", "و": "أو"}


@pytest.mark.parametrize("text, level, expected", [
    ("ذهبت إلى المدرسه اليوم", "light", "ذهبت إلى المدرسة اليوم"),
    ("وكورونا انتشر", "light", "وكورونا انتشر"),            # الخفيف لا يلتقط الحروف الملتصقة
    ("وكورونا انتشر", "medium", "وكوفيد انتشر"),
    ("مررت بالمدرسه", "medium", "مررت بالمدرسة"),
    ("كوروناتي", "medium", "كوروناتي"),                      # لا يصحح جزءاً من كلمة أخرى
    ("ولد و بنت", "medium", "ولد أو بنت"),                   # الكلمات القصيرة بدون حروف ملتصقة
    ("والذكاء", "medium", "والذكاء"),                        # "ال" لا تتكرر
    ("كُورُونَا", "aggressive", "كوفيد"),                    # تجاهل التشكيل
])
def test_corrector_levels(text, level, expected):
    assert TextCorrector(DICT).correct(text, level) == expected


def test_corrector_single_pass_and_edge_cases():
    assert TextCorrector({"أ": "ب", "ب": "ج"}).correct("أ ب", "light") == "ب ج"
    assert TextCorrector({"احمد": "أحمد"}).correct("قال إحمد", "aggressive") == "قال أحمد"
    assert TextCorrector({}).correct("نص", "medium") == "نص"
    assert TextCorrector(DICT).get_hotwords() == "المدرسة, كوفيد, الذكاء, أو"


def test_model_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(ModelManager, "get_models_dir", staticmethod(lambda: str(tmp_path)))
    turbo = "deepdml/faster-whisper-large-v3-turbo-ct2"
    assert ModelManager.resolve_model_path(turbo) == turbo
    assert ModelManager.resolve_model_path("tiny") == "Systran/faster-whisper-tiny"

    # الاسم القديم الذي استخدمته نافذة التحميل سابقاً ما زال يُكتشف
    old = tmp_path / "whisper-faster-whisper-large-v3-turbo-ct2"
    old.mkdir()
    (old / "model.bin").write_bytes(b"x")
    assert ModelManager.find_local_model(turbo) == str(old)
    assert ModelManager.get_installed_models() == [old.name]
    assert ModelManager.folder_name_for("tiny") == "Systran_faster-whisper-tiny"
    # مجلد بدون model.bin ليس نموذجاً
    (tmp_path / "broken").mkdir()
    assert "broken" not in ModelManager.get_installed_models()


def test_subtitles_and_search(tmp_path):
    srt = tmp_path / "clip.srt"
    srt.write_bytes("﻿1\r\n00:00:01,500 --> 00:00:03,000\r\nمرحبا بكم\r\n\r\n2\r\n01:02:03,040 --> 01:02:05,000\r\nسطر ثاني\r\nوثالث\r\n\r\n".encode("utf-8"))
    segs = parse_subtitles(str(srt))
    assert segs[0] == (1.5, 3.0, "مرحبا بكم")
    assert segs[1][2] == "سطر ثاني\nوثالث"
    assert abs(segs[1][0] - 3723.04) < 1e-6

    vtt = tmp_path / "v.vtt"
    vtt.write_text("WEBVTT\n\n00:05.000 --> 00:06.250\nhello there\n", encoding="utf-8")
    assert parse_subtitles(str(vtt)) == [(5.0, 6.25, "hello there")]

    (tmp_path / "clip.mp3").write_bytes(b"")
    assert find_audio_for(str(srt)) == str(tmp_path / "clip.mp3")

    (tmp_path / "other.json").write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    res = CrossFileSearcher().search_in_directory(str(tmp_path), "مرحبا")
    assert len(res) == 1 and res[0]["start"] == 1.5 and res[0]["time_str"] == "00:01 - 00:03"


def test_time_formats():
    assert format_srt_time(59.9996) == "00:01:00,000"
    assert format_srt_time(3723.04, ".") == "01:02:03.040"
    assert format_clock(3725) == "1:02:05"
    assert format_range(0, 2.5) == "00:00 - 00:02"


def test_settings(tmp_path):
    cfg = tmp_path / "config.json"
    s = SettingsManager(str(cfg))
    s.update({"beam_size": 3, "theme": "dark"})
    assert json.loads(cfg.read_text(encoding="utf-8"))["beam_size"] == 3
    assert SettingsManager(str(cfg)).get("theme") == "dark"

    cfg.write_text("{broken", encoding="utf-8")
    assert SettingsManager(str(cfg)).get("theme") == "light"   # ملف تالف => الافتراضي
    assert SettingsManager().config_file == os.path.join(BASE_DIR, "config.json")


def test_locales_have_same_keys():
    base = os.path.join(BASE_DIR, "locales")
    ar = json.load(open(os.path.join(base, "ar.json"), encoding="utf-8"))
    en = json.load(open(os.path.join(base, "en.json"), encoding="utf-8"))
    # صيغ المثنى والجمع القليل (_two, _few) خاصة بالعربية، والإنجليزية تستخدم one/many فقط
    only_ar = {k for k in set(ar) - set(en) if not k.endswith(("_two", "_few"))}
    assert only_ar == set() and set(en) - set(ar) == set()


def test_all_used_keys_exist():
    import check_keys
    used = check_keys.extract_keys_from_code(BASE_DIR)
    ar = json.load(open(os.path.join(BASE_DIR, "locales", "ar.json"), encoding="utf-8"))
    assert sorted(used - set(ar)) == []


def test_std_streams_fixed_without_console(tmp_path, monkeypatch):
    """بدون نافذة سوداء (exe/pythonw) الطباعة وشريط تقدم التحميل يجب ألا يوقفا البرنامج"""
    import sys
    from core import paths
    monkeypatch.setattr(paths, "LOGS_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    paths.ensure_std_streams()
    from tqdm import tqdm
    for _ in tqdm(range(3)):
        pass
    print("works")
    assert (tmp_path / "logs" / "console.log").exists()


def test_read_only_program_folder_falls_back(tmp_path, monkeypatch):
    """لو مجلد البرنامج للقراءة فقط (Program Files) البيانات تذهب لمجلد المستخدم ولا ينهار البرنامج"""
    import tempfile
    from core import paths
    appdata = str(tmp_path)

    def deny_program_folder(*a, dir=None, **k):
        # محاكاة Program Files: الكتابة ممنوعة في مجلد البرنامج فقط
        if dir and not dir.startswith(appdata):
            raise PermissionError("denied")
        return real_mkstemp(*a, dir=dir, **k)
    real_mkstemp = tempfile.mkstemp
    monkeypatch.setattr(tempfile, "mkstemp", deny_program_folder)
    monkeypatch.setenv("APPDATA", appdata)
    import importlib
    reloaded = importlib.reload(paths)
    try:
        assert reloaded.DATA_DIR == str(tmp_path / "AudioTranscriber")
        assert reloaded.CONFIG_FILE.startswith(reloaded.DATA_DIR)
        assert reloaded.ensure_dir(reloaded.LOGS_DIR)
        # مجلد نماذج بجانب البرنامج يبقى ضمن أماكن البحث
        assert any(d.endswith("models") for d in reloaded.EXTRA_MODEL_DIRS)
    finally:
        monkeypatch.undo()
        importlib.reload(paths)


def test_logger_survives_unwritable_dir(monkeypatch):
    from core import logger
    monkeypatch.setattr(logger, "LOGS_DIR", r"Z:\definitely\not\here")
    lg = logger.Logger()   # لا يجب أن يرمي خطأ
    lg._write("ERROR", "test")


def test_recovery_save_load_and_invalidate(tmp_path):
    from core import recovery
    audio = tmp_path / "talk.mp3"
    audio.write_bytes(b"abc")
    segs = [("00:00 - 00:02", "أ", 0.0, 2.0, []), ("00:02 - 00:05", "ب", 2.0, 5.0, [])]
    assert recovery.save(str(audio), segs, 60.0)
    data = recovery.load(str(audio))
    assert data["last_end"] == 5.0 and data["segments"] == segs and data["duration"] == 60.0
    assert [d["audio_path"] for d in recovery.list_pending()] == [str(audio)]

    # لو تغيّر الملف الصوتي لا نستكمل تفريغاً لا يطابقه
    audio.write_bytes(b"different content")
    assert recovery.load(str(audio)) is None

    audio.write_bytes(b"abc")
    import os
    os.utime(audio, (1, 1))
    recovery.save(str(audio), segs, 60.0)
    recovery.delete(str(audio))
    assert recovery.load(str(audio)) is None and recovery.list_pending() == []


def test_single_instance_messages(tmp_path, monkeypatch):
    from core import single_instance as si
    monkeypatch.setattr(si, "INBOX_DIR", str(tmp_path / "inbox"))
    assert si.send_request([str(tmp_path / "a.mp3")])
    assert si.send_request([])                       # فتح البرنامج بدون ملف: إظهار النافذة فقط
    reqs = si.take_requests()
    assert reqs == [[str(tmp_path / "a.mp3")], []]
    assert si.take_requests() == []                  # كل طلب يُقرأ مرة واحدة فقط


def test_split_on_gaps():
    from types import SimpleNamespace as N
    from core.audio_processor import split_on_gaps
    w = lambda t, a, b: N(word=t, start=a, end=b, probability=0.9)
    merged = N(start=55.6, end=87.6, avg_logprob=-0.1, text="x",
               words=[w(" last", 55.6, 56.0), w(" decade.", 56.0, 56.3), w(" Finally,", 82.0, 82.6), w(" wind", 82.6, 83.0)])
    normal = N(start=0, end=2, avg_logprob=-0.1, text="hi there", words=[w(" hi", 0, 0.5), w(" there", 0.6, 1.0)])
    parts = list(split_on_gaps([merged, normal]))
    assert [(p.start, p.end, p.text) for p in parts[:2]] == [(55.6, 56.3, "last decade."), (82.0, 83.0, "Finally, wind")]
    assert parts[2] is normal


def test_no_ampersand_in_texts():
    """& في نص زر أو قائمة يتحول لشرطة سفلية (اختصار لوحة مفاتيح) في ويندوز"""
    for lang in ("ar", "en"):
        d = json.load(open(os.path.join(BASE_DIR, "locales", f"{lang}.json"), encoding="utf-8"))
        assert [k for k, v in d.items() if "&" in v] == []


def test_merge_and_split_segments():
    from core import segments
    w = lambda t, a, b: {"word": " " + t, "start": a, "end": b, "probability": 0.9}
    a = ("", "بسم الله", 0.0, 2.0, [w("بسم", 0.0, 0.8), w("الله", 0.9, 2.0)])
    b = ("", "الرحمن الرحيم", 2.0, 5.0, [w("الرحمن", 2.1, 3.4), w("الرحيم", 3.5, 5.0)])
    m = segments.merge(a, b)
    assert m[1] == "بسم الله الرحمن الرحيم" and (m[2], m[3]) == (0.0, 5.0) and len(m[4]) == 4

    # التقسيم عند كلمة: الوقت من توقيت أول كلمة في الجزء الثاني
    first, second = segments.split(m, len("بسم الله "))
    assert (first[1], second[1]) == ("بسم الله", "الرحمن الرحيم")
    assert first[3] == second[2] == 2.1 and len(first[4]) == 2

    # بدون توقيتات كلمات: تقدير بنسبة طول النص
    plain = ("", "abcd efgh", 10.0, 20.0, [])
    p1, p2 = segments.split(plain, 4)
    assert 13 < p1[3] < 16 and p2[2] == p1[3]
    # في أول النص أو آخره: لا تقسيم
    assert segments.split(plain, 0) is None and segments.split(plain, len(plain[1])) is None


def test_word_export_direction_follows_text_not_interface(tmp_path):
    """النص العربي من اليمين لليسار في الوورد حتى لو كانت الواجهة إنجليزية، والإنجليزي العكس"""
    import docx
    from core import exporters
    segs = [("", "بسم الله الرحمن الرحيم", 0.0, 2.0, []), ("", "Hello world", 2.0, 3.0, [])]
    path = tmp_path / "out.docx"
    exporters.export(str(path), "docx", segs, title="x")
    paras = [p for p in docx.Document(str(path)).paragraphs if p.text.strip() and p.text != "x"]
    has_bidi = [p._p.pPr is not None and p._p.pPr.find(docx.oxml.ns.qn("w:bidi")) is not None for p in paras]
    assert has_bidi == [True, False]
