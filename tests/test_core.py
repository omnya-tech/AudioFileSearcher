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

    cfg.write_text('{"theme": "dark"}', encoding="utf-8-sig")
    assert SettingsManager(str(cfg)).get("theme") == "dark"    # ملف محفوظ بـ BOM


def test_installer_language(tmp_path, monkeypatch):
    import core.settings as settings_module
    monkeypatch.setattr(settings_module, "APP_DIR", str(tmp_path))
    marker = tmp_path / settings_module.INSTALLER_LANGUAGE_FILE
    cfg = str(tmp_path / "config.json")

    s = SettingsManager(cfg)
    s.apply_installer_language()                # لا يوجد ملف من المثبت: لا تغيير
    assert s.get("language") == "ar"

    marker.write_text("en", encoding="ascii")    # المستخدم اختار الإنجليزية في المثبت
    s.apply_installer_language()
    assert SettingsManager(cfg).get("language") == "en"

    s.set("language", "ar")                      # ثم غيّر اللغة من الإعدادات: يبقى اختياره
    s.apply_installer_language()
    assert s.get("language") == "ar"

    marker.write_text("en", encoding="ascii")    # تثبيت جديد بالإنجليزية يطبَّق مرة أخرى
    os.utime(marker, (1, 1))
    s.apply_installer_language()
    assert s.get("language") == "en"

    marker.write_text("xx", encoding="ascii")    # قيمة غير معروفة: تُتجاهل
    s.apply_installer_language()
    assert s.get("language") == "en"


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
        assert reloaded.DATA_DIR == str(tmp_path / "MediaSearcher")
        assert reloaded.CONFIG_FILE.startswith(reloaded.DATA_DIR)
        assert reloaded.ensure_dir(reloaded.LOGS_DIR)
        # مجلد نماذج بجانب البرنامج يبقى ضمن أماكن البحث
        assert any(d.endswith("models") for d in reloaded.EXTRA_MODEL_DIRS)
    finally:
        monkeypatch.undo()
        importlib.reload(paths)


def test_legacy_appdata_folder_is_moved(tmp_path, monkeypatch):
    """بيانات %APPDATA% بالأسماء التقنية القديمة تُنقل للاسم الحالي بإعداداتها"""
    from core import paths
    monkeypatch.setenv("APPDATA", str(tmp_path))
    current = tmp_path / "MediaSearcher"
    for name in ("AudioTranscriber", "AudioFileSearcher"):
        legacy = tmp_path / name
        legacy.mkdir()
        (legacy / "config.json").write_text(name, encoding="utf-8")
        assert paths._user_data_dir() == str(current)
        assert (current / "config.json").read_text(encoding="utf-8") == name and not legacy.exists()
        # لو وُجد المجلد الحالي لا نلمس القديم
        legacy.mkdir()
        assert paths._user_data_dir() == str(current) and legacy.exists()
        import shutil
        shutil.rmtree(current)
        shutil.rmtree(legacy)


def test_installed_build_keeps_data_in_roaming(tmp_path, monkeypatch):
    """النسخة المثبتة (exe) تحفظ بياناتها في %APPDATA% دائماً، حتى لو كان مجلد البرنامج قابلاً للكتابة"""
    import importlib
    import sys
    from core import paths
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    monkeypatch.delenv("MEDIA_SEARCHER_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Program Files" / "MediaSearcher" / "MediaSearcher.exe"))
    try:
        reloaded = importlib.reload(paths)
        assert reloaded.DATA_DIR == str(tmp_path / "Roaming" / "MediaSearcher")
        assert reloaded.MODELS_DIR.startswith(reloaded.DATA_DIR) and reloaded.CONFIG_FILE.startswith(reloaded.DATA_DIR)
    finally:
        monkeypatch.undo()
        importlib.reload(paths)


def test_old_install_data_moves_to_roaming(tmp_path, monkeypatch):
    """بيانات التثبيت القديم للمستخدم (بجانب البرنامج في مجلد Programs داخل LOCALAPPDATA) تُنقل لمجلد المستخدم دون استبدال الموجود"""
    from core import paths
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    old = tmp_path / "Local" / "Programs" / "AudioFileSearcher"
    (old / "models" / "turbo").mkdir(parents=True)
    (old / "models" / "turbo" / "model.bin").write_bytes(b"x")
    (old / "config.json").write_text('{"language": "en"}', encoding="utf-8")
    (old / "learning.json").write_text("old", encoding="utf-8")
    (old / "MediaSearcher.exe").write_bytes(b"exe")
    target = tmp_path / "Roaming" / "MediaSearcher"
    target.mkdir(parents=True)
    (target / "learning.json").write_text("new", encoding="utf-8")

    assert paths._user_data_dir() == str(target)
    assert (target / "models" / "turbo" / "model.bin").exists() and not (old / "models").exists()
    assert (target / "config.json").read_text(encoding="utf-8") == '{"language": "en"}'
    # الموجود في المجلد الجديد لا يُستبدل، والبرنامج نفسه لا يُنقل
    assert (target / "learning.json").read_text(encoding="utf-8") == "new" and (old / "learning.json").exists()
    assert not (target / "MediaSearcher.exe").exists()


def test_legacy_dictionary_file_imports(tmp_path):
    from core import dictionaries
    path = tmp_path / "old.json"
    path.write_text(json.dumps({"format": "audio-transcriber-dictionary", "version": 1, "name": "قرآن",
                                "corrections": {"سراط": "صراط"}, "terms": ["الفاتحة"]}, ensure_ascii=False),
                    encoding="utf-8")
    name, profile = dictionaries.import_file(str(path))
    assert name == "قرآن" and profile["corrections"] == {"سراط": "صراط"} and profile["terms"] == ["الفاتحة"]


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


@pytest.mark.parametrize("before, after, expected", [
    ("سراط الذين أنعمت عليهم ولا الظالم", "صراط الذين أنعمت عليهم ولا الضالين", [("سراط", "صراط"), ("الظالم", "الضالين")]),
    ("ذهبت الى المدرسه", "ذهبت إلى المدرسة،", [("الى", "إلى"), ("المدرسه", "المدرسة")]),   # كلمة كلمة
    ("في عام الف وتسعمية", "في عام 1900", [("الف وتسعمية", "1900")]),                     # عبارة قصيرة
    ("The weather is nice today.", "The weather is nice today", []),                      # ترقيم فقط
    ("مالك يوم الدين", "مالك يوم الدين والحساب", []),                                     # إضافة لا تصحيح
    ("one two three four five", "six seven eight nine ten", [("one", "six"), ("two", "seven"), ("three", "eight"), ("four", "nine"), ("five", "ten")]),
    ("one two three four five", "a b", []),                                               # إعادة صياغة طويلة
])
def test_extract_corrections(before, after, expected):
    from core.learning import extract_corrections
    assert extract_corrections(before, after) == expected


def test_learning_store_and_model_hints(tmp_path):
    from core.learning import LearningStore, hotwords_for_model
    store = LearningStore(str(tmp_path / "l.json"))
    store.record_edit("a.mp3", 1.0, 2.0, "سراط الذين", "صراط الذين")
    store.record_edit("a.mp3", 5.0, 6.0, "سراط المستقيم", "صراط المستقيم")
    store.record_edit("a.mp3", 7.0, 8.0, "ولا الظالم", "ولا الضالين")
    assert store.count("سراط", "صراط") == 2 and len(store.samples()) == 3

    again = LearningStore(str(tmp_path / "l.json"))          # يبقى بعد إعادة فتح البرنامج
    assert again.count("سراط", "صراط") == 2

    # التلميحات للنموذج: الأكثر تصحيحاً أولاً، ثم باقي القاموس، بدون تكرار
    hints = hotwords_for_model({"الظالم": "الضالين", "سراط": "صراط", "x": "يدوي"}, again)
    assert hints.split(", ") == ["صراط", "الضالين", "يدوي"]
    assert len(hotwords_for_model({str(i): f"w{i}" for i in range(100)}, None, limit=10).split(", ")) == 10

    again.forget("سراط")
    assert again.count("سراط", "صراط") == 0


def test_export_training_data(tmp_path):
    import csv, wave
    import numpy as np
    from core.learning import export_dataset
    audio = tmp_path / "talk.wav"
    with wave.open(str(audio), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes((np.sin(np.linspace(0, 2000, 16000 * 3)) * 5000).astype(np.int16).tobytes())
    samples = [{"audio": str(audio), "start": 0.5, "end": 1.5, "original": "سراط", "corrected": "صراط"},
               {"audio": str(tmp_path / "missing.wav"), "start": 0, "end": 1, "original": "a", "corrected": "b"}]
    exported, skipped = export_dataset(samples, str(tmp_path / "out"))
    assert (exported, skipped) == (1, 1)
    rows = list(csv.DictReader(open(tmp_path / "out" / "metadata.csv", encoding="utf-8-sig")))
    assert rows == [{"file_name": "clip_00001.wav", "transcription": "صراط", "original": "سراط"}]
    with wave.open(str(tmp_path / "out" / "clip_00001.wav")) as w:
        assert abs(w.getnframes() - 16000) < 50          # ثانية واحدة من 0.5 إلى 1.5


def test_dictionaries_migration_and_profiles(tmp_path):
    from core import dictionaries
    s = SettingsManager(str(tmp_path / "c.json"))
    s.set("custom_dictionary", {"سراط": "صراط"})                 # إعدادات إصدار قديم: قاموس واحد
    assert dictionaries.names(s) == ["عام"]
    assert dictionaries.active_corrections(s) == {"سراط": "صراط"}  # لا يضيع شيء عند النقل

    profiles = dictionaries.all_profiles(s)
    profiles["محاضرات"] = {"corrections": {"اكشن": "أكشن"}, "terms": ["تشارلز باباج"]}
    dictionaries.save_all(s, profiles, "محاضرات")
    assert dictionaries.active_terms(s) == ["تشارلز باباج"]

    # التعلم يذهب للقاموس النشط فقط: تصحيح المحاضرات لا يدخل قاموس القرآن والعكس
    dictionaries.add_corrections(s, [("الظالم", "الظلم")])
    assert "الظالم" in dictionaries.get(s, "محاضرات")["corrections"]
    assert "الظالم" not in dictionaries.get(s, "عام")["corrections"]

    reloaded = SettingsManager(str(tmp_path / "c.json"))
    assert dictionaries.active_name(reloaded) == "محاضرات" and dictionaries.names(reloaded) == ["عام", "محاضرات"]


def test_dictionary_import_export_formats(tmp_path):
    from core import dictionaries
    profile = {"corrections": {"سراط": "صراط"}, "terms": ["الفاتحة", "الفاتحة", " "]}
    dictionaries.export_file(str(tmp_path / "quran.json"), "قرآن", profile)
    name, imported = dictionaries.import_file(str(tmp_path / "quran.json"))
    assert name == "قرآن" and imported == {"corrections": {"سراط": "صراط"}, "terms": ["الفاتحة"]}

    (tmp_path / "medical.csv").write_text("ضغت,ضغط\nالسكرى,السكري\nأنسولين\n", encoding="utf-8")
    name, imported = dictionaries.import_file(str(tmp_path / "medical.csv"))
    assert name == "medical" and imported["corrections"] == {"ضغت": "ضغط", "السكرى": "السكري"} and imported["terms"] == ["أنسولين"]

    (tmp_path / "names.txt").write_text("# أسماء\nأحمد شوقي\nسراط ← صراط\nاكشن = أكشن\n", encoding="utf-8")
    _, imported = dictionaries.import_file(str(tmp_path / "names.txt"))
    assert imported["terms"] == ["أحمد شوقي"] and imported["corrections"] == {"سراط": "صراط", "اكشن": "أكشن"}

    (tmp_path / "plain.json").write_text('{"ا": "ب"}', encoding="utf-8")          # قاموس بسيط {خطأ: صحيح}
    assert dictionaries.import_file(str(tmp_path / "plain.json"))[1]["corrections"] == {"ا": "ب"}

    (tmp_path / "empty.txt").write_text("\n# فقط تعليق\n", encoding="utf-8")
    with pytest.raises(ValueError):
        dictionaries.import_file(str(tmp_path / "empty.txt"))

    merged = dictionaries.merge({"corrections": {"a": "b"}, "terms": ["x"]}, {"corrections": {"a": "c", "d": "e"}, "terms": ["x", "y"]})
    assert merged == {"corrections": {"a": "c", "d": "e"}, "terms": ["x", "y"]}


def test_terms_go_to_model_first():
    from core.learning import hotwords_for_model
    assert hotwords_for_model({"سراط": "صراط"}, None, terms=["تشارلز باباج"]).split(", ") == ["تشارلز باباج", "صراط"]


CRASH_SCRIPT = r'''
import ctypes, sys, time
sys.path.insert(0, {root!r})
mode, log = sys.argv[1], sys.argv[2]
if mode == "old":
    import faulthandler
    faulthandler.enable(open(log, "a"))
else:
    from core import crash_log
    crash_log.install(log)
# استثناء ويندوز يُعالَج (ctypes يحوّله لخطأ بايثون)، مثل استثناءات COM التي كانت تملأ الملف
try:
    ctypes.windll.kernel32.RaiseException(0x80010108, 0, 0, None)
except OSError:
    pass
if mode == "crash":
    # انهيار حقيقي: استثناء لا يعالجه أحد في خيط ويندوز
    k = ctypes.windll.kernel32
    k.CreateThread.restype = ctypes.c_void_p
    k.CreateThread.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
    k.CreateThread(None, 0, ctypes.cast(k.RaiseException, ctypes.c_void_p), ctypes.c_void_p(0xC0000005), 0, None)
    time.sleep(10)
'''


@pytest.mark.parametrize("mode", ["old", "handled", "crash"])
def test_crash_log_records_only_real_crashes(tmp_path, mode):
    import subprocess
    import sys
    script = tmp_path / "crash.py"
    script.write_text(CRASH_SCRIPT.format(root=BASE_DIR), encoding="utf-8")
    log = tmp_path / "crash.log"
    proc = subprocess.run([sys.executable, str(script), mode, str(log)], timeout=60, capture_output=True)
    text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    if mode == "old":
        # الطريقة القديمة كانت تسجّل الاستثناء المعالَج كأنه انهيار
        assert "0x80010108" in text
    elif mode == "handled":
        assert proc.returncode == 0 and text == ""
    else:
        assert proc.returncode != 0
        assert "Unhandled exception 0xC0000005" in text and "0x80010108" not in text
        assert "crash.py" in text   # مكان كود بايثون في الخيط الرئيسي


# ---------- كرت الشاشة ----------

def test_gpu_status_and_resolve(monkeypatch):
    import ctranslate2
    from core import gpu
    monkeypatch.setattr(ctranslate2, "get_cuda_device_count", lambda: 0)
    assert gpu.status() == (gpu.NO_GPU, []) and gpu.resolve("auto") == "cpu" and gpu.resolve("cuda") == "cpu"
    # كرت موجود لكن مكتبات NVIDIA ناقصة: لا نجرّبه (قد يُغلق البرنامج فجأة)
    monkeypatch.setattr(ctranslate2, "get_cuda_device_count", lambda: 1)
    monkeypatch.setattr(gpu, "_loadable", lambda name: name != "cudnn64_9.dll")
    assert gpu.status() == (gpu.MISSING_LIBS, ["cudnn64_9.dll"]) and gpu.resolve("auto") == "cpu"
    monkeypatch.setattr(gpu, "_loadable", lambda name: True)
    assert gpu.status()[0] == gpu.AVAILABLE
    assert gpu.resolve("auto") == "cuda" and gpu.resolve("cuda") == "cuda" and gpu.resolve("cpu") == "cpu"
    assert gpu.compute_type_for("cuda", "int8") == "int8_float16"
    assert gpu.compute_type_for("cpu", "float16") == "int8" and gpu.compute_type_for("cpu", "int8") == "int8"


def test_gpu_load_failure_falls_back_to_cpu(monkeypatch):
    from core import audio_processor as ap
    from core import gpu
    monkeypatch.setattr(gpu, "resolve", lambda setting: "cuda")
    monkeypatch.setattr(ap, "_CACHED_MODEL", None)
    monkeypatch.setattr(ap, "_CACHED_CONFIG", None)
    t = ap.TranscriptionThread.__new__(ap.TranscriptionThread)
    t.settings = {"device": "auto", "keep_in_memory": False}
    t._post = lambda *a: None
    created = []

    def create(model_target, is_local, device, compute_type, opts):
        created.append((device, compute_type))
        if device == "cuda":
            raise RuntimeError("CUDA failed with error out of memory")
        return "cpu-model"
    t._create_model = create
    model = t._load_model("m", True, {"compute_type": "int8", "threads_count": 0})
    assert model == "cpu-model" and t.device_used == "cpu" and "out of memory" in t.gpu_error
    assert created == [("cuda", "int8_float16"), ("cpu", "int8")]


def test_old_install_models_merge_into_existing_folder(tmp_path, monkeypatch):
    """مجلد النماذج موجود في المجلد الجديد: نماذج التثبيت القديم تُدمج فيه ولا تبقى مختبئة"""
    from core import paths
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    old_models = tmp_path / "Local" / "Programs" / "AudioFileSearcher" / "models"
    (old_models / "turbo").mkdir(parents=True)
    (old_models / "turbo" / "model.bin").write_bytes(b"old")
    (old_models / "small").mkdir()
    (old_models / "small" / "model.bin").write_bytes(b"old-small")
    target = tmp_path / "Roaming" / "MediaSearcher" / "models"
    (target / "small").mkdir(parents=True)
    (target / "small" / "model.bin").write_bytes(b"new-small")
    paths._user_data_dir()
    assert (target / "turbo" / "model.bin").read_bytes() == b"old"
    # الموجود لا يُستبدل، ويبقى في مكانه القديم
    assert (target / "small" / "model.bin").read_bytes() == b"new-small"
    assert (old_models / "small" / "model.bin").exists() and not (old_models / "turbo").exists()


def test_report_keeps_history_deletions_made_during_transcription(tmp_path):
    """التفريغ الجاري لا يعيد تفريغات حذفها المستخدم من السجل أثناءه"""
    from core import transcription_logger as tl
    running = tl.TranscriptionLogger()           # سجل التفريغ الجاري (حُمِّل عند بدئه)
    running.history_file = str(tmp_path / "h.json")
    running.history = []
    segs = [("", "كلمة", 0, 1, [])]
    running.create_report("old.mp3", segs, 0, 1, "m")
    window = tl.TranscriptionLogger()            # نافذة السجل
    window.history_file = running.history_file
    window.history = window.load_history()
    window.delete_entry(window.history[0])
    running.create_report("new.mp3", segs, 0, 1, "m")
    names = [e["file_name"] for e in tl.TranscriptionLogger.load_history(running)]
    assert names == ["new.mp3"]
