import json
import os
import threading
from datetime import datetime
from core.paths import LOGS_DIR, ensure_dir
from typing import List, Dict, Any

def log_error(msg):
    print(f"[ERROR]: {msg}")

class TranscriptionLogger:
    def __init__(self, i18n=None):
        self.i18n = i18n
        self.log_dir = LOGS_DIR
        self.history_file = os.path.join(self.log_dir, "transcription_history.json")
        self.file_lock = threading.Lock()

        ensure_dir(self.log_dir)

        self.history = self.load_history()

    def load_history(self) -> List[Dict]:
        with self.file_lock:
            if os.path.exists(self.history_file):
                try:
                    with open(self.history_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    log_error(f"Error loading history: {e}")
                    return []
            return []

    def save_history(self):
        with self.file_lock:
            try:
                with open(self.history_file, 'w', encoding='utf-8') as f:
                    json.dump(self.history, f, ensure_ascii=False, indent=2)
            except Exception as e:
                log_error(f"Error saving history: {e}")

    def create_report(self, file_path: str, segments: List[tuple], start_time: float, end_time: float, model_used: str, errors: List[str] = None, warnings: List[str] = None, audio_duration: float = None, extra: Dict[str, Any] = None) -> Dict[str, Any]:
        duration = end_time - start_time
        total_words = sum(len(seg[1].split()) for seg in segments)
        total_segments = len(segments)

        if audio_duration is None:
            audio_duration = segments[-1][3] if segments else 0
        words_per_minute = (total_words / (audio_duration / 60)) if audio_duration > 0 else 0

        success_status = self.i18n.get("history_status_success") if self.i18n else "success"
        error_status = self.i18n.get("history_status_errors") if self.i18n else "completed_with_errors"

        report = {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "timestamp": datetime.now().isoformat(),
            "model_used": model_used,
            "processing_time": {
                "total_seconds": round(duration, 2),
                "formatted": self.format_duration(duration)
            },
            "audio_info": {
                "duration_seconds": round(audio_duration, 2),
                "duration_formatted": self.format_duration(audio_duration)
            },
            "statistics": {
                "total_segments": total_segments,
                "total_words": total_words,
                "words_per_minute": round(words_per_minute, 2),
                "average_segment_length": round(total_words / total_segments, 2) if total_segments > 0 else 0
            },
            "errors": errors or [],
            "warnings": warnings or [],
            "status": success_status if not errors else error_status
        }
        if extra:
            report.update(extra)

        # التفاصيل الكاملة لكل مقطع تظهر في التقرير فقط، ولا داعي لتضخيم ملف السجل بها
        history_entry = {k: v for k, v in report.items() if k != "segment_details"}

        with self.file_lock:
            self.history.insert(0, history_entry)
            if len(self.history) > 100:
                self.history = self.history[:100]

        self.save_history()
        return report

    def clear_history(self):
        with self.file_lock:
            self.history = []
        self.save_history()

    def format_duration(self, seconds: float) -> str:
        # صيغة رقمية لا تعتمد على لغة الواجهة
        seconds = max(0, int(round(seconds)))
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        return f"{hours:d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"

    def get_history(self, limit: int = 50) -> List[Dict]:
        with self.file_lock: return self.history[:limit]

    def search_history(self, query: str) -> List[Dict]:
        query_lower = query.lower()
        results = []
        with self.file_lock:
            for entry in self.history:
                if (query_lower in entry['file_name'].lower() or query_lower in entry.get('file_path', '').lower()):
                    results.append(entry)
        return results

    def get_statistics(self) -> Dict[str, Any]:
        with self.file_lock:
            if not self.history:
                return {"total_transcriptions": 0, "total_processing_time": 0, "total_words": 0, "total_errors": 0}
            total_time = sum(entry['processing_time']['total_seconds'] for entry in self.history)
            total_words = sum(entry['statistics']['total_words'] for entry in self.history)
            total_errors = sum(len(entry['errors']) for entry in self.history)
            history_length = len(self.history)

        return {
            "total_transcriptions": history_length,
            "total_processing_time": self.format_duration(total_time),
            "total_words": total_words,
            "total_errors": total_errors,
            "average_words_per_transcription": round(total_words / history_length, 2) if history_length > 0 else 0
        }

class ErrorDetector:
    def __init__(self, i18n=None):
        self.i18n = i18n

    def detect_errors(self, segments: List[tuple]) -> List[str]:
        errors = []
        for idx, seg in enumerate(segments, 1):
            text = seg[1]
            if not text or len(text.strip()) < 2:
                err_msg = self.i18n.get("log_err_empty_segment") if self.i18n else f"Segment {idx}: Empty or too short text"
                errors.append(err_msg.format(idx=idx) if '{idx}' in err_msg else err_msg)
                continue
        return errors

    def detect_warnings(self, segments: List[tuple]) -> List[str]:
        warnings = []
        for idx, seg in enumerate(segments, 1):
            end = seg[3]
            if idx < len(segments):
                next_start = segments[idx][2]
                gap = next_start - end
                if gap > 5.0:
                    warn_msg = self.i18n.get("log_warn_long_silence") if self.i18n else f"Segment {idx}: Long silence detected ({gap:.1f}s)"
                    warnings.append(warn_msg.format(idx=idx, gap=gap) if '{idx}' in warn_msg else warn_msg)
        return warnings