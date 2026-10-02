"""
سجل العمليات: كل تفريغ سابق بتفاصيله، مع الإحصائيات والبحث والترتيب، وفتح تقريره أو ملف التفريغ أو مجلده، وحذفه.
"""
import os

import wx
from gui import icons, widgets
from core.i18n import LocalizationManager
from core.transcription_logger import TranscriptionLogger, format_hours

# الترتيب: (المفتاح في ملفات اللغة، دالة الترتيب، تنازلي؟)
SORTS = [
    ("history_sort_newest", lambda e: e.get("timestamp", ""), True),
    ("history_sort_oldest", lambda e: e.get("timestamp", ""), False),
    ("history_sort_name", lambda e: e.get("file_name", "").lower(), False),
    ("history_sort_longest", lambda e: e.get("audio_info", {}).get("duration_seconds", 0) or 0, True),
    ("history_sort_least_accurate", lambda e: e.get("score", 101) if e.get("score") is not None else 101, False),
]
# ملفات التفريغ التي يفتحها البرنامج نفسه في قائمة النتائج
LOADABLE_FORMATS = (".srt", ".vtt")


def short_model_name(model):
    """«deepdml/faster-whisper-large-v3-turbo-ct2» ← «large-v3-turbo-ct2»"""
    name = (model or "").split("/")[-1]
    return name[len("faster-whisper-"):] if name.startswith("faster-whisper-") else name


class HistoryDialog(wx.Dialog):
    def __init__(self, parent, i18n: LocalizationManager):
        super().__init__(parent, title=i18n.get("history_title"), size=(980, 560), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.i18n = i18n
        i18n.apply_direction(self)
        widgets.fit_to_screen(self)
        self.parent_win = parent
        self.logger = TranscriptionLogger(i18n)
        self.history = []
        self.rows = []
        self.setup_ui()
        self.load_history()
        self.CenterOnParent()
        wx.CallAfter(self._focus_list)

    def _focus_list(self):
        self.list_ctrl.SetFocus()
        if self.rows:
            self.list_ctrl.Focus(0)
            self.list_ctrl.Select(0)

    def setup_ui(self):
        g = self.i18n.get
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # الإحصائيات في خانة يصل إليها قارئ الشاشة بـ Tab
        sizer.Add(wx.StaticText(panel, label=g("history_stats_label")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.txt_stats = wx.TextCtrl(panel, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_NO_VSCROLL)
        self.txt_stats.SetMinSize((-1, self.txt_stats.FromDIP(40)))
        sizer.Add(self.txt_stats, 0, wx.EXPAND | wx.ALL, 10)

        filters = wx.FlexGridSizer(cols=4, vgap=5, hgap=8)
        filters.AddGrowableCol(1, 1)
        filters.Add(wx.StaticText(panel, label=g("history_search")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_search = wx.TextCtrl(panel)
        filters.Add(self.txt_search, 1, wx.EXPAND)
        filters.Add(wx.StaticText(panel, label=g("history_sort")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.cb_sort = wx.Choice(panel, choices=[g(key) for key, _, _ in SORTS])
        self.cb_sort.SetSelection(0)
        filters.Add(self.cb_sort, 0)
        sizer.Add(filters, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        sizer.Add(wx.StaticText(panel, label=g("lbl_history_list")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        columns = [("history_col_date", 120), ("history_col_file", 200), ("history_col_audio_duration", 90),
                   ("history_col_duration", 90), ("history_col_words", 80), ("history_col_accuracy", 70),
                   ("history_col_model", 150), ("history_col_device", 110), ("history_col_status", 110)]
        for i, (key, width) in enumerate(columns):
            self.list_ctrl.InsertColumn(i, g(key), width=self.FromDIP(width))
        # عمود اسم الملف يأخذ العرض المتبقي
        widgets.auto_fit_first_column(self.list_ctrl, column=1, min_width=120)
        sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_report = icons.button(wx.Button(panel, label=g("btn_view_report")), "report", theme="light")
        self.btn_open = icons.button(wx.Button(panel, label=g("btn_history_open_transcript")), "subtitle", theme="light")
        self.btn_folder = icons.button(wx.Button(panel, label=g("btn_history_open_folder")), "folder", theme="light")
        self.btn_delete = icons.button(wx.Button(panel, label=g("btn_history_delete")), "delete", theme="light")
        self.btn_clear = icons.button(wx.Button(panel, label=g("btn_clear_history")), "clear", theme="light")
        btn_close = icons.button(wx.Button(panel, id=wx.ID_OK, label=g("btn_close")), "close", theme="light")
        for b in (self.btn_report, self.btn_open, self.btn_folder, self.btn_delete, self.btn_clear):
            btn_sizer.Add(b, 0, wx.ALL, 5)
        btn_sizer.AddStretchSpacer(1)
        btn_sizer.Add(btn_close, 0, wx.ALL, 5)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(sizer)
        self.txt_search.Bind(wx.EVT_TEXT, lambda e: self.refresh_list())
        self.cb_sort.Bind(wx.EVT_CHOICE, lambda e: self.refresh_list())
        self.btn_report.Bind(wx.EVT_BUTTON, self.on_view_report)
        self.btn_open.Bind(wx.EVT_BUTTON, self.on_open_transcript)
        self.btn_folder.Bind(wx.EVT_BUTTON, self.on_open_folder)
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_delete)
        self.btn_clear.Bind(wx.EVT_BUTTON, self.on_clear)
        # Enter على أي تفريغ يفتح تقريره، وDelete يحذفه
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_view_report)
        self.list_ctrl.Bind(wx.EVT_KEY_DOWN, self._on_list_key)
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda e: self._update_buttons())

    # ---------- العرض ----------

    def load_history(self):
        self.history = self.logger.get_history(limit=len(self.logger.history) or 1)
        self._update_stats()
        self.refresh_list()

    def _update_stats(self):
        g = self.i18n.get
        if not self.history:
            self.txt_stats.SetValue(g("history_no_records"))
            return
        audio = sum(e.get("audio_info", {}).get("duration_seconds", 0) or 0 for e in self.history)
        processing = sum(e.get("processing_time", {}).get("total_seconds", 0) or 0 for e in self.history)
        words = sum(e.get("statistics", {}).get("total_words", 0) or 0 for e in self.history)
        self.txt_stats.SetValue(g("history_stats", count=self.i18n.plural("n_files", len(self.history)),
                                  audio=format_hours(audio), processing=format_hours(processing), words=f"{words:,}"))

    def refresh_list(self):
        query = self.txt_search.GetValue().strip().lower()
        _, key, reverse = SORTS[max(0, self.cb_sort.GetSelection())]
        rows = [e for e in self.history if not query or query in e.get("file_name", "").lower()]
        self.rows = sorted(rows, key=key, reverse=reverse)

        self.list_ctrl.DeleteAllItems()
        if not self.rows:
            self.list_ctrl.InsertItem(0, self.i18n.get("history_no_matches" if self.history else "history_no_records"))
        for idx, entry in enumerate(self.rows):
            device = entry.get("device")
            score = entry.get("score")
            cells = [
                entry.get("timestamp", "").replace("T", " ")[:16],
                entry.get("file_name", ""),
                entry.get("audio_info", {}).get("duration_formatted", ""),
                entry.get("processing_time", {}).get("formatted", ""),
                str(entry.get("statistics", {}).get("total_words", "")),
                f"{score}%" if score is not None else "",
                short_model_name(entry.get("model_used")),
                self.i18n.get(f"device_used_{device}") if device in ("cpu", "cuda") else "",
                entry.get("status", ""),
            ]
            self.list_ctrl.InsertItem(idx, cells[0])
            for col, value in enumerate(cells[1:], start=1):
                self.list_ctrl.SetItem(idx, col, value)
        if self.rows:
            self.list_ctrl.Select(0)
            self.list_ctrl.Focus(0)
        self._update_buttons()

    def _selected(self):
        index = self.list_ctrl.GetFirstSelected()
        return self.rows[index] if 0 <= index < len(self.rows) else None

    def _update_buttons(self):
        has = self._selected() is not None
        for b in (self.btn_report, self.btn_open, self.btn_folder, self.btn_delete):
            b.Enable(has)
        self.btn_clear.Enable(bool(self.history))

    def _on_list_key(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE:
            self.on_delete(None)
        else:
            event.Skip()

    # ---------- الأوامر ----------

    def on_view_report(self, event):
        entry = self._selected()
        if not entry:
            return
        from gui.report_dialog import ReportDialog
        dlg = ReportDialog(self, self.i18n, self.logger.load_report(entry))
        dlg.ShowModal()
        dlg.Destroy()
        self.list_ctrl.SetFocus()

    def transcript_path(self, entry):
        """ملف التفريغ المحفوظ: المسجّل في السجل، أو ملف ترجمة بجانب الصوت بنفس الاسم (للتفريغات القديمة)"""
        saved = entry.get("output_file")
        if saved and os.path.isfile(saved):
            return saved
        audio = entry.get("file_path", "")
        base = os.path.splitext(audio)[0]
        output_dir = getattr(getattr(self.parent_win, "settings", None), "get", lambda *a: "")("output_directory", "")
        candidates = [base]
        if output_dir:
            candidates.append(os.path.join(output_dir, os.path.basename(base)))
        for candidate in candidates:
            for ext in LOADABLE_FORMATS:
                if os.path.isfile(candidate + ext):
                    return candidate + ext
        return None

    def on_open_transcript(self, event):
        entry = self._selected()
        if not entry:
            return
        # أثناء التفريغ تمتلئ قائمة النتائج بالملف الجاري، ففتح ملف آخر فيها يخلطهما
        if getattr(self.parent_win, "transcription_thread_running", lambda: False)():
            wx.MessageBox(self.i18n.get("msg_history_busy"), self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION, self)
            return
        path = self.transcript_path(entry)
        if not path:
            wx.MessageBox(self.i18n.get("msg_history_transcript_missing", file=entry.get("file_name", "")),
                          self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION, self)
            return
        if path.lower().endswith(LOADABLE_FORMATS) and hasattr(self.parent_win, "load_srt_file"):
            # في قائمة النتائج مع صوته، للمراجعة والتصحيح والتصدير
            self.EndModal(wx.ID_OK)
            wx.CallAfter(self.parent_win.load_srt_file, path)
        else:
            # صيغ لا يقرؤها البرنامج (Word، نص، JSON): تُفتح بالبرنامج المرتبط بها في ويندوز
            os.startfile(path)

    def on_open_folder(self, event):
        entry = self._selected()
        if not entry:
            return
        target = self.transcript_path(entry) or entry.get("file_path", "")
        if not (target and (os.path.exists(target) or os.path.isdir(os.path.dirname(target)))):
            wx.MessageBox(self.i18n.get("msg_history_folder_missing"), self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION, self)
            return
        if hasattr(self.parent_win, "open_in_file_manager"):
            self.parent_win.open_in_file_manager(target if os.path.exists(target) else os.path.dirname(target))

    def on_delete(self, event):
        entry = self._selected()
        if not entry:
            return
        index = self.list_ctrl.GetFirstSelected()
        dlg = wx.MessageDialog(self, self.i18n.get("msg_history_delete_confirm", file=entry.get("file_name", "")),
                               self.i18n.get("dialog_warning_title"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
        answer = dlg.ShowModal()
        dlg.Destroy()
        if answer != wx.ID_YES:
            return
        self.logger.delete_entry(entry)
        self.history = [e for e in self.history if e is not entry]
        self._update_stats()
        self.refresh_list()
        # التركيز على التفريغ التالي في مكان المحذوف
        if self.rows:
            index = min(index, len(self.rows) - 1)
            self.list_ctrl.Select(index)
            self.list_ctrl.Focus(index)
        self.list_ctrl.SetFocus()

    def on_clear(self, event):
        dlg = wx.MessageDialog(self, self.i18n.get("msg_clear_history_confirm"), self.i18n.get("dialog_warning_title"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
        if dlg.ShowModal() == wx.ID_YES:
            self.logger.clear_history()
            self.load_history()
            wx.MessageBox(self.i18n.get("msg_history_cleared"), self.i18n.get("dialog_success_title"), wx.ICON_INFORMATION)
        dlg.Destroy()
