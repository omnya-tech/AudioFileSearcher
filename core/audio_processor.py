import threading
import time
import wx
import os
import gc
import math
import psutil
from faster_whisper import WhisperModel
from core.text_corrector import TextCorrector
from core.transcription_logger import TranscriptionLogger, ErrorDetector
from core.model_manager import ModelManager
from core.logger import log_error
from core.time_utils import format_range

EVT_RESULT_ID = wx.NewIdRef()

def EVT_RESULT(win, func):
    win.Connect(-1, -1, EVT_RESULT_ID, func)

class ResultEvent(wx.PyEvent):
    def __init__(self, status, data=None, source=None):
        super().__init__()
        self.SetEventType(EVT_RESULT_ID)
        self.status = status
        self.data = data
        # الخيط الذي أرسل الحدث، حتى تتجاهل الواجهة أحداث عملية تم إلغاؤها
        self.source = source

class TranscriptionAborted(Exception):
    pass

class ModelNotInstalledError(Exception):
    pass

# أي كلمة احتمالها أقل من هذا تُعتبر مشكوكاً فيها وتحتاج مراجعة
WEAK_WORD_THRESHOLD = 0.75

_CACHED_MODEL = None
_CACHED_CONFIG = None
# عملية تفريغ واحدة فقط في نفس الوقت (لو أُلغيت عملية وبدأت أخرى، تنتظر الجديدة انتهاء القديمة)
_RUN_LOCK = threading.Lock()

class TranscriptionThread(threading.Thread):
    def __init__(self, parent, audio_file, i18n):
        super().__init__(daemon=True)
        self.parent = parent
        self.audio_file = audio_file
        self.i18n = i18n
        self.settings = parent.settings
        self.corrections_dict = dict(self.settings.get("custom_dictionary", {}) or {})
        self.corrector = TextCorrector(self.corrections_dict)
        self.logger = TranscriptionLogger(i18n)
        self.error_detector = ErrorDetector(i18n)
        self.start_time = None
        self._abort = threading.Event()
        self.start()

    def abort(self):
        self._abort.set()

    @property
    def aborted(self):
        return self._abort.is_set()

    def _post(self, status, data=None):
        if self.aborted:
            return
        try:
            wx.PostEvent(self.parent, ResultEvent(status, data, source=self))
        except RuntimeError:
            # النافذة الرئيسية أُغلقت
            self._abort.set()

    def _check_abort(self):
        if self.aborted:
            raise TranscriptionAborted()

    def _set_priority(self, low):
        try:
            p = psutil.Process(os.getpid())
            if os.name == 'nt': p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if low else psutil.NORMAL_PRIORITY_CLASS)
            else: p.nice(10 if low else 0)
        except Exception:
            pass

    def _read_options(self):
        s = self.settings
        transcription_lang = s.get("transcription_language", "ar")
        auto_detect_lang = s.get("auto_detect_language", False) or transcription_lang == "auto"

        if s.get("user_mode", "beginner") == "beginner":
            # الوضع المبسط: إعدادات ثابتة آمنة، لكن مع احترام لغة الملف التي اختارها المستخدم
            return {
                "compute_type": "int8", "beam_size": 2, "temperature": 0.0,
                "transcription_lang": transcription_lang, "auto_detect_lang": auto_detect_lang,
                # فلتر الصمت يتبع اختيار المستخدم: قد يقطع نهايات المدود الطويلة في التلاوة
                "vad_filter": s.get("vad_filter", False), "word_timestamps": True, "prompt": None,
                "no_speech_threshold": 0.6, "threads_count": 2,
            }

        custom_prompt = s.get("initial_prompt", "") or ""
        return {
            "compute_type": s.get("compute_type", "int8"),
            "beam_size": int(s.get("beam_size", 5)),
            "temperature": float(s.get("temperature", 0.0)),
            "transcription_lang": transcription_lang,
            "auto_detect_lang": auto_detect_lang,
            "vad_filter": s.get("vad_filter", False),
            "word_timestamps": s.get("word_timestamps", True),
            "prompt": custom_prompt if custom_prompt.strip() else None,
            "no_speech_threshold": float(s.get("no_speech_threshold", 0.6)),
            "threads_count": int(s.get("threads", 0)),
        }

    def _resolve_model(self):
        """تحديد مصدر النموذج: مسار محلي، أو اسم المستودع للتحميل من الإنترنت"""
        model_size = self.settings.get("model_size", "large-v3")
        use_local_model = self.settings.get("use_local_model", False)
        local_model_path = self.settings.get("local_model_path", "")

        if local_model_path and ModelManager.is_valid_model_dir(local_model_path):
            return local_model_path, True

        local = ModelManager.find_local_model(model_size)
        if local:
            return local, True

        if use_local_model:
            # المستخدم طلب العمل بدون إنترنت والنموذج غير موجود على الجهاز
            raise ModelNotInstalledError(self.i18n.get("msg_model_not_installed", model=model_size))

        return ModelManager.to_repo_id(model_size), False

    def _load_model(self, model_target, is_local, opts):
        global _CACHED_MODEL, _CACHED_CONFIG
        device = self.settings.get("device", "cpu")
        keep_in_memory = self.settings.get("keep_in_memory", True)

        model_kwargs = {"device": device, "compute_type": opts["compute_type"], "num_workers": 1}
        if opts["threads_count"] > 0: model_kwargs["cpu_threads"] = opts["threads_count"]
        if is_local: model_kwargs["local_files_only"] = True

        current_config = (model_target, device, opts["compute_type"], opts["threads_count"])

        if keep_in_memory and _CACHED_MODEL is not None and _CACHED_CONFIG == current_config:
            return _CACHED_MODEL

        # تحرير النموذج القديم قبل تحميل الجديد لتوفير الذاكرة
        _CACHED_MODEL = None
        _CACHED_CONFIG = None
        gc.collect()

        self._post("loading_local" if is_local else "loading")
        model = WhisperModel(model_target, **model_kwargs)
        if keep_in_memory:
            _CACHED_MODEL = model
            _CACHED_CONFIG = current_config
        return model

    def run(self):
        with _RUN_LOCK:
            self._set_priority(low=True)
            try:
                self._run()
            except TranscriptionAborted:
                pass
            except ModelNotInstalledError as e:
                self._post("error", str(e))
            except Exception as e:
                log_error(f"Transcription failed for {self.audio_file}: {e}")
                self._post("error", str(e))
            finally:
                self._set_priority(low=False)

    def _run(self):
        if not os.path.isfile(self.audio_file):
            raise FileNotFoundError(self.i18n.get("msg_audio_not_found"))

        opts = self._read_options()
        model_target, is_local = self._resolve_model()
        self._check_abort()

        model = self._load_model(model_target, is_local, opts)
        self._check_abort()

        self._post("transcribing")
        self.start_time = time.time()

        enable_correction = self.settings.get("enable_correction", True)
        use_hotwords = self.settings.get("use_hotwords", True)
        correction_level = self.settings.get("correction_level", "medium")
        dynamic_hotwords = self.corrector.get_hotwords() if enable_correction and use_hotwords else None

        transcribe_params = {
            "audio": self.audio_file,
            "beam_size": opts["beam_size"],
            "temperature": opts["temperature"],
            "initial_prompt": opts["prompt"],
            "hotwords": dynamic_hotwords,
            "vad_filter": opts["vad_filter"],
            "word_timestamps": opts["word_timestamps"],
            "condition_on_previous_text": False,
            "no_speech_threshold": opts["no_speech_threshold"],
            "compression_ratio_threshold": 2.4
        }
        if not opts["auto_detect_lang"]: transcribe_params["language"] = opts["transcription_lang"]

        segments, info = model.transcribe(**transcribe_params)

        total_duration = info.duration
        results = []
        total_segments, flagged_segments, total_confidence = 0, 0, 0.0
        segment_details = []
        last_percent = -1

        for segment in segments:
            self._check_abort()
            if total_duration > 0:
                percent = min(int((segment.end / total_duration) * 100), 100)
                if percent != last_percent:
                    last_percent = percent
                    self._post("progress", percent)

            total_segments += 1
            words = getattr(segment, 'words', None) or []
            if words:
                # الدقة من احتمال كل كلمة: avg_logprob واحد لكل نافذة 30 ثانية فلا يميز بين المقاطع
                confidence = sum(float(w.probability) for w in words) / len(words) * 100
            else:
                try: confidence = math.exp(segment.avg_logprob) * 100
                except (OverflowError, ValueError, TypeError): confidence = 0.0
            total_confidence += confidence

            # كلمة واحدة ضعيفة تكفي لطلب مراجعة المقطع، حتى لو باقي كلماته ممتازة
            weak_words = [w.word.strip() for w in words if float(w.probability) < WEAK_WORD_THRESHOLD]
            if confidence < 75.0 or weak_words:
                flagged_segments += 1
                status = self.i18n.get("status_quality_poor")
                if weak_words:
                    status += " - " + self.i18n.get("report_weak_words", words="، ".join(weak_words))
            else:
                status = self.i18n.get("status_quality_excellent")

            segment_details.append({
                "time": format_range(segment.start, segment.end),
                "status": status,
                "confidence": f"{int(confidence)}%",
                "flagged": bool(confidence < 75.0 or weak_words),
            })

            raw_text = segment.text.strip()
            corrected_text = self.corrector.correct(raw_text, level=correction_level) if enable_correction else raw_text

            words_data = []
            if opts["word_timestamps"] and getattr(segment, 'words', None):
                words_data = [{"word": w.word, "start": float(w.start), "end": float(w.end), "probability": round(float(w.probability), 3)} for w in segment.words]

            results.append((format_range(segment.start, segment.end), corrected_text, segment.start, segment.end, words_data))

        self._check_abort()

        elapsed = round(time.time() - self.start_time, 2)
        avg_confidence = int(total_confidence / total_segments) if total_segments > 0 else 0

        report_model = os.path.basename(model_target) if is_local else model_target

        detected_errors = self.error_detector.detect_errors(results)
        detected_warnings = self.error_detector.detect_warnings(results)

        report = self.logger.create_report(
            file_path=self.audio_file,
            segments=results,
            start_time=self.start_time,
            end_time=time.time(),
            model_used=report_model,
            errors=detected_errors,
            warnings=detected_warnings,
            audio_duration=total_duration,
            extra={
                "score": avg_confidence,
                "flagged_segments": flagged_segments,
                "segment_details": segment_details,
                "language": getattr(info, "language", None),
            }
        )

        if not self.settings.get("keep_in_memory", True):
            del model
            gc.collect()

        self._post("done", {"results": results, "time": elapsed, "report": report})
