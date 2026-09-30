def format_clock(seconds):
    """تحويل الثواني إلى صيغة (دقائق:ثواني) أو (ساعات:دقائق:ثواني) للمقاطع الطويلة"""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def format_range(start, end):
    # شرطة عادية بدل السهم: السهم يظهر معكوساً ومربكاً في الواجهة العربية
    return f"{format_clock(start)} - {format_clock(end)}"


def format_srt_time(seconds, separator=","):
    """صيغة التوقيت في ملفات الترجمة: 00:01:02,345 (أو بنقطة لملفات VTT)"""
    total_ms = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(total_ms, 3600 * 1000)
    minutes, rem = divmod(rem, 60 * 1000)
    secs, msecs = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{msecs:03d}"
