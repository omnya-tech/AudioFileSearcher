"""
عمليات المراجعة على المقاطع: دمج جملتين، وتقسيم جملة عند موضع في نصها.
المقطع: (نص التوقيت للعرض، النص، البداية، النهاية، قائمة الكلمات بتوقيتاتها)
"""
from core.time_utils import format_range


def merge(first, second):
    """دمج جملة مع التي بعدها: النص متصل، والتوقيت من بداية الأولى لنهاية الثانية"""
    text = f"{first[1].strip()} {second[1].strip()}".strip()
    words = list(first[4] or []) + list(second[4] or []) if len(first) > 4 and len(second) > 4 else []
    return (format_range(first[2], second[3]), text, first[2], second[3], words)


def split(seg, char_pos):
    """
    تقسيم جملة عند موضع حرف في نصها. ترجع (الأولى، الثانية) أو None لو الموضع في أول النص أو آخره.
    وقت التقسيم: بداية أول كلمة في الجزء الثاني لو توقيتات الكلمات متاحة وتطابق النص،
    وإلا تقدير بنسبة طول النص (أدق المتاح بدون توقيتات).
    """
    text = seg[1]
    left, right = text[:char_pos].strip(), text[char_pos:].strip()
    if not left or not right:
        return None
    start, end = seg[2], seg[3]
    words = list(seg[4]) if len(seg) > 4 and seg[4] else []

    k = len(left.split())
    if words and len(words) == len(text.split()) and 0 < k < len(words):
        cut = float(words[k]["start"])
        first_words, second_words = words[:k], words[k:]
    else:
        cut = start + (end - start) * (len(left) / max(1, len(left) + len(right)))
        first_words, second_words = [], []
    cut = min(max(cut, start), end)
    return ((format_range(start, cut), left, start, cut, first_words),
            (format_range(cut, end), right, cut, end, second_words))
