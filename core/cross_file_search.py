import os
import re
import json
from core.time_utils import format_range

AUDIO_EXTENSIONS = ('.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus', '.rm')
SEARCHABLE_EXTENSIONS = ('.srt', '.vtt', '.txt', '.json')

_TIME_LINE_RE = re.compile(r'(\d+:)?(\d{1,2}):(\d{1,2})[.,](\d{1,3})\s*-->\s*(\d+:)?(\d{1,2}):(\d{1,2})[.,](\d{1,3})')


def _to_seconds(h, m, s, ms):
    h = int(h.rstrip(':')) if h else 0
    return h * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, '0')) / 1000.0


def read_text_file(path):
    """قراءة ملف نصي مع التعامل مع علامة BOM ونهايات أسطر ويندوز"""
    with open(path, 'r', encoding='utf-8-sig', errors='replace') as f:
        return f.read().replace('\r\n', '\n').replace('\r', '\n')


def parse_subtitles(path):
    """قراءة ملف SRT أو VTT وإرجاع قائمة (بداية، نهاية، نص)"""
    content = read_text_file(path)
    segments = []
    for block in re.split(r'\n\s*\n', content.strip()):
        lines = [l for l in block.strip().split('\n')]
        for i, line in enumerate(lines):
            m = _TIME_LINE_RE.search(line)
            if m:
                start = _to_seconds(*m.group(1, 2, 3, 4))
                end = _to_seconds(*m.group(5, 6, 7, 8))
                text = '\n'.join(lines[i + 1:]).strip()
                if text:
                    segments.append((start, end, text))
                break
    return segments


def find_audio_for(transcript_path):
    """البحث عن ملف صوتي بنفس اسم ملف التفريغ في نفس المجلد"""
    folder = os.path.dirname(transcript_path)
    base = os.path.splitext(os.path.basename(transcript_path))[0]
    for ext in AUDIO_EXTENSIONS:
        for candidate in (ext, ext.upper()):
            p = os.path.join(folder, base + candidate)
            if os.path.isfile(p):
                return p
    return None


class CrossFileSearcher:
    def search_in_directory(self, directory, query, should_stop=None):
        results = []
        if not os.path.isdir(directory) or not query:
            return results

        query_lower = query.lower()
        for root, _, files in os.walk(directory):
            for f in files:
                if should_stop and should_stop():
                    return results
                if f.lower().endswith(SEARCHABLE_EXTENSIONS):
                    file_path = os.path.join(root, f)
                    try:
                        results.extend(self._search_file(file_path, query_lower))
                    except Exception:
                        # ملف تالف أو بصيغة غير متوقعة: نتخطاه ونكمل البحث
                        continue
        return results

    def _make_result(self, file_path, text, start=None, end=None, line_no=None):
        if start is not None:
            time_str = format_range(start, end if end is not None else start)
        else:
            time_str = f"#{line_no}"
        return {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "time_str": time_str,
            "start": start,
            "text": text,
        }

    def _search_file(self, file_path, query):
        results = []
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.json':
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            if not isinstance(data, list):
                return results
            for item in data:
                if not isinstance(item, dict):
                    continue
                text = str(item.get('text', ''))
                if query in text.lower():
                    start = item.get('start')
                    end = item.get('end')
                    start = float(start) if isinstance(start, (int, float)) else None
                    end = float(end) if isinstance(end, (int, float)) else None
                    results.append(self._make_result(file_path, text, start, end))

        elif ext in ('.srt', '.vtt'):
            for start, end, text in parse_subtitles(file_path):
                if query in text.lower():
                    results.append(self._make_result(file_path, text.replace('\n', ' '), start, end))

        else:
            for i, line in enumerate(read_text_file(file_path).split('\n'), 1):
                if query in line.lower():
                    results.append(self._make_result(file_path, line.strip(), line_no=i))
        return results
