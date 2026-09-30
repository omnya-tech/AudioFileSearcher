import os
import wave
import shutil
import hashlib
import tempfile
import numpy as np
import wx
import pygame
from core.i18n import LocalizationManager
from core.logger import log_error
from core.time_utils import format_clock
from gui import icons

# جودة كافية للاستماع للكلام، مع حجم معقول للنسخة المؤقتة
PLAYBACK_RATE = 22050
# كل كم مللي ثانية يُحدَّث موضع التشغيل ويُفحص الوصول لنهاية الجملة
TICK_MS = 200


def audio_duration(path):
    """مدة الملف بالثواني بقراءة معلوماته فقط (بدون فك الصوت كله)"""
    try:
        import av
        with av.open(path) as container:
            if container.duration:
                return container.duration / 1_000_000
            stream = container.streams.audio[0]
            return float(stream.duration * stream.time_base) if stream.duration else 0.0
    except Exception:
        return 0.0


class AudioPlayerPanel(wx.Panel):
    """
    مشغّل المراجعة: تشغيل/إيقاف مؤقت، إيقاف، شريط موضع قابل للتحريك مع الوقت،
    والتوقف تلقائياً في آخر الجملة عند تشغيل جملة واحدة.
    """

    def __init__(self, parent, i18n: LocalizationManager, on_finished=None):
        super().__init__(parent)
        self.i18n = i18n
        self.is_playing = False
        self.current_audio = None
        self.on_finished = on_finished
        self.duration = 0.0
        self._offset = 0.0      # الثانية التي بدأ منها آخر تشغيل (pygame يعطي الزمن منذ بدء التشغيل فقط)
        self._stop_at = None    # نهاية الجملة عند تشغيل جملة واحدة
        self._dragging = False
        self.setup_ui()
        # متابعة الموضع، ونهاية الجملة، وانتهاء الملف من تلقاء نفسه
        self._timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_tick, self._timer)
        self._timer.Start(TICK_MS)

    # ------------------------------------------------------------------ الواجهة
    def setup_ui(self):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_play = wx.Button(self, label=self.i18n.get("tooltip_play_btn"))
        self.btn_stop = wx.Button(self, label=self.i18n.get("tooltip_stop_btn"))
        # العنوان قبل الشريط مباشرة ليقرأه قارئ الشاشة كاسم له. قيمة الشريط = الثانية الحالية
        self.lbl_position = wx.StaticText(self, label=self.i18n.get("lbl_playback_position"))
        self.slider = wx.Slider(self, minValue=0, maxValue=1, style=wx.SL_HORIZONTAL)
        self.lbl_time = wx.StaticText(self, label="00:00 / 00:00")

        self.btn_play.Bind(wx.EVT_BUTTON, self.on_play)
        self.btn_stop.Bind(wx.EVT_BUTTON, self.on_stop)
        self.slider.Bind(wx.EVT_SCROLL_THUMBTRACK, self._on_drag)
        self.slider.Bind(wx.EVT_SCROLL_THUMBRELEASE, self._on_slider_released)
        # الأسهم و PageUp/PageDown على الشريط (من لوحة المفاتيح) تنقل الموضع مباشرة
        for evt in (wx.EVT_SCROLL_LINEUP, wx.EVT_SCROLL_LINEDOWN, wx.EVT_SCROLL_PAGEUP,
                    wx.EVT_SCROLL_PAGEDOWN, wx.EVT_SCROLL_TOP, wx.EVT_SCROLL_BOTTOM):
            self.slider.Bind(evt, self._on_slider_released)

        sizer.Add(self.btn_play, 0, wx.ALL, 5)
        sizer.Add(self.btn_stop, 0, wx.ALL, 5)
        sizer.Add(self.lbl_position, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(self.slider, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.lbl_time, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.SetSizer(sizer)

    def _update_play_label(self):
        key = "tooltip_pause_btn" if self.is_playing else "tooltip_play_btn"
        self.btn_play.SetLabel(self.i18n.get(key))
        icons.button(self.btn_play, "pause" if self.is_playing else "play")

    def apply_icons(self):
        self._update_play_label()
        icons.button(self.btn_stop, "stop")

    def refresh_ui_texts(self):
        self._update_play_label()
        self.btn_stop.SetLabel(self.i18n.get("tooltip_stop_btn"))
        self.lbl_position.SetLabel(self.i18n.get("lbl_playback_position"))
        self.Layout()

    # ------------------------------------------------------------------ الموضع
    def position(self):
        """الثانية الحالية في الملف"""
        try:
            if pygame.mixer.get_init() and self.current_audio and self.is_playing:
                elapsed = pygame.mixer.music.get_pos()
                if elapsed >= 0:
                    return min(self._offset + elapsed / 1000.0, self.duration or float("inf"))
        except Exception:
            pass
        return self._offset

    def _show_position(self, pos):
        if not self._dragging:
            self.slider.SetValue(int(pos))
        self.lbl_time.SetLabel(f"{format_clock(pos)} / {format_clock(self.duration)}")

    def _on_tick(self, event):
        if not self.current_audio or not self.is_playing:
            return
        pos = self.position()
        self._show_position(pos)
        # تشغيل جملة واحدة: توقف مؤقت في آخرها (F3 يكمل بعدها لو أراد المستخدم)
        if self._stop_at is not None and pos >= self._stop_at:
            self._stop_at = None
            self._pause()
            return
        try:
            busy = pygame.mixer.get_init() and pygame.mixer.music.get_busy()
        except Exception:
            busy = False
        if not busy:
            # انتهى الملف من تلقاء نفسه
            self.is_playing = False
            self._offset = self.duration
            self._update_play_label()
            if self.on_finished:
                self.on_finished()

    def _on_drag(self, event):
        self._dragging = True
        self.lbl_time.SetLabel(f"{format_clock(self.slider.GetValue())} / {format_clock(self.duration)}")

    def _on_slider_released(self, event):
        self._dragging = False
        self.seek(self.slider.GetValue())

    # ------------------------------------------------------------------ التشغيل
    def _ensure_mixer(self):
        if pygame.mixer.get_init():
            return True, None
        try:
            pygame.mixer.init()
            return True, None
        except Exception as e:
            log_error(f"Audio device init failed: {e}")
            return False, str(e)

    def _start_at(self, seconds):
        try:
            pygame.mixer.music.play(start=seconds)
        except pygame.error:
            # بعض الصيغ لا تدعم البدء من منتصف الملف مباشرة، فنجرب القفز بعد بدء التشغيل
            pygame.mixer.music.play()
            if seconds:
                pygame.mixer.music.set_pos(seconds)
        self._offset = seconds

    def load_and_play(self, path, start_time=0, end_time=None):
        """تشغيل الملف من ثانية محددة، والتوقف عند end_time لو حُدد. ترجع (نجح؟، رسالة الخطأ)"""
        ok, error = self._ensure_mixer()
        if not ok:
            return False, error
        try:
            if path != self.current_audio:
                try:
                    pygame.mixer.music.load(path)
                except pygame.error:
                    # صيغ مثل m4a و aac لا يشغلها pygame، فنحولها لنسخة wav مؤقتة ونشغلها
                    pygame.mixer.music.load(self._playable_copy(path))
                self.current_audio = path
                self.duration = audio_duration(path)
                self.slider.SetRange(0, max(1, int(self.duration)))
            self._start_at(start_time or 0)
            self._stop_at = end_time
            self.is_playing = True
            self._update_play_label()
            self._show_position(start_time or 0)
            return True, None
        except Exception as e:
            log_error(f"Playback failed for {path}: {e}")
            self.current_audio = None
            self.is_playing = False
            self._update_play_label()
            return False, str(e)

    def seek(self, seconds):
        """الانتقال لثانية معينة. التحريك اليدوي يلغي التوقف عند آخر الجملة"""
        if not self.current_audio:
            return
        seconds = max(0.0, min(float(seconds), max(0.0, self.duration - 0.5)))
        self._stop_at = None
        was_playing = self.is_playing
        self._start_at(seconds)
        if not was_playing:
            pygame.mixer.music.pause()
        self._show_position(seconds)

    def seek_relative(self, delta):
        self.seek(self.position() + delta)

    def _pause(self):
        self._offset = self.position()
        pygame.mixer.music.pause()
        self.is_playing = False
        self._update_play_label()

    def on_play(self, event):
        if not self.current_audio or not pygame.mixer.get_init():
            return
        if self.is_playing:
            self._pause()
            return
        # الاستئناف يكمل بعد نهاية الجملة (المستخدم طلب الاستمرار صراحة)
        self._stop_at = None
        self._start_at(0 if self._offset >= self.duration - 0.3 else self._offset)
        self.is_playing = True
        self._update_play_label()

    def on_stop(self, event):
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception as e:
            log_error(f"Stopping playback failed: {e}")
        self.is_playing = False
        self._stop_at = None
        self._offset = 0.0
        if self.current_audio:
            self._show_position(0)
        self._update_play_label()

    # ------------------------------------------------------------------ الصيغ غير المدعومة
    def _playable_copy(self, path):
        """تحويل الملف لـ wav مؤقت (مرة واحدة لكل ملف، ويُعاد استخدامه طالما الملف الأصلي لم يتغير)"""
        key = hashlib.md5(f"{os.path.abspath(path)}|{os.path.getmtime(path)}".encode("utf-8")).hexdigest()
        target = os.path.join(self._cache_dir(), f"{key}.wav")
        if os.path.isfile(target):
            return target

        from faster_whisper.audio import decode_audio
        busy = wx.BusyInfo(self.i18n.get("status_preparing_audio"))
        try:
            samples = decode_audio(path, sampling_rate=PLAYBACK_RATE)
            pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
            tmp = target + ".part"
            with wave.open(tmp, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(PLAYBACK_RATE)
                w.writeframes(pcm.tobytes())
            os.replace(tmp, target)
        finally:
            del busy
        return target

    @staticmethod
    def _cache_dir():
        d = os.path.join(tempfile.gettempdir(), "audio_transcriber_playback")
        os.makedirs(d, exist_ok=True)
        return d

    def cleanup(self):
        self._timer.Stop()
        self.on_stop(None)
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass
        # حذف النسخ المؤقتة التي أنشأها البرنامج للتشغيل
        shutil.rmtree(os.path.join(tempfile.gettempdir(), "audio_transcriber_playback"), ignore_errors=True)
