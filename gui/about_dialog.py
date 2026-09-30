import wx
from gui import icons, widgets
from core.i18n import LocalizationManager

class AboutDialog(wx.Dialog):
    def __init__(self, parent, i18n: LocalizationManager):
        super().__init__(parent, title=i18n.get("about_title"), size=(420, 380))
        self.i18n = i18n
        i18n.apply_direction(self)
        widgets.fit_to_screen(self)
        self.setup_ui()
        self.CenterOnParent()

    def setup_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # أيقونة البرنامج بحجم كبير فوق اسمه (زخرفة فقط، لا تؤثر على قارئ الشاشة)
        bundle = icons.app_icons()
        if bundle is not None:
            icon = bundle.GetIcon(self.FromDIP(wx.Size(64, 64)))
            if icon.IsOk():
                bmp = wx.Bitmap(); bmp.CopyFromIcon(icon)
                sizer.Add(wx.StaticBitmap(panel, bitmap=bmp), 0, wx.TOP | wx.ALIGN_CENTER_HORIZONTAL, 15)
        title = wx.StaticText(panel, label=self.i18n.get("app_name"))
        font = title.GetFont()
        font.SetPointSize(16)
        font.MakeBold()
        title.SetFont(font)
        
        version = wx.StaticText(panel, label=self.i18n.get("app_version"))
        desc = wx.StaticText(panel, label=self.i18n.get("about_description"))
        desc.Wrap(350)
        
        dev = wx.StaticText(panel, label=self.i18n.get("about_developer"))
        
        sizer.Add(title, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)
        sizer.Add(version, 0, wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL, 10)
        sizer.Add(desc, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 15)
        sizer.AddStretchSpacer(1)
        sizer.Add(dev, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)
        
        btn_close = icons.button(wx.Button(panel, id=wx.ID_OK, label=self.i18n.get("btn_close")), "close", theme="light")
        sizer.Add(btn_close, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 10)
        
        panel.SetSizer(sizer)