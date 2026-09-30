import json
import os

import pytest

from core.text_corrector import TextCorrector
from core.model_manager import ModelManager
from core.cross_file_search import parse_subtitles, CrossFileSearcher, find_audio_for
from core.time_utils import format_srt_time, format_range, format_clock
from core.settings import SettingsManager, BASE_DIR

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
    assert set(ar) == set(en)


def test_all_used_keys_exist():
    import check_keys
    used = check_keys.extract_keys_from_code(BASE_DIR)
    ar = json.load(open(os.path.join(BASE_DIR, "locales", "ar.json"), encoding="utf-8"))
    assert sorted(used - set(ar)) == []
