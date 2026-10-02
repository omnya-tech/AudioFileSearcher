import wx
from gui import icons, widgets
from core.i18n import LocalizationManager
from core.transcription_logger import TranscriptionLogger

class HistoryDialog(wx.Dialog):
    def __init__(self, parent, i18n: LocalizationManager):
        super().__init__(parent, title=i18n.get("history_title"), size=(850, 500), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.i18n = i18n
        i18n.apply_direction(self)
        widgets.fit_to_screen(self)
        self.logger = TranscriptionLogger(i18n)
        self.setup_ui()
        self.load_history()
        self.CenterOnParent()
        wx.CallAfter(self._focus_list)

    def _focus_list(self):
        self.list_ctrl.SetFocus()
        if self.list_ctrl.GetItemCount():
            self.list_ctrl.Focus(0)
            self.list_ctrl.Select(0)

    def setup_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(wx.StaticText(panel, label=self.i18n.get("lbl_history_list")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list_ctrl.InsertColumn(0, self.i18n.get("history_col_date"), width=self.FromDIP(130))
        self.list_ctrl.InsertColumn(1, self.i18n.get("history_col_file"), width=self.FromDIP(200))
        self.list_ctrl.InsertColumn(2, self.i18n.get("report_audio_duration").rstrip(":"), width=self.FromDIP(140))
        self.list_ctrl.InsertColumn(3, self.i18n.get("history_col_duration"), width=self.FromDIP(110))
        self.list_ctrl.InsertColumn(4, self.i18n.get("history_col_words"), width=self.FromDIP(90))
        self.list_ctrl.InsertColumn(5, self.i18n.get("history_col_status"), width=self.FromDIP(130))
        # عمود اسم الملف يأخذ العرض المتبقي
        widgets.auto_fit_first_column(self.list_ctrl, column=1, min_width=120)

        sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_report = icons.button(wx.Button(panel, label=self.i18n.get("btn_view_report")), "report", theme="light")
        self.btn_clear = icons.button(wx.Button(panel, label=self.i18n.get("btn_clear_history")), "clear", theme="light")
        btn_close = icons.button(wx.Button(panel, id=wx.ID_OK, label=self.i18n.get("btn_close")), "close", theme="light")
        btn_sizer.Add(self.btn_report, 0, wx.ALL, 5)
        btn_sizer.Add(self.btn_clear, 0, wx.ALL, 5)
        btn_sizer.AddStretchSpacer(1)
        btn_sizer.Add(btn_close, 0, wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(sizer)
        self.btn_clear.Bind(wx.EVT_BUTTON, self.on_clear)
        self.btn_report.Bind(wx.EVT_BUTTON, self.on_view_report)
        # Enter على أي تفريغ يفتح تقريره
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_view_report)

    def load_history(self):
        self.history = history = self.logger.get_history(limit=100)
        self.list_ctrl.DeleteAllItems()
        if not history:
            self.list_ctrl.InsertItem(0, self.i18n.get("history_no_records"))
            self.btn_clear.Disable()
            self.btn_report.Disable()
            return
        self.btn_clear.Enable()
        self.btn_report.Enable()
        for idx, entry in enumerate(history):
            timestamp = entry.get("timestamp", "")
            date_str = timestamp.replace("T", " ")[:16]
            self.list_ctrl.InsertItem(idx, date_str)
            self.list_ctrl.SetItem(idx, 1, entry.get("file_name", ""))
            self.list_ctrl.SetItem(idx, 2, entry.get("audio_info", {}).get("duration_formatted", ""))
            self.list_ctrl.SetItem(idx, 3, entry.get("processing_time", {}).get("formatted", ""))
            self.list_ctrl.SetItem(idx, 4, str(entry.get("statistics", {}).get("total_words", "")))
            self.list_ctrl.SetItem(idx, 5, entry.get("status", ""))

    def on_view_report(self, event):
        index = self.list_ctrl.GetFirstSelected()
        if not (0 <= index < len(getattr(self, "history", []))):
            return
        from gui.report_dialog import ReportDialog
        dlg = ReportDialog(self, self.i18n, self.logger.load_report(self.history[index]))
        dlg.ShowModal()
        dlg.Destroy()
        self.list_ctrl.SetFocus()

    def on_clear(self, event):
        dlg = wx.MessageDialog(self, self.i18n.get("msg_clear_history_confirm"), self.i18n.get("dialog_warning_title"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
        if dlg.ShowModal() == wx.ID_YES:
            self.logger.clear_history()
            self.load_history()
            wx.MessageBox(self.i18n.get("msg_history_cleared"), self.i18n.get("dialog_success_title"), wx.ICON_INFORMATION)
        dlg.Destroy()
