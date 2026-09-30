import wx
from gui import icons, widgets
from core.i18n import LocalizationManager

class EditSegmentDialog(wx.Dialog):
    """تعديل نص مقطع واحد، مع إمكانية سماعه أثناء التعديل"""

    def __init__(self, parent, i18n: LocalizationManager, time_range, text, play_callback=None):
        super().__init__(parent, title=i18n.get("dialog_edit_segment_title"), size=(560, 300), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.i18n = i18n
        i18n.apply_direction(self)
        widgets.fit_to_screen(self)
        self.play_callback = play_callback
        self.setup_ui(time_range, text)
        self.CenterOnParent()

    def setup_ui(self, time_range, text):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(panel, label=f"{self.i18n.get('list_header_time')}: {time_range}"), 0, wx.ALL, 10)

        self.txt = wx.TextCtrl(panel, value=text, style=wx.TE_MULTILINE)
        font = self.txt.GetFont()
        font.SetPointSize(font.GetPointSize() + 2)
        self.txt.SetFont(font)
        sizer.Add(self.txt, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_play = icons.button(wx.Button(panel, label=self.i18n.get("menu_play_segment") + " (F5)"), "play", theme="light")
        self.btn_play.Enable(self.play_callback is not None)
        btn_ok = icons.button(wx.Button(panel, id=wx.ID_OK, label=self.i18n.get("btn_save")), "save", theme="light")
        btn_cancel = icons.button(wx.Button(panel, id=wx.ID_CANCEL, label=self.i18n.get("btn_cancel")), "cancel", theme="light")
        btn_sizer.Add(self.btn_play, 0, wx.ALL, 5)
        btn_sizer.AddStretchSpacer(1)
        btn_sizer.Add(btn_ok, 0, wx.ALL, 5)
        btn_sizer.Add(btn_cancel, 0, wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(sizer)
        btn_ok.SetDefault()

        self.btn_play.Bind(wx.EVT_BUTTON, self.on_play)
        # F5 للسماع دون ترك مربع الكتابة، و Ctrl+Enter للحفظ (Enter وحده ينزل سطراً)
        id_play, id_save = wx.NewIdRef(), wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.on_play, id=id_play)
        self.Bind(wx.EVT_MENU, lambda e: self.EndModal(wx.ID_OK), id=id_save)
        self.SetAcceleratorTable(wx.AcceleratorTable([
            (wx.ACCEL_NORMAL, wx.WXK_F5, id_play),
            (wx.ACCEL_CTRL, wx.WXK_RETURN, id_save),
        ]))
        wx.CallAfter(self._focus_text)

    def _focus_text(self):
        self.txt.SetFocus()
        self.txt.SetInsertionPointEnd()

    def on_play(self, event):
        if self.play_callback:
            self.play_callback()

    def get_text(self):
        return self.txt.GetValue().strip()
