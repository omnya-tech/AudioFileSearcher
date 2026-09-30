import wx
from core.i18n import LocalizationManager
from core.settings import SettingsManager

class CustomDictDialog(wx.Dialog):
    def __init__(self, parent, i18n: LocalizationManager, settings: SettingsManager):
        super().__init__(parent, title=i18n.get("dialog_custom_dict_title"), size=(550, 450))
        self.i18n = i18n
        i18n.apply_direction(self)
        self.settings = settings
        # نعمل على نسخة، فلا تتغير الإعدادات إلا عند الضغط على موافق
        self.custom_dict = dict(self.settings.get("custom_dictionary", {}) or {})
        self.setup_ui()
        self.populate_list()
        self.apply_theme(self.settings.get("theme", "light"))
        self.CenterOnParent()

    def setup_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        input_sizer = wx.FlexGridSizer(2, 2, 10, 10)
        input_sizer.AddGrowableCol(1, 1)
        
        lbl_wrong = wx.StaticText(panel, label=self.i18n.get("lbl_wrong_word"))
        self.txt_wrong = wx.TextCtrl(panel)
        
        lbl_correct = wx.StaticText(panel, label=self.i18n.get("lbl_correct_word"))
        self.txt_correct = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        
        input_sizer.Add(lbl_wrong, 0, wx.ALIGN_CENTER_VERTICAL)
        input_sizer.Add(self.txt_wrong, 1, wx.EXPAND)
        input_sizer.Add(lbl_correct, 0, wx.ALIGN_CENTER_VERTICAL)
        input_sizer.Add(self.txt_correct, 1, wx.EXPAND)
        
        main_sizer.Add(input_sizer, 0, wx.EXPAND | wx.ALL, 15)
        
        self.btn_add = wx.Button(panel, label=self.i18n.get("btn_add_word"))
        main_sizer.Add(self.btn_add, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.LEFT, 15)
        
        self.dict_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES)
        self.dict_list.InsertColumn(0, self.i18n.get("lbl_wrong_word"), width=200)
        self.dict_list.InsertColumn(1, self.i18n.get("lbl_correct_word"), width=300)
        main_sizer.Add(self.dict_list, 1, wx.EXPAND | wx.ALL, 15)
        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_remove = wx.Button(panel, label=self.i18n.get("btn_remove_word"))
        self.btn_clear = wx.Button(panel, label=self.i18n.get("btn_clear_dict"))
        self.btn_ok = wx.Button(panel, label=self.i18n.get("btn_ok"))
        
        btn_sizer.Add(self.btn_remove, 0, wx.RIGHT, 10)
        btn_sizer.Add(self.btn_clear, 0, wx.RIGHT, 10)
        btn_sizer.AddStretchSpacer(1)
        btn_sizer.Add(self.btn_ok, 0)
        
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 15)
        panel.SetSizer(main_sizer)
        
        self.btn_add.Bind(wx.EVT_BUTTON, self.on_add)
        self.txt_correct.Bind(wx.EVT_TEXT_ENTER, self.on_add)
        self.btn_remove.Bind(wx.EVT_BUTTON, self.on_remove)
        self.btn_clear.Bind(wx.EVT_BUTTON, self.on_clear)
        self.btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)

    def populate_list(self):
        self.dict_list.DeleteAllItems()
        for wrong, correct in self.custom_dict.items():
            idx = self.dict_list.InsertItem(self.dict_list.GetItemCount(), wrong)
            self.dict_list.SetItem(idx, 1, correct)

    def on_add(self, event):
        wrong = self.txt_wrong.GetValue().strip()
        correct = self.txt_correct.GetValue().strip()
        if wrong and correct and wrong != correct:
            self.custom_dict[wrong] = correct
            self.populate_list()
            self.txt_wrong.SetValue("")
            self.txt_correct.SetValue("")
            self.txt_wrong.SetFocus()

    def on_remove(self, event):
        sel = self.dict_list.GetFirstSelected()
        if sel != -1:
            wrong = self.dict_list.GetItemText(sel)
            if wrong in self.custom_dict: del self.custom_dict[wrong]
            self.populate_list()
            
    def on_clear(self, event):
        self.custom_dict.clear()
        self.populate_list()

    def on_ok(self, event):
        self.settings.set("custom_dictionary", self.custom_dict)
        self.EndModal(wx.ID_OK)
        
    def apply_theme(self, theme):
        if theme == "dark":
            bg_color, panel_bg, fg_color, input_bg = wx.Colour(15,19,28), wx.Colour(22,29,43), wx.Colour(241,241,241), wx.Colour(10,13,18)
        else:
            bg_color, panel_bg, fg_color, input_bg = wx.Colour(248,249,250), wx.Colour(255,255,255), wx.Colour(33,37,41), wx.Colour(255,255,255)

        self.SetBackgroundColour(bg_color)
        self.SetForegroundColour(fg_color)
        for child in self.GetChildren(): self.apply_theme_to_widget(child, panel_bg, fg_color, input_bg)
        self.Refresh()

    def apply_theme_to_widget(self, widget, bg_color, fg_color, input_bg):
        try:
            if isinstance(widget, (wx.TextCtrl, wx.ListCtrl)): widget.SetBackgroundColour(input_bg)
            else: widget.SetBackgroundColour(bg_color)
            widget.SetForegroundColour(fg_color)
            for child in widget.GetChildren(): self.apply_theme_to_widget(child, bg_color, fg_color, input_bg)
        except: pass