"""
توليد أيقونة البرنامج (assets/app.ico) بعدة أحجام: مربع أزرق بحواف دائرية، ميكروفون أبيض، وموجات صوت.
التشغيل مرة واحدة عند تغيير التصميم:  python tools/make_app_icon.py
"""
import io
import os
import struct
import sys

import wx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from gui.icons import ICON_FONT  # noqa: E402

SIZES = (16, 24, 32, 48, 64, 128, 256)


def draw_icon(size):
    img = wx.Image(size, size)
    img.InitAlpha()
    for x in range(size):
        for y in range(size):
            img.SetAlpha(x, y, 0)
    bmp = wx.Bitmap(img)
    dc = wx.MemoryDC(bmp)
    gc = wx.GraphicsContext.Create(dc)

    m = size * 0.04
    r = size * 0.22
    path = gc.CreatePath()
    path.AddRoundedRectangle(m, m, size - 2 * m, size - 2 * m, r)
    gc.SetBrush(gc.CreateLinearGradientBrush(0, 0, size, size, wx.Colour(21, 101, 192), wx.Colour(66, 165, 245)))
    gc.SetPen(wx.TRANSPARENT_PEN)
    gc.FillPath(path)

    # الميكروفون من خط أيقونات ويندوز
    font = wx.Font(wx.FontInfo(wx.Size(0, int(size * 0.58))).FaceName(ICON_FONT))
    gc.SetFont(gc.CreateFont(font, wx.WHITE))
    glyph = ""
    tw, th = gc.GetTextExtent(glyph)[:2]
    cx, cy = size * 0.40, size * 0.5
    gc.DrawText(glyph, cx - tw / 2, cy - th / 2)

    # موجات الصوت على يمين الميكروفون (تُحذف في الأحجام الصغيرة حتى لا تزدحم)
    if size >= 32:
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        for i, (rad, alpha) in enumerate(((0.17, 255), (0.27, 190))):
            pen = gc.CreatePen(wx.GraphicsPenInfo(wx.Colour(255, 255, 255, alpha)).Width(max(1.5, size * 0.045)).Cap(wx.CAP_ROUND))
            gc.SetPen(pen)
            arc = gc.CreatePath()
            arc.AddArc(cx + size * 0.08, cy - size * 0.02, size * rad, -0.9, 0.9, True)
            gc.StrokePath(arc)
    del gc
    dc.SelectObject(wx.NullBitmap)
    return bmp


def png_bytes(bmp):
    stream = io.BytesIO()
    bmp.ConvertToImage().SaveFile(stream, wx.BITMAP_TYPE_PNG)
    return stream.getvalue()


def write_ico(path, bitmaps):
    """ملف ICO بصور PNG داخله (مدعوم منذ ويندوز فيستا) لكل الأحجام"""
    pngs = [(b.GetWidth(), png_bytes(b)) for b in bitmaps]
    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries, data = b"", b""
    for size, png in pngs:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    with open(path, "wb") as f:
        f.write(header + entries + data)


if __name__ == "__main__":
    app = wx.App(False)
    bitmaps = [draw_icon(s) for s in SIZES]
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    write_ico(os.path.join(ROOT, "assets", "app.ico"), bitmaps)
    bitmaps[-1].SaveFile(os.path.join(ROOT, "assets", "app_256.png"), wx.BITMAP_TYPE_PNG)
    print("assets/app.ico written")
