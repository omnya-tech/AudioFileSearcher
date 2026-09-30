import wx
from core.i18n import LocalizationManager


class TextDialog(wx.Dialog):
    """نافذة لعرض نص طويل للقراءة فقط. التركيز على النص مباشرة ليقرأه قارئ الشاشة بالأسهم"""

    def __init__(self, parent, i18n: LocalizationManager, title, text):
        super().__init__(parent, title=title, size=(560, 520), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        i18n.apply_direction(self)
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(panel, label=title), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.txt = wx.TextCtrl(panel, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(self.txt, 1, wx.EXPAND | wx.ALL, 10)

        btn_close = wx.Button(panel, id=wx.ID_CANCEL, label=i18n.get("btn_close"))
        sizer.Add(btn_close, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)
        panel.SetSizer(sizer)
        self.CenterOnParent()
        wx.CallAfter(self._focus_start)

    def _focus_start(self):
        self.txt.SetFocus()
        self.txt.SetInsertionPoint(0)
