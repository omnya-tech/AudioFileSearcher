"""أدوات صغيرة مشتركة بين نوافذ البرنامج"""
import wx


def fit_first_column(list_ctrl, min_width=200, column=0):
    """عمود النص يأخذ كل العرض المتبقي، فلا يظهر شريط تمرير أفقي بلا داعٍ"""
    others = sum(list_ctrl.GetColumnWidth(i) for i in range(list_ctrl.GetColumnCount()) if i != column)
    width = list_ctrl.GetClientSize().width - others - 4
    list_ctrl.SetColumnWidth(column, max(min_width, width))


def auto_fit_first_column(list_ctrl, column=0, min_width=200):
    def on_size(event):
        wx.CallAfter(lambda: list_ctrl and fit_first_column(list_ctrl, min_width, column))
        event.Skip()
    list_ctrl.Bind(wx.EVT_SIZE, on_size)


def fit_to_screen(window, margin=20):
    """النافذة لا تكون أبداً أكبر من المساحة المتاحة في الشاشة (بدون شريط المهام)، وإلا يُقص جزء منها"""
    idx = wx.Display.GetFromWindow(window)
    display = wx.Display(idx if idx != wx.NOT_FOUND else 0)
    area = display.GetClientArea()
    w, h = window.GetSize()
    new_w, new_h = min(w, area.width - margin), min(h, area.height - margin)
    if (new_w, new_h) != (w, h):
        window.SetSize((new_w, new_h))


def refit_texts(window):
    """بعد تغيير نصوص الأزرار والعناوين (تغيير اللغة): إعادة حساب مقاساتها حتى لا يُقص النص"""
    for child in window.GetChildren():
        if isinstance(child, (wx.Button, wx.StaticText, wx.CheckBox)):
            child.SetMinSize(wx.DefaultSize)
            child.InvalidateBestSize()
            child.SetMinSize(child.GetBestSize())
        refit_texts(child)
