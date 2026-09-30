import wx
from core.i18n import LocalizationManager

class ProcessingDialog(wx.Dialog):
    def __init__(self, parent, i18n: LocalizationManager):
        # تم إعداد النافذة بحجم مناسب لاحتواء الجدول وشريط التقدم
        super().__init__(parent, title=i18n.get("dialog_processing_title"), size=(550, 320), 
                         style=wx.DEFAULT_DIALOG_STYLE)
        self.i18n = i18n
        i18n.apply_direction(self)
        self.parent_win = parent
        self.is_canceling = False
        
        self.setup_ui()
        if hasattr(parent, 'settings'):
            self.apply_theme(parent.settings.get("theme", "light"))
            
        self.CenterOnParent()
        
        # توجيه التركيز (Focus) فوراً إلى الجدول ليقرأه قارئ الشاشة (NVDA)
        wx.CallAfter(self.list_ctrl.SetFocus)
        wx.CallAfter(self.list_ctrl.Select, 0)

    def setup_ui(self):
        self.panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # 1. رسالة الانتظار (صديقة لقارئ الشاشة)
        self.lbl_title = wx.TextCtrl(self.panel, value=self.i18n.get("dialog_processing_msg"), 
                                     style=wx.TE_READONLY | wx.BORDER_NONE | wx.TE_CENTER)
        title_font = self.lbl_title.GetFont()
        title_font.SetPointSize(11)
        title_font.MakeBold()
        self.lbl_title.SetFont(title_font)
        main_sizer.Add(self.lbl_title, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)
        
        # 2. الجدول التفاعلي (ListCtrl)
        self.list_ctrl = wx.ListCtrl(self.panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES | wx.LC_VRULES)
        self.list_ctrl.InsertColumn(0, self.i18n.get("proc_col_item"), width=150)
        self.list_ctrl.InsertColumn(1, self.i18n.get("proc_col_status"), width=350)
        
        # إدراج الصفوف الافتراضية
        self.list_ctrl.InsertItem(0, self.i18n.get("proc_item_file"))
        self.list_ctrl.SetItem(0, 1, self.i18n.get("proc_val_waiting"))
        
        self.list_ctrl.InsertItem(1, self.i18n.get("proc_item_percent"))
        self.list_ctrl.SetItem(1, 1, "0%")
        
        self.list_ctrl.InsertItem(2, self.i18n.get("proc_item_step"))
        self.list_ctrl.SetItem(2, 1, self.i18n.get("status_init_engine"))
        
        self.list_ctrl.SetMinSize((-1, 110))
        main_sizer.Add(self.list_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)
        
        # 3. شريط التقدم المرئي (Gauge)
        self.gauge = wx.Gauge(self.panel, range=100, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.gauge.SetMinSize((-1, 20))
        main_sizer.Add(self.gauge, 0, wx.EXPAND | wx.ALL, 15)
        
        main_sizer.AddStretchSpacer(1)
        
        # 4. خط فاصل وزر الإلغاء
        line = wx.StaticLine(self.panel)
        main_sizer.Add(line, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        
        self.btn_cancel = wx.Button(self.panel, id=wx.ID_CANCEL, label=self.i18n.get("btn_cancel"))
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        # إغلاق النافذة (زر X أو Esc) يعني إلغاء العملية، بدلاً من إخفائها والعملية مستمرة
        self.Bind(wx.EVT_CLOSE, self.on_cancel)
        main_sizer.Add(self.btn_cancel, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 15)
        
        self.panel.SetSizer(main_sizer)

    def update_progress(self, percent, total, status, filename):
        if self.is_canceling:
            return
            
        # تحديث شريط التقدم
        self.gauge.SetValue(percent)
        
        # تقصير اسم الملف إذا كان طويلاً جداً ليتناسب مع عرض الجدول
        display_name = filename if len(filename) <= 45 else filename[:20] + "..." + filename[-20:]
        
        # تحديث بيانات الجدول التفاعلي
        self.list_ctrl.SetItem(0, 1, display_name)
        self.list_ctrl.SetItem(1, 1, f"{percent}%")
        self.list_ctrl.SetItem(2, 1, status)
        
        # تحديث عنوان النافذة ليقرأه NVDA تلقائياً دون تدخل من المستخدم
        clean_status = status.replace("...", "")
        window_title_announcement = f"{percent}% - {clean_status} - {self.i18n.get('dialog_processing_title')}"
        self.SetTitle(window_title_announcement)
        
        self.panel.Layout()

    def on_cancel(self, event):
        if self.is_canceling:
            return
        self.is_canceling = True
        self.btn_cancel.Disable()
        
        # إعلام المستخدم بالإلغاء في الجدول وعنوان النافذة
        cancel_msg = self.i18n.get("proc_step_cancel")
        self.list_ctrl.SetItem(2, 1, cancel_msg)
        self.list_ctrl.SetItemBackgroundColour(2, wx.Colour(255, 230, 230)) # تمييز صف الإلغاء بلون مختلف
        
        self.SetTitle(cancel_msg)
        self.gauge.Pulse() 
        self.panel.Layout()
        
        if hasattr(self.parent_win, 'cancel_processing'):
            wx.CallAfter(self.parent_win.cancel_processing)

    def apply_theme(self, theme):
        if theme == "dark":
            bg_color = wx.Colour(22, 29, 43)
            fg_color = wx.Colour(241, 241, 241)
            list_bg = wx.Colour(30, 38, 56)
        else:
            bg_color = wx.Colour(248, 249, 250)
            fg_color = wx.Colour(33, 37, 41)
            list_bg = wx.Colour(255, 255, 255)

        self.SetBackgroundColour(bg_color)
        self.SetForegroundColour(fg_color)
        self.panel.SetBackgroundColour(bg_color)
        self.panel.SetForegroundColour(fg_color)
        
        # تلوين حقل النص ليتماشى مع الخلفية
        self.lbl_title.SetBackgroundColour(bg_color)
        self.lbl_title.SetForegroundColour(fg_color)
        
        # تلوين الجدول (ListCtrl)
        self.list_ctrl.SetBackgroundColour(list_bg)
        self.list_ctrl.SetForegroundColour(fg_color)
            
        self.Refresh()