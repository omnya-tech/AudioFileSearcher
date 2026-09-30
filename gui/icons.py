"""
أيقونات البرنامج، مرسومة من خط الأيقونات الرسمي في ويندوز (Segoe MDL2 Assets):
شكل موحد مع واجهة ويندوز، واضحة في أي حجم، ولا تحتاج ملفات صور.
الأيقونة زخرفة فقط: اسم كل زر وقائمة يبقى نصاً كما هو، فلا يتأثر قارئ الشاشة.
"""
import wx

ICON_FONT = "Segoe MDL2 Assets"

# الاسم الدلالي -> (رمز الخط، نوع اللون)
GLYPHS = {
    "audio_file": ("", "normal"),
    "folder": ("", "normal"),
    "subtitle": ("", "normal"),
    "save": ("", "accent"),
    "exit": ("", "normal"),
    "search": ("", "normal"),
    "edit": ("", "normal"),
    "play": ("", "good"),
    "back": ("", "normal"),
    "forward": ("", "normal"),
    "merge": ("", "normal"),
    "split": ("", "normal"),
    "pause": ("", "normal"),
    "stop": ("", "danger"),
    "progress": ("", "normal"),
    "history": ("", "normal"),
    "settings": ("", "normal"),
    "download": ("", "accent"),
    "dictionary": ("", "normal"),
    "keyboard": ("", "normal"),
    "info": ("", "normal"),
    "transcribe": ("", "good"),
    "add": ("", "good"),
    "delete": ("", "danger"),
    "clear": ("", "danger"),
    "ok": ("", "accent"),
    "cancel": ("", "normal"),
    "close": ("", "normal"),
    "reset": ("", "normal"),
    "suggest": ("", "normal"),
    "hide": ("", "normal"),
    "engine": ("", "normal"),
    "advanced": ("", "normal"),
    "appearance": ("", "normal"),
    "report": ("", "normal"),
}

PALETTE = {
    "light": {"normal": (45, 45, 45), "accent": (0, 95, 184), "good": (16, 124, 16), "danger": (196, 43, 28)},
    "dark": {"normal": (230, 230, 230), "accent": (96, 176, 255), "good": (108, 203, 95), "danger": (255, 153, 164)},
}

_theme = "light"
_cache = {}
# المظهر الداكن الأصلي في ويندوز (يُفعَّل عند بدء البرنامج): كل النوافذ والقوائم داكنة، فكل الأيقونات بألوان الداكن
native_dark = False


def scale():
    """نسبة تكبير الشاشة الأساسية في ويندوز (1.0 = 100%، 1.5 = 150%)"""
    try:
        return max(1.0, wx.Display(0).GetScaleFactor())
    except Exception:
        return 1.0


def px(size):
    """حجم الأيقونة بالبكسل الفعلي: 16 على شاشة 100% تصبح 24 على شاشة 150%"""
    return int(round(size * scale()))


def set_theme(theme):
    global _theme
    _theme = "dark" if theme == "dark" else "light"


def available():
    return wx.FontEnumerator.IsValidFacename(ICON_FONT)


def render_glyph(glyph, size, colour):
    """رسم رمز من الخط كصورة شفافة بلون محدد (الحواف ناعمة من شدة الرسم نفسه)"""
    bmp = wx.Bitmap(size, size, 24)
    dc = wx.MemoryDC(bmp)
    dc.SetBackground(wx.Brush(wx.BLACK))
    dc.Clear()
    dc.SetFont(wx.Font(wx.FontInfo(wx.Size(0, int(size * 0.85))).FaceName(ICON_FONT)))
    dc.SetTextForeground(wx.WHITE)
    tw, th = dc.GetTextExtent(glyph)
    dc.DrawText(glyph, (size - tw) // 2, (size - th) // 2)
    dc.SelectObject(wx.NullBitmap)

    mask = bmp.ConvertToImage()
    img = wx.Image(size, size)
    img.SetData(bytes(colour) * (size * size))
    # شدة البياض في الرسم = درجة الشفافية
    img.SetAlpha(bytes(mask.GetData()[0::3]))
    return wx.Bitmap(img)


def get(name, size=16, theme=None):
    if name not in GLYPHS or not available():
        return wx.NullBitmap
    theme = "dark" if native_dark else (theme or _theme)
    size = px(size)
    key = (name, size, theme)
    if key not in _cache:
        glyph, kind = GLYPHS[name]
        _cache[key] = render_glyph(glyph, size, PALETTE[theme][kind])
    return _cache[key]


def button(btn, name, theme=None, size=16):
    """أيقونة بجانب نص الزر (النص يبقى كما هو لقارئ الشاشة)"""
    bmp = get(name, size, theme)
    if bmp.IsOk():
        btn.SetBitmap(bmp)
        btn.SetBitmapMargins(btn.FromDIP(4), 0)
    return btn


def menu_item(menu, item_id, label, name):
    """إنشاء عنصر قائمة بأيقونة (الأيقونة يجب ضبطها قبل الإضافة للقائمة في ويندوز)"""
    item = wx.MenuItem(menu, item_id, label)
    # قوائم ويندوز فاتحة دائماً حتى لو البرنامج بالمظهر الداكن، فأيقوناتها بألوان المظهر الفاتح
    bmp = get(name, 16, theme="light")
    if bmp.IsOk():
        item.SetBitmap(bmp)
    return menu.Append(item)


def app_icons():
    """أيقونة البرنامج بكل أحجامها (شريط المهام، عنوان النافذة، Alt+Tab)"""
    import os
    from core.paths import RESOURCE_DIR
    path = os.path.join(RESOURCE_DIR, "assets", "app.ico")
    return wx.IconBundle(path, wx.BITMAP_TYPE_ICO) if os.path.isfile(path) else None


def set_window_icon(window):
    bundle = app_icons()
    if bundle is not None:
        window.SetIcons(bundle)


def image_list(names, size=16, theme=None):
    """قائمة صور لتبويبات النوافذ"""
    il = wx.ImageList(px(size), px(size))
    for n in names:
        bmp = get(n, size, theme)
        il.Add(bmp if bmp.IsOk() else wx.Bitmap(px(size), px(size)))
    return il

