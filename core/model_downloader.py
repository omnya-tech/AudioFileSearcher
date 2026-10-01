import sys
import re
import threading
import wx
from huggingface_hub import snapshot_download, HfApi

EVT_DOWNLOAD_RESULT_ID = wx.NewIdRef()
EVT_DOWNLOAD_PROGRESS_ID = wx.NewIdRef()

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

class StderrInterceptor:
    def __init__(self, parent, expected_size, i18n, is_aborted=None):
        self.parent = parent
        self.is_aborted = is_aborted or (lambda: False)
        self.expected_size = expected_size
        self.i18n = i18n
        self.original_stderr = sys.stderr
        self.buffer = ""
        self.max_dl_bytes = 0
        
        self.total_str = self.format_size(self.expected_size) if self.expected_size > 0 else self.i18n.get("dl_val_unknown", "غير معروف")

    def format_size(self, size_bytes):
        unit_gb = self.i18n.get('unit_gb', 'جيجابايت')
        unit_mb = self.i18n.get('unit_mb', 'ميجابايت')
        unit_kb = self.i18n.get('unit_kb', 'كيلوبايت')
        unit_b = self.i18n.get('unit_b', 'بايت')
        
        if size_bytes >= 1024**3: return f"{size_bytes / 1024**3:.2f} {unit_gb}"
        elif size_bytes >= 1024**2: return f"{size_bytes / 1024**2:.2f} {unit_mb}"
        elif size_bytes >= 1024: return f"{size_bytes / 1024:.2f} {unit_kb}"
        return f"{int(size_bytes)} {unit_b}"

    def translate_speed_str(self, speed_str):
        s = speed_str.upper()
        unit_gb_s = self.i18n.get('unit_gb_s', 'جيجابايت/ثانية')
        unit_mb_s = self.i18n.get('unit_mb_s', 'ميجابايت/ثانية')
        unit_kb_s = self.i18n.get('unit_kb_s', 'كيلوبايت/ثانية')
        unit_b_s = self.i18n.get('unit_b_s', 'بايت/ثانية')
        
        s = s.replace('GB/S', f" {unit_gb_s}")
        s = s.replace('MB/S', f" {unit_mb_s}")
        s = s.replace('KB/S', f" {unit_kb_s}")
        s = s.replace('B/S', f" {unit_b_s}")
        return s.strip()

    def write(self, text):
        # شريط التقدم يكتب هنا باستمرار من خيوط التحميل، فنستغل ذلك لإيقاف التحميل فوراً عند الإلغاء
        if self.is_aborted() and threading.current_thread() is not threading.main_thread():
            raise DownloadAborted()
        if self.original_stderr is not None:
            try: self.original_stderr.write(text)
            except Exception: pass
        self.buffer += text
        while '\r' in self.buffer or '\n' in self.buffer:
            if '\r' in self.buffer:
                line, self.buffer = self.buffer.split('\r', 1)
            else:
                line, self.buffer = self.buffer.split('\n', 1)
            if line.strip():
                self.parse_line(line)

    def flush(self):
        if self.original_stderr is not None:
            try: self.original_stderr.flush()
            except Exception: pass

    def isatty(self):
        return False

    def parse_line(self, line):
        if "B/s" not in line and "it/s" not in line:
            return

        clean_line = line.replace(" ", "")

        speed_str = ""
        speed_bytes = 0
        speed_match = re.search(r'([\d.]+[kMGT]?B/s)', clean_line, re.IGNORECASE)
        if speed_match:
            speed_str = speed_match.group(1).upper()
            try:
                s_val = float(re.findall(r'[\d.]+', speed_str)[0])
                if 'K' in speed_str: speed_bytes = s_val * 1024
                elif 'M' in speed_str: speed_bytes = s_val * 1024**2
                elif 'G' in speed_str: speed_bytes = s_val * 1024**3
                else: speed_bytes = s_val
            except: pass

        dl_str = ""
        dl_bytes = 0
        dl_match = re.search(r'([\d.]+[kMGT]?B?),[\d.]+[kMGT]?B/s', clean_line, re.IGNORECASE)
        if not dl_match:
            dl_match = re.search(r'\|([\d.]+[kMGT]?B?),', clean_line, re.IGNORECASE)

        if dl_match:
            dl_str = dl_match.group(1).upper()
            if not dl_str.endswith('B'): dl_str += 'B'
            try:
                val = float(re.findall(r'[\d.]+', dl_str)[0])
                if 'K' in dl_str: dl_bytes = val * 1024
                elif 'M' in dl_str: dl_bytes = val * 1024**2
                elif 'G' in dl_str: dl_bytes = val * 1024**3
                else: dl_bytes = val
            except: pass

        if not dl_str or not speed_str:
            return

        # الحماية من تراجع شريط التحميل
        if dl_bytes > self.max_dl_bytes:
            self.max_dl_bytes = dl_bytes
        else:
            dl_bytes = self.max_dl_bytes

        # التمدد الذكي في حال تجاوز الحجم الفعلي الحجم المتوقع
        if dl_bytes >= self.expected_size:
            self.expected_size = dl_bytes + (15 * 1024 * 1024)
            self.total_str = f"~ {self.format_size(self.expected_size)}"

        percent = 0
        eta_str = "..."
        remaining_str = "..."

        if self.expected_size > 0:
            safe_dl_bytes = min(dl_bytes, self.expected_size) 
            percent = int((safe_dl_bytes / self.expected_size) * 100)
            percent = min(max(percent, 0), 99) 

            remaining_bytes = self.expected_size - safe_dl_bytes
            remaining_str = self.format_size(remaining_bytes)

            if speed_bytes > 0:
                eta = remaining_bytes / speed_bytes
                if eta > 0:
                    m, s = divmod(int(eta), 60)
                    h, m = divmod(m, 60)
                    eta_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

        # ترجمة الوحدات إلى لغة الواجهة
        loc_speed_str = self.translate_speed_str(speed_str)
        loc_dl_str = self.format_size(dl_bytes)

        try:
            wx.PostEvent(self.parent, DownloadProgressEvent(percent, loc_speed_str, loc_dl_str, remaining_str, self.total_str, eta_str))
        except RuntimeError:
            pass  # نافذة التحميل أُغلقت

class ModelDownloadThread(threading.Thread):
    def __init__(self, parent, model_id, save_dir, expected_size, i18n):
        super().__init__(daemon=True)
        self.parent = parent
        self.model_id = model_id
        self.save_dir = save_dir
        self.expected_size = expected_size
        self.i18n = i18n
        self._abort = False
        self.start()

    def abort(self):
        self._abort = True

    def _post(self, event):
        try:
            wx.PostEvent(self.parent, event)
        except RuntimeError:
            pass  # النافذة أُغلقت

    def run(self):
        original_stderr = sys.stderr
        try:
            repo_id = self.model_id if "/" in self.model_id else f"Systran/faster-whisper-{self.model_id}"

            try:
                api = HfApi()
                info = api.model_info(repo_id, files_metadata=True)
                exact_size = sum(f.size for f in info.siblings if getattr(f, 'size', None) is not None)
                if exact_size > 0:
                    self.expected_size = exact_size
            except Exception:
                pass

            if self._abort:
                return

            sys.stderr = StderrInterceptor(self.parent, self.expected_size, self.i18n, is_aborted=lambda: self._abort)

            snapshot_download(
                repo_id=repo_id,
                local_dir=self.save_dir
            )

            if not self._abort:
                self._post(DownloadResultEvent("success", self.save_dir))

        except Exception as e:
            if not self._abort and not isinstance(e, DownloadAborted):
                self._post(DownloadResultEvent("error", str(e)))
        finally:
            sys.stderr = original_stderr