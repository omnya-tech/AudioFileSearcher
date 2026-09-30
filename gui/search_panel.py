import threading
import wx
from core.i18n import LocalizationManager
from core.cross_file_search import CrossFileSearcher, find_audio_for
from gui import icons, widgets

EVT_SEARCH_DONE_ID = wx.NewIdRef()

class SearchDoneEvent(wx.PyEvent):
    def __init__(self, results, token):
        super().__init__()
        self.SetEventType(EVT_SEARCH_DONE_ID)
        self.results = results
        self.token = token


class CrossFileSearchPanel(wx.Panel):
    def __init__(self, parent, i18n: LocalizationManager, play_callback=None):
        super().__init__(parent)
        self.i18n = i18n
        self.play_callback = play_callback
        self.searcher = CrossFileSearcher()
        self.search_dir = ""
        self.results = []
        # رقم آخر عملية بحث: أي نتيجة من بحث أقدم يتم تجاهلها
        self._search_token = 0
        self.setup_ui()
        self.Connect(-1, -1, EVT_SEARCH_DONE_ID, self.on_search_done)

    def setup_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # كل عنوان يُنشأ قبل حقله مباشرة ليقرأه قارئ الشاشة كاسم للحقل، وترتيب الإنشاء = ترتيب التنقل بـ Tab
        folder_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_folder = wx.Button(self, label=self.i18n.get("btn_select_search_folder"))
        self.lbl_folder = wx.StaticText(self, label=self.i18n.get("lbl_search_folder"))
        self.txt_folder = wx.TextCtrl(self, style=wx.TE_READONLY)
        self.txt_folder.SetValue(self.i18n.get("hint_no_folder_selected"))
        folder_sizer.Add(self.btn_folder, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        folder_sizer.Add(self.lbl_folder, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        folder_sizer.Add(self.txt_folder, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(folder_sizer, 0, wx.EXPAND | wx.ALL, 5)

        query_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_query = wx.StaticText(self, label=self.i18n.get("lbl_search_word"))
        self.txt_query = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        self.txt_query.SetHint(self.i18n.get("hint_search_global"))
        self.btn_search = wx.Button(self, label=self.i18n.get("btn_search"))
        query_sizer.Add(self.lbl_query, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        query_sizer.Add(self.txt_query, 1, wx.ALL | wx.EXPAND, 5)
        query_sizer.Add(self.btn_search, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        sizer.Add(query_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # عنوان القائمة يحمل عدد النتائج، فيُنطق تلقائياً عند الانتقال للقائمة
        self.lbl_list = wx.StaticText(self, label=self.i18n.get("lbl_search_results"))
        self.list_ctrl = self._create_list()
        sizer.Add(self.lbl_list, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        self.main_sizer = sizer

        self.lbl_status = wx.StaticText(self, label="")
        sizer.Add(self.lbl_status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.SetSizer(sizer)

        self.btn_folder.Bind(wx.EVT_BUTTON, self.on_select_folder)
        self.btn_search.Bind(wx.EVT_BUTTON, self.on_search)
        self.txt_query.Bind(wx.EVT_TEXT_ENTER, self.on_search)

    def _create_list(self):
        lst = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        lst.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        self.list_ctrl = lst
        self._insert_columns()
        widgets.auto_fit_first_column(lst)
        return lst

    def rebuild_list(self):
        """بعد تغيير اتجاه الواجهة: قائمة جديدة بالاتجاه الصحيح (رؤوس الأعمدة لا تنعكس في القائمة القديمة)"""
        old = self.list_ctrl
        new = self._create_list()
        self.main_sizer.Replace(old, new)
        old.Destroy()
        new.MoveAfterInTabOrder(self.lbl_list)
        self._show_results(self.results)

    def apply_icons(self):
        icons.button(self.btn_folder, "folder")
        icons.button(self.btn_search, "search")

    def _insert_columns(self):
        # النص أولاً لأن قارئ الشاشة ينطق العمود الأول قبل غيره
        self.list_ctrl.InsertColumn(0, self.i18n.get("col_text_snippet"), width=self.FromDIP(500))
        self.list_ctrl.InsertColumn(1, self.i18n.get("col_file_name"), width=self.FromDIP(200))
        self.list_ctrl.InsertColumn(2, self.i18n.get("col_time"), width=self.FromDIP(150))
        widgets.fit_first_column(self.list_ctrl)

    def refresh_ui_texts(self):
        self.btn_folder.SetLabel(self.i18n.get("btn_select_search_folder"))
        self.lbl_folder.SetLabel(self.i18n.get("lbl_search_folder"))
        self.lbl_query.SetLabel(self.i18n.get("lbl_search_word"))
        self.lbl_list.SetLabel(self.i18n.get("lbl_search_results"))
        self.txt_query.SetHint(self.i18n.get("hint_search_global"))
        self.btn_search.SetLabel(self.i18n.get("btn_search"))
        if not self.search_dir:
            self.txt_folder.SetValue(self.i18n.get("hint_no_folder_selected"))
        if self.list_ctrl.GetColumnCount() == 0 or self.list_ctrl.GetColumn(0).GetText() != self.i18n.get("col_text_snippet"):
            self.list_ctrl.ClearAll()
            self._insert_columns()
        self._show_results(self.results)
        self.lbl_status.SetLabel("")
        self.Layout()

    def on_select_folder(self, event):
        dlg = wx.DirDialog(self, self.i18n.get("dialog_select_search_folder"), style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.search_dir = dlg.GetPath()
            self.txt_folder.SetValue(self.search_dir)
            self.txt_query.SetFocus()
        dlg.Destroy()

    def on_search(self, event):
        query = self.txt_query.GetValue().strip()
        if not self.search_dir:
            wx.MessageBox(self.i18n.get("msg_select_folder_first"), self.i18n.get("dialog_warning_title"), wx.ICON_WARNING)
            return
        if not query: return

        self._search_token += 1
        token = self._search_token
        self.list_ctrl.DeleteAllItems()
        self.results = []
        self.lbl_status.SetLabel(self.i18n.get("status_searching"))

        folder = self.search_dir
        is_stale = lambda: token != self._search_token

        def worker():
            results = self.searcher.search_in_directory(folder, query, should_stop=is_stale)
            try:
                wx.PostEvent(self, SearchDoneEvent(results, token))
            except RuntimeError:
                pass  # النافذة أُغلقت أثناء البحث

        threading.Thread(target=worker, daemon=True).start()

    def on_search_done(self, event):
        if event.token != self._search_token:
            return
        self.results = event.results
        self._show_results(self.results)
        if self.results:
            found = self.i18n.get("status_found_results", count=self.i18n.plural("n_results", len(self.results)))
            self.lbl_status.SetLabel(found)
            # العدد في اسم القائمة: قارئ الشاشة ينطقه عند نقل التركيز إليها
            self.lbl_list.SetLabel(f"{self.i18n.get('lbl_search_results')} {found}")
            self.list_ctrl.SetFocus()
            self.list_ctrl.Focus(0)
            self.list_ctrl.Select(0)
        else:
            self.lbl_status.SetLabel(self.i18n.get("status_no_results"))
            self.lbl_list.SetLabel(self.i18n.get("lbl_search_results"))
            # رسالة منبثقة لأن النص الثابت لا يُنطق تلقائياً
            wx.MessageBox(self.i18n.get("status_no_results"), self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION)
            self.txt_query.SetFocus()
        self.Layout()

    def _show_results(self, results):
        self.list_ctrl.Freeze()
        try:
            self.list_ctrl.DeleteAllItems()
            for idx, res in enumerate(results):
                self.list_ctrl.InsertItem(idx, res.get("text", ""))
                self.list_ctrl.SetItem(idx, 1, res.get("file_name", ""))
                self.list_ctrl.SetItem(idx, 2, res.get("time_str", ""))
        finally:
            self.list_ctrl.Thaw()

    def on_item_activated(self, event):
        idx = event.GetIndex()
        if not (0 <= idx < len(self.results)) or not self.play_callback:
            return
        res = self.results[idx]
        audio = find_audio_for(res["file_path"])
        if not audio:
            wx.MessageBox(self.i18n.get("msg_audio_not_found"), self.i18n.get("dialog_warning_title"), wx.ICON_WARNING)
            return
        self.play_callback(audio, res.get("start") or 0)
