"""تحميل النماذج بخادم وهمي: التقدم بالبايت، والاستكمال، والإلغاء، والملف الناقص"""
import time

import httpx
import pytest

from core.model_downloader import (ModelDownloadThread, EVT_DOWNLOAD_PROGRESS, EVT_DOWNLOAD_RESULT, CHUNK,
                                   format_eta, format_size)
from core.model_manager import ModelManager


class FakeI18n:
    def get(self, key, default=None, **kw):
        return default or key


def serve(files, calls, ignore_range=False, delay=0.0):
    def handler(request):
        name = request.url.path.rsplit("/", 1)[-1]
        rng = request.headers.get("range")
        calls.append((name, rng))
        data = files[name]
        if delay:
            time.sleep(delay)
        if rng and not ignore_range:
            return httpx.Response(206, content=data[int(rng.split("=")[1].rstrip("-")):])
        return httpx.Response(200, content=data)
    return httpx.Client(transport=httpx.MockTransport(handler))


def run_download(wx_app, files, listing, target, client, abort_after=None):
    import wx
    frame = wx.Frame(None)
    progress, results = [], []
    # wx يحذف الحدث بعد معالجته، فنحفظ قيمه
    EVT_DOWNLOAD_PROGRESS(frame, lambda e: progress.append({"percent": e.percent, "total": e.total}))
    EVT_DOWNLOAD_RESULT(frame, lambda e: results.append(e.status))
    thread = ModelDownloadThread(frame, "org/repo", str(target), 0, FakeI18n(), client=client, files=listing)
    if abort_after is not None:
        time.sleep(abort_after)
        thread.abort()
    thread.join(10)
    for _ in range(20):
        wx.Yield()
    frame.Destroy()
    return progress, results


@pytest.fixture
def model_files():
    files = {"config.json": b"{}" * 10, "model.bin": bytes(range(256)) * 4000}
    listing = [("model.bin", len(files["model.bin"])), ("config.json", len(files["config.json"]))]
    listing.sort(key=lambda f: f[0] == "model.bin")
    return files, listing


def test_download_resumes_and_reports_progress(wx_app, tmp_path, model_files):
    files, listing = model_files
    target = tmp_path / "m"
    target.mkdir()
    # تحميل سابق انقطع في منتصف model.bin
    (target / "model.bin.part").write_bytes(files["model.bin"][:5000])
    calls = []
    progress, results = run_download(wx_app, files, listing, target, serve(files, calls))
    assert results == ["success"]
    assert (target / "model.bin").read_bytes() == files["model.bin"]
    assert not (target / "model.bin.part").exists()
    # model.bin آخر ملف، ويكمل من حيث توقف
    assert calls == [("config.json", None), ("model.bin", "bytes=5000-")]
    assert progress and progress[0]["percent"] >= 0 and progress[0]["total"] == format_size(sum(s for _, s in listing), FakeI18n())
    assert ModelManager.is_valid_model_dir(str(target))


def test_download_server_ignores_range(wx_app, tmp_path):
    files = {"model.bin": b"abcdefghij" * 1000}
    target = tmp_path / "m"
    target.mkdir()
    (target / "model.bin.part").write_bytes(b"abcde")
    _, results = run_download(wx_app, files, [("model.bin", 10000)], target, serve(files, [], ignore_range=True))
    assert results == ["success"]
    assert (target / "model.bin").read_bytes() == files["model.bin"]


def test_download_abort_stops_quickly(wx_app, tmp_path):
    files = {"model.bin": b"x" * (CHUNK * 40)}
    target = tmp_path / "m"
    started = time.time()
    _, results = run_download(wx_app, files, [("model.bin", len(files["model.bin"]))], target,
                              serve(files, [], delay=0.3), abort_after=0.1)
    assert results == [] and time.time() - started < 5
    assert not ModelManager.is_valid_model_dir(str(target))


def test_download_incomplete_file_is_error(wx_app, tmp_path):
    files = {"model.bin": b"short"}
    _, results = run_download(wx_app, files, [("model.bin", 100)], tmp_path / "m", serve(files, []))
    assert results == ["error"]
    assert not ModelManager.is_valid_model_dir(str(tmp_path / "m"))


def test_format_eta():
    assert format_eta(125) == "02:05" and format_eta(3725) == "01:02:05"
