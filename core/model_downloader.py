"""
تحميل نماذج Whisper من HuggingFace مع تقدم حقيقي وإلغاء فوري واستكمال بعد الانقطاع.

كنا نقرأ شريط التقدم الذي تطبعه snapshot_download، لكن الإصدارات الحديثة من huggingface_hub لم تعد تطبع
تقدم كل ملف بالبايت (تطبع عدد الملفات فقط)، فكانت النافذة تبقى على «جارٍ الاتصال» والتحميل يجري في الخلفية،
ولا يتوقف عند الإلغاء. الآن نحمّل الملفات بأنفسنا:
  - التقدم بالبايت مهما كان عدد الملفات، والسرعة على آخر بضع ثوانٍ.
  - الإلغاء يُفحص بين كل دفعتين من البيانات.
  - كل ملف يُكتب في ‎.part‎ ويُكمَل من حيث توقف، وmodel.bin آخر ملف، فلا يصبح المجلد نموذجاً صالحاً إلا كاملاً.
"""
import os
import threading
import time

import wx

EVT_DOWNLOAD_RESULT_ID = wx.NewIdRef()
EVT_DOWNLOAD_PROGRESS_ID = wx.NewIdRef()

# دفعة صغيرة: التقدم يتحدث والإلغاء يستجيب بسرعة حتى على اتصال بطيء
CHUNK = 1024 * 64
SKIP_FILES = (".gitattributes",)
# أقل فاصل بين تحديثين للواجهة (لا داعي لتحديثها مع كل دفعة بيانات)
PROGRESS_INTERVAL = 0.5
# السرعة محسوبة على آخر هذه الثواني
SPEED_WINDOW = 5.0


def EVT_DOWNLOAD_RESULT(win, func):
    win.Connect(-1, -1, EVT_DOWNLOAD_RESULT_ID, func)


def EVT_DOWNLOAD_PROGRESS(win, func):
    win.Connect(-1, -1, EVT_DOWNLOAD_PROGRESS_ID, func)


class DownloadResultEvent(wx.PyEvent):
    def __init__(self, status, data=None):
        super().__init__()
        self.SetEventType(EVT_DOWNLOAD_RESULT_ID)
        self.status = status
        self.data = data


class DownloadProgressEvent(wx.PyEvent):
    def __init__(self, percent, speed, downloaded, remaining, total, eta):
        super().__init__()
        self.SetEventType(EVT_DOWNLOAD_PROGRESS_ID)
        self.percent = percent
        self.speed = speed
        self.downloaded = downloaded
        self.remaining = remaining
        self.total = total
        self.eta = eta


class DownloadAborted(Exception):
    pass


def repo_files(repo_id, api=None):
    """[(اسم الملف، الحجم بالبايت)] مع model.bin في آخر القائمة"""
    from huggingface_hub import HfApi
    info = (api or HfApi()).model_info(repo_id, files_metadata=True)
    files = [(s.rfilename, int(getattr(s, "size", None) or 0)) for s in info.siblings if s.rfilename not in SKIP_FILES]
    files.sort(key=lambda f: f[0] == "model.bin")
    return files


def format_size(size_bytes, i18n):
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / 1024 ** 3:.2f} {i18n.get('unit_gb', 'GB')}"
    if size_bytes >= 1024 ** 2:
        return f"{size_bytes / 1024 ** 2:.2f} {i18n.get('unit_mb', 'MB')}"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} {i18n.get('unit_kb', 'KB')}"
    return f"{int(size_bytes)} {i18n.get('unit_b', 'B')}"


def format_speed(bytes_per_second, i18n):
    for key, factor in (("unit_gb_s", 1024 ** 3), ("unit_mb_s", 1024 ** 2), ("unit_kb_s", 1024)):
        if bytes_per_second >= factor:
            return f"{bytes_per_second / factor:.2f} {i18n.get(key)}"
    return f"{int(bytes_per_second)} {i18n.get('unit_b_s')}"


def format_eta(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class ModelDownloadThread(threading.Thread):
    def __init__(self, parent, model_id, save_dir, expected_size, i18n, client=None, files=None):
        super().__init__(daemon=True)
        self.parent = parent
        self.repo_id = model_id if "/" in model_id else f"Systran/faster-whisper-{model_id}"
        self.save_dir = save_dir
        self.total = expected_size or 0
        self.i18n = i18n
        # للاختبارات: عميل HTTP وقائمة ملفات جاهزة بدلاً من الإنترنت
        self.client = client
        self.files = files
        self.downloaded = 0
        self._abort = threading.Event()
        self._samples = []
        self._last_post = 0.0
        self.start()

    def abort(self):
        self._abort.set()

    def _post(self, event):
        try:
            wx.PostEvent(self.parent, event)
        except RuntimeError:
            pass  # النافذة أُغلقت

    def run(self):
        import httpx
        own_client = self.client is None
        client = self.client or httpx.Client(follow_redirects=True, timeout=httpx.Timeout(30.0, read=60.0))
        try:
            if self.files is None:
                self.files = repo_files(self.repo_id)
            self.total = sum(size for _, size in self.files) or self.total
            os.makedirs(self.save_dir, exist_ok=True)
            # ما اكتمل سابقاً (أو جزئياً) يُحسب من البداية حتى تكون النسبة صحيحة عند الاستكمال
            self.downloaded = sum(self._existing_size(name, size) for name, size in self.files)
            self._progress(force=True)
            for name, size in self.files:
                self._download_file(client, name, size)
            self._post(DownloadResultEvent("success", self.save_dir))
        except DownloadAborted:
            pass
        except Exception as e:
            if not self._abort.is_set():
                self._post(DownloadResultEvent("error", str(e) or type(e).__name__))
        finally:
            if own_client:
                client.close()

    # ---------- الملفات ----------

    def _paths(self, name):
        final = os.path.join(self.save_dir, *name.split("/"))
        return final, final + ".part"

    def _existing_size(self, name, size):
        final, part = self._paths(name)
        if os.path.isfile(final) and (not size or os.path.getsize(final) == size):
            return size or os.path.getsize(final)
        return os.path.getsize(part) if os.path.isfile(part) else 0

    def _download_file(self, client, name, size):
        from huggingface_hub import hf_hub_url
        final, part = self._paths(name)
        if os.path.isfile(final) and (not size or os.path.getsize(final) == size):
            return
        os.makedirs(os.path.dirname(final), exist_ok=True)
        have = os.path.getsize(part) if os.path.isfile(part) else 0
        if size and have > size:
            # ملف جزئي أكبر من الحقيقي (تغيّر الملف على الخادم): نبدأ من جديد
            self.downloaded -= have
            have = 0
            os.remove(part)
        if not size or have < size:
            headers = {"Range": f"bytes={have}-"} if have else {}
            with client.stream("GET", hf_hub_url(self.repo_id, name), headers=headers) as response:
                if have and response.status_code == 200:
                    # الخادم تجاهل طلب الاستكمال وأرسل الملف كاملاً
                    self.downloaded -= have
                    have = 0
                response.raise_for_status()
                with open(part, "ab" if have else "wb") as f:
                    for chunk in response.iter_bytes(CHUNK):
                        if self._abort.is_set():
                            raise DownloadAborted()
                        f.write(chunk)
                        self.downloaded += len(chunk)
                        self._progress()
        if size and os.path.getsize(part) != size:
            raise IOError(f"Incomplete file {name}: {os.path.getsize(part)} of {size} bytes")
        os.replace(part, final)

    # ---------- التقدم ----------

    def speed(self):
        if len(self._samples) < 2:
            return 0.0
        (t0, b0), (t1, b1) = self._samples[0], self._samples[-1]
        return (b1 - b0) / (t1 - t0) if t1 > t0 else 0.0

    def _progress(self, force=False):
        now = time.monotonic()
        self._samples.append((now, self.downloaded))
        while len(self._samples) > 2 and self._samples[0][0] < now - SPEED_WINDOW:
            self._samples.pop(0)
        if not force and now - self._last_post < PROGRESS_INTERVAL:
            return
        self._last_post = now
        i18n = self.i18n
        total = max(self.total, self.downloaded)
        percent = min(99, int(self.downloaded * 100 / total)) if total else 0
        speed = self.speed()
        remaining = max(0, total - self.downloaded)
        eta = format_eta(remaining / speed) if speed > 0 else "..."
        self._post(DownloadProgressEvent(percent, format_speed(speed, i18n), format_size(self.downloaded, i18n),
                                         format_size(remaining, i18n), format_size(total, i18n), eta))
