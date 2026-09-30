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

# جودة كافية للاستماع للكلام، مع حجم معقول للنسخة المؤقتة
PLAYBACK_RATE = 22050

class AudioPlayerPanel(wx.Panel):
    def __init__(self, parent, i18n: LocalizationManager):
        super().__init__(parent)
        self.i18n = i18n
        self.is_playing = False
        self.current_audio = None
        self.setup_ui()

    def setup_ui(self):
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_play = wx.Button(self, label=self.i18n.get("tooltip_play_btn", "▶ Play"))
        self.btn_stop = wx.Button(self, label=self.i18n.get("tooltip_stop_btn", "■ Stop"))

        self.btn_play.Bind(wx.EVT_BUTTON, self.on_play)
        self.btn_stop.Bind(wx.EVT_BUTTON, self.on_stop)

        sizer.Add(self.btn_play, 0, wx.ALL, 5)
        sizer.Add(self.btn_stop, 0, wx.ALL, 5)
        self.SetSizer(sizer)

    def _update_play_label(self):
        key = "tooltip_pause_btn" if self.is_playing else "tooltip_play_btn"
        self.btn_play.SetLabel(self.i18n.get(key))

    def refresh_ui_texts(self):
        self._update_play_label()
        self.btn_stop.SetLabel(self.i18n.get("tooltip_stop_btn"))
        self.Layout()

    def load_and_play(self, path, start_time=0):
        """تشغيل الملف من ثانية محددة. ترجع (نجح؟، رسالة الخطأ)"""
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception as e:
                log_error(f"Audio device init failed: {e}")
                return False, str(e)
        try:
            try:
                pygame.mixer.music.load(path)
            except pygame.error:
                # صيغ مثل m4a و aac لا يشغلها pygame، فنحولها لنسخة wav مؤقتة ونشغلها
                pygame.mixer.music.load(self._playable_copy(path))
            try:
                pygame.mixer.music.play(start=start_time)
            except pygame.error:
                # بعض الصيغ لا تدعم البدء من منتصف الملف مباشرة، فنجرب القفز بعد بدء التشغيل
                pygame.mixer.music.play()
                if start_time:
                    pygame.mixer.music.set_pos(start_time)
            self.current_audio = path
            self.is_playing = True
            self._update_play_label()
            return True, None
        except Exception as e:
            log_error(f"Playback failed for {path}: {e}")
            self.is_playing = False
            self._update_play_label()
            return False, str(e)

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

    def on_play(self, event):
        if not self.current_audio or not pygame.mixer.get_init(): return
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
        else:
            pygame.mixer.music.unpause()
            self.is_playing = True
        self._update_play_label()

    def on_stop(self, event):
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception as e:
            log_error(f"Stopping playback failed: {e}")
        self.is_playing = False
        self._update_play_label()

    def cleanup(self):
        self.on_stop(None)
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass
        # حذف النسخ المؤقتة التي أنشأها البرنامج للتشغيل
        shutil.rmtree(os.path.join(tempfile.gettempdir(), "audio_transcriber_playback"), ignore_errors=True)
