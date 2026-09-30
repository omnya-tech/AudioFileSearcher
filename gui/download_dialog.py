import wx
import os
import shutil
import threading
from huggingface_hub import HfApi
from huggingface_hub.constants import HF_HUB_CACHE
from core.i18n import LocalizationManager
from core.model_downloader import ModelDownloadThread, EVT_DOWNLOAD_RESULT, EVT_DOWNLOAD_PROGRESS
from core.model_manager import ModelManager  

EVT_HF_SEARCH_DONE_ID = wx.NewIdRef()
EVT_HF_DETAILS_DONE_ID = wx.NewIdRef()

def EVT_HF_SEARCH_DONE(win, func):
    win.Connect(-1, -1, EVT_HF_SEARCH_DONE_ID, func)

def EVT_HF_DETAILS_DONE(win, func):
    win.Connect(-1, -1, EVT_HF_DETAILS_DONE_ID, func)

class HFSearchResultEvent(wx.PyEvent):
    def __init__(self, data):
        super().__init__()
        self.SetEventType(EVT_HF_SEARCH_DONE_ID)
        self.data = data

class HFDetailsResultEvent(wx.PyEvent):
    def __init__(self, data):
        super().__init__()
        self.SetEventType(EVT_HF_DETAILS_DONE_ID)
        self.data = data

class HFSearchThread(threading.Thread):
    def __init__(self, parent, category_idx):
        super().__init__(daemon=True)
        self.parent = parent
        self.category_idx = category_idx
        self.start()

    def run(self):
        try:
            api = HfApi()
            results = []
            
            if self.category_idx == 0:
                official_ids = [
                    "deepdml/faster-whisper-large-v3-turbo-ct2", 
                    "Systran/faster-whisper-large-v3", 
                    "Systran/faster-whisper-medium", 
                    "Systran/faster-whisper-small", 
                    "Systran/faster-whisper-base",
                    "Systran/faster-whisper-tiny"
                ]
                for mid in official_ids:
                    results.append({"id": mid})
            else:
                models = api.list_models(search="faster-whisper", sort="downloads", direction=-1, limit=300)
                for model in models:
                    model_id = getattr(model, 'id', getattr(model, 'modelId', ''))
                    if not model_id: continue
                    model_id_lower = model_id.lower()
                    tags = [t.lower() for t in getattr(model, 'tags', [])]
                    
                    if "systran/" in model_id_lower or "deepdml/" in model_id_lower: continue
                        
                    is_arabic = ("ar" in tags or "arabic" in tags or "-ar" in model_id_lower or "arabic" in model_id_lower)
                    
                    if self.category_idx == 1 and not is_arabic: continue
                    if self.category_idx == 2 and is_arabic: continue 
                        
                    results.append({
                        "id": model_id, 
                        "downloads": getattr(model, 'downloads', 0), 
                        "likes": getattr(model, 'likes', 0)
                    })
                    if len(results) >= 20: break
                    
            wx.PostEvent(self.parent, HFSearchResultEvent(results))
        except Exception as e:
            wx.PostEvent(self.parent, HFSearchResultEvent({"error": str(e)}))

class HFModelDetailsThread(threading.Thread):
    def __init__(self, parent, model_id):
        super().__init__(daemon=True)
        self.parent = parent
        self.model_id = model_id
        self.start()

    def run(self):
        try:
            api = HfApi()
            repo_id = self.model_id if "/" in self.model_id else f"Systran/faster-whisper-{self.model_id}"
            info = api.model_info(repo_id, files_metadata=True)
            
            exact_size = sum(f.size for f in info.siblings if getattr(f, 'size', None) is not None)
            
            data = {
                "id": repo_id,
                "author": getattr(info, 'author', 'Unknown'),
                "last_modified": getattr(info, 'lastModified', 'Unknown'),
                "downloads": getattr(info, 'downloads', 0),
                "likes": getattr(info, 'likes', 0),
                "size_bytes": exact_size
            }
            wx.PostEvent(self.parent, HFDetailsResultEvent(data))
        except Exception as e:
            wx.PostEvent(self.parent, HFDetailsResultEvent({"error": str(e)}))


class DownloadDialog(wx.Frame):
    def __init__(self, parent, i18n: LocalizationManager):
        super().__init__(parent, title=i18n.get("dialog_download_model_title"), size=(680, 780), style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER ^ wx.MAXIMIZE_BOX)
        self.i18n = i18n
        i18n.apply_direction(self)
        self.parent_window = parent
        self.is_downloading = False
        self.download_thread = None
        self.current_expected_size = 0
        
        self.setup_ui()
        if hasattr(parent, 'settings'): self.apply_theme(parent.settings.get("theme", "light"))
        self.CenterOnParent()
        
        EVT_DOWNLOAD_RESULT(self, self.on_download_result)
        EVT_DOWNLOAD_PROGRESS(self, self.on_download_progress)
        EVT_HF_SEARCH_DONE(self, self.on_hf_search_done)
        EVT_HF_DETAILS_DONE(self, self.on_hf_details_done)
        
        self.on_category_select(None)
        self.refresh_installed_models()

    def format_size(self, size_bytes):
        unit_gb = self.i18n.get('unit_gb', 'GB')
        unit_mb = self.i18n.get('unit_mb', 'MB')
        unit_kb = self.i18n.get('unit_kb', 'KB')
        unit_b = self.i18n.get('unit_b', 'B')
        
        if size_bytes >= 1024 ** 3: return f"{size_bytes / (1024**3):.2f} {unit_gb}"
        elif size_bytes >= 1024 ** 2: return f"{size_bytes / (1024**2):.2f} {unit_mb}"
        elif size_bytes >= 1024: return f"{size_bytes / 1024:.2f} {unit_kb}"
        return f"{int(size_bytes)} {unit_b}"

    def setup_ui(self):
        self.panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.panel_selection = wx.Panel(self.panel)
        sel_sizer = wx.BoxSizer(wx.VERTICAL)

        store_lbl = wx.StaticText(self.panel_selection, label=self.i18n.get("dl_explore_title"))
        font_store = store_lbl.GetFont()
        font_store.MakeBold()
        store_lbl.SetFont(font_store)
        sel_sizer.Add(store_lbl, 0, wx.ALL, 5)

        cat_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl_cat = wx.StaticText(self.panel_selection, label=self.i18n.get("dl_cat_label"))
        self.cb_category = wx.Choice(self.panel_selection, choices=[self.i18n.get("dl_cat_standard"), self.i18n.get("dl_cat_community_ar"), self.i18n.get("dl_cat_community_multi")])
        self.cb_category.SetSelection(0)
        cat_sizer.Add(lbl_cat, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        cat_sizer.Add(self.cb_category, 1, wx.ALL | wx.EXPAND, 5)
        sel_sizer.Add(cat_sizer, 0, wx.EXPAND | wx.ALL, 5)

        model_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl_model = wx.StaticText(self.panel_selection, label=self.i18n.get("lbl_select_model_to_download"))
        self.cb_model = wx.Choice(self.panel_selection, choices=[])
        model_sizer.Add(lbl_model, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        model_sizer.Add(self.cb_model, 1, wx.ALL | wx.EXPAND, 5)
        sel_sizer.Add(model_sizer, 0, wx.EXPAND | wx.ALL, 5)

        dir_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl_dir = wx.StaticText(self.panel_selection, label=self.i18n.get("lbl_download_dir"))
        self.txt_dir = wx.TextCtrl(self.panel_selection, style=wx.TE_READONLY)
        self.btn_browse = wx.Button(self.panel_selection, label=self.i18n.get("btn_browse"))
        self.txt_dir.SetValue(ModelManager.get_models_dir())
        dir_sizer.Add(lbl_dir, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        dir_sizer.Add(self.txt_dir, 1, wx.ALL | wx.EXPAND, 5)
        dir_sizer.Add(self.btn_browse, 0, wx.ALL, 5)
        sel_sizer.Add(dir_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        self.panel_selection.SetSizer(sel_sizer)

        self.panel_info = wx.Panel(self.panel)
        info_sizer = wx.BoxSizer(wx.VERTICAL)
        self.info_list = wx.ListCtrl(self.panel_info, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES | wx.LC_VRULES)
        self.info_list.InsertColumn(0, self.i18n.get("dl_col_prop"), width=160)
        self.info_list.InsertColumn(1, self.i18n.get("dl_col_details"), width=470)
        self.info_list.SetMinSize((-1, 160))
        info_sizer.Add(self.info_list, 1, wx.EXPAND | wx.ALL, 5)
        self.panel_info.SetSizer(info_sizer)

        self.panel_progress = wx.Panel(self.panel)
        prog_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.progress_bar = wx.Gauge(self.panel_progress, range=100, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        prog_sizer.Add(self.progress_bar, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.progress_list = wx.ListCtrl(self.panel_progress, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES)
        self.progress_list.InsertColumn(0, self.i18n.get("dl_col_info"), width=180)
        self.progress_list.InsertColumn(1, self.i18n.get("dl_col_data"), width=450)
        self.progress_list.SetMinSize((-1, 180))
        
        self.progress_list.InsertItem(0, self.i18n.get("dl_item_process"))
        self.progress_list.SetItem(0, 1, self.i18n.get("dl_val_waiting"))
        
        self.progress_list.InsertItem(1, self.i18n.get("dl_item_total"))
        self.progress_list.SetItem(1, 1, "...")
        
        self.progress_list.InsertItem(2, self.i18n.get("dl_item_percent"))
        self.progress_list.SetItem(2, 1, "0%")
        
        self.progress_list.InsertItem(3, self.i18n.get("dl_item_speed"))
        self.progress_list.SetItem(3, 1, f"0 {self.i18n.get('unit_b_s', 'B/s')}")
        
        self.progress_list.InsertItem(4, self.i18n.get("dl_item_downloaded_only"))
        self.progress_list.SetItem(4, 1, f"0 {self.i18n.get('unit_b', 'B')}")
        
        self.progress_list.InsertItem(5, self.i18n.get("dl_item_remaining"))
        self.progress_list.SetItem(5, 1, "...")
        
        self.progress_list.InsertItem(6, self.i18n.get("dl_item_eta"))
        self.progress_list.SetItem(6, 1, self.i18n.get("dl_val_unknown"))
        
        prog_sizer.Add(self.progress_list, 0, wx.EXPAND | wx.ALL, 10)
        
        self.panel_progress.SetSizer(prog_sizer)
        self.panel_progress.Hide() 

        self.panel_manage = wx.Panel(self.panel)
        manage_sizer = wx.BoxSizer(wx.VERTICAL)
        
        line = wx.StaticLine(self.panel_manage)
        manage_sizer.Add(line, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

        manage_lbl = wx.StaticText(self.panel_manage, label=self.i18n.get("dl_manage_title"))
        manage_font = manage_lbl.GetFont()
        manage_font.MakeBold()
        manage_lbl.SetFont(manage_font)
        manage_sizer.Add(manage_lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)

        m_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.cb_installed = wx.Choice(self.panel_manage, choices=[])
        self.btn_delete = wx.Button(self.panel_manage, label=self.i18n.get("dl_btn_delete"))
        self.btn_clean_cache = wx.Button(self.panel_manage, label=self.i18n.get("dl_btn_clean_cache"))
        m_sizer.Add(self.cb_installed, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        m_sizer.Add(self.btn_delete, 0, wx.ALL, 5)
        manage_sizer.Add(m_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        
        c_sizer = wx.BoxSizer(wx.HORIZONTAL)
        c_sizer.Add(self.btn_clean_cache, 1, wx.ALL | wx.EXPAND, 5)
        manage_sizer.Add(c_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        self.panel_manage.SetSizer(manage_sizer)

        self.btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_start = wx.Button(self.panel, label=self.i18n.get("btn_start_download"))
        self.btn_hide = wx.Button(self.panel, label=self.i18n.get("dl_btn_hide"))
        self.btn_cancel = wx.Button(self.panel, label=self.i18n.get("btn_cancel"))
        
        self.btn_start.Disable()
        self.btn_hide.Hide()
        
        self.btn_sizer.Add(self.btn_start, 0, wx.ALL, 10)
        self.btn_sizer.Add(self.btn_hide, 0, wx.ALL, 10)
        self.btn_sizer.AddStretchSpacer(1)
        self.btn_sizer.Add(self.btn_cancel, 0, wx.ALL, 10)

        self.main_sizer.Add(self.panel_selection, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.panel_info, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.panel_progress, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.panel_manage, 0, wx.EXPAND | wx.ALL, 5)
        self.main_sizer.Add(self.btn_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.panel.SetSizer(self.main_sizer)

        self.cb_category.Bind(wx.EVT_CHOICE, self.on_category_select)
        self.cb_model.Bind(wx.EVT_CHOICE, self.on_model_select)
        self.btn_browse.Bind(wx.EVT_BUTTON, self.on_browse)
        self.btn_start.Bind(wx.EVT_BUTTON, self.on_start)
        self.btn_hide.Bind(wx.EVT_BUTTON, self.on_hide)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.btn_delete.Bind(wx.EVT_BUTTON, self.on_delete_model)
        self.btn_clean_cache.Bind(wx.EVT_BUTTON, self.on_clean_cache)
        self.cb_installed.Bind(wx.EVT_CHOICE, self.on_installed_model_select)
        self.Bind(wx.EVT_CLOSE, self.on_close_window)

    def _add_info_item(self, prop, value):
        idx = self.info_list.GetItemCount()
        self.info_list.InsertItem(idx, prop)
        self.info_list.SetItem(idx, 1, str(value))

    def on_category_select(self, event):
        selection = self.cb_category.GetSelection()
        self.cb_model.Clear()
        self.info_list.DeleteAllItems()
        self.cb_model.AppendItems([self.i18n.get("dl_msg_fetching")])
        self.cb_model.SetSelection(0)
        self.cb_model.Disable()
        self.btn_start.Disable()
        
        HFSearchThread(self, selection)

    def on_hf_search_done(self, event):
        self.cb_model.Clear()
        self.cb_model.Enable()
        data = event.data
        if isinstance(data, dict) and "error" in data:
            self.cb_model.AppendItems([self.i18n.get("dl_msg_fetch_failed")])
            self.cb_model.SetSelection(0)
            self._add_info_item(self.i18n.get("dl_prop_error"), str(data['error']))
            return
        if not data:
            self.cb_model.AppendItems([self.i18n.get("dl_msg_no_results")])
            self.cb_model.SetSelection(0)
            return
            
        model_names = [m["id"] for m in data]
        self.cb_model.AppendItems(model_names)
        self.cb_model.SetSelection(0)
        self.on_model_select(None)

    def on_model_select(self, event):
        model_name = self.cb_model.GetStringSelection()
        self.info_list.DeleteAllItems()
        if not model_name or self.i18n.get("dl_msg_fetching") in model_name or self.i18n.get("dl_msg_fetch_failed") in model_name or self.i18n.get("dl_msg_no_results") in model_name: 
            self.btn_start.Disable()
            return
            
        self.btn_start.Disable()
        self._add_info_item(self.i18n.get("dl_col_info"), self.i18n.get("dl_msg_fetching"))
        
        HFModelDetailsThread(self, model_name)

    def on_hf_details_done(self, event):
        self.info_list.DeleteAllItems()
        data = event.data
        if "error" in data:
            self._add_info_item(self.i18n.get("dl_prop_error"), str(data['error']))
            return
            
        self.btn_start.Enable()
        self.current_expected_size = data.get("size_bytes", 0)
        
        self._add_info_item(self.i18n.get("dl_prop_model_name"), data.get("id"))
        category_name = self.i18n.get("dl_cat_standard") if self.cb_category.GetSelection() == 0 else self.i18n.get("dl_val_community")
        self._add_info_item(self.i18n.get("dl_prop_category"), category_name)
        self._add_info_item(self.i18n.get("dl_prop_author", default="الناشر:"), str(data.get("author")))
        self._add_info_item(self.i18n.get("dl_prop_size"), self.format_size(self.current_expected_size))
        self._add_info_item(self.i18n.get("dl_prop_downloads"), f"{data.get('downloads'):,}")
        self._add_info_item(self.i18n.get("dl_prop_likes"), f"{data.get('likes'):,}")
        self._add_info_item(self.i18n.get("dl_prop_updated", default="آخر تحديث:"), str(data.get("last_modified")).split('T')[0])
        self._add_info_item(self.i18n.get("dl_prop_url", default="الرابط:"), f"https://huggingface.co/{data.get('id')}")

    def refresh_installed_models(self):
        installed = ModelManager.get_installed_models()
        self.cb_installed.Clear()
        if installed:
            self.cb_installed.AppendItems(installed)
            self.cb_installed.SetSelection(0)
            self.btn_delete.Enable(True)
        else:
            self.cb_installed.Append(self.i18n.get("dl_msg_no_installed"))
            self.cb_installed.SetSelection(0)
            self.btn_delete.Enable(False)

    def on_installed_model_select(self, event):
        model_name = self.cb_installed.GetStringSelection()
        if model_name and model_name != self.i18n.get("dl_msg_no_installed"):
            self.info_list.DeleteAllItems()
            
            # جلب البيانات الحقيقية من المجلد بدلاً من القاموس الوهمي
            info = ModelManager.extract_model_info(model_name, self.i18n)
            
            self._add_info_item(self.i18n.get("dl_prop_model_name"), info.get('name', model_name))
            self._add_info_item(self.i18n.get("dl_prop_category"), info.get('status', self.i18n.get("dl_val_installed")))
            self._add_info_item(self.i18n.get("dl_prop_size"), info.get('size_str', self.i18n.get("dl_val_unknown_size")))

    def on_delete_model(self, event):
        model_name = self.cb_installed.GetStringSelection()
        if not model_name or model_name == self.i18n.get("dl_msg_no_installed"): return
        dlg = wx.MessageDialog(self, self.i18n.get("dl_msg_confirm_delete", model=model_name), self.i18n.get("dl_title_confirm_delete"), wx.YES_NO | wx.ICON_WARNING)
        if dlg.ShowModal() == wx.ID_YES:
            try:
                path = ModelManager.get_installed_model_path(model_name)
                if os.path.isdir(path): shutil.rmtree(path)
                wx.MessageBox(self.i18n.get("dl_msg_delete_success"), self.i18n.get("dialog_success_title"), wx.ICON_INFORMATION)
                self.refresh_installed_models()
                self.info_list.DeleteAllItems()
            except Exception as e:
                wx.MessageBox(self.i18n.get("dl_msg_delete_error", error=str(e)), self.i18n.get("dialog_error_title"), wx.ICON_ERROR)
        dlg.Destroy()

    def on_clean_cache(self, event):
        # مجلد النماذج المؤقتة فقط، وليس مجلد huggingface كله (فيه بيانات تسجيل الدخول)
        cache_dir = HF_HUB_CACHE
        if not os.path.exists(cache_dir):
            wx.MessageBox(self.i18n.get("dl_msg_cache_empty"), self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION)
            return
        total_size = 0
        for dirpath, _, filenames in os.walk(cache_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp) and os.path.exists(fp): total_size += os.path.getsize(fp)
        if total_size == 0:
            wx.MessageBox(self.i18n.get("dl_msg_cache_empty"), self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION)
            return
        mb_size = total_size / (1024 * 1024)
        dlg = wx.MessageDialog(self, self.i18n.get("dl_msg_confirm_clean", size=f"{mb_size:.2f}"), self.i18n.get("dl_title_confirm_clean"), wx.YES_NO | wx.ICON_WARNING)
        if dlg.ShowModal() == wx.ID_YES:
            try:
                shutil.rmtree(cache_dir)
                wx.MessageBox(self.i18n.get("dl_msg_clean_success"), self.i18n.get("dialog_success_title"), wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(self.i18n.get("dl_msg_clean_error", error=str(e)), self.i18n.get("dialog_error_title"), wx.ICON_ERROR)
        dlg.Destroy()

    def cleanup_and_destroy(self):
        if self.parent_window and hasattr(self.parent_window, 'download_dialog'): self.parent_window.download_dialog = None
        self.Destroy()

    def on_browse(self, event):
        dlg = wx.DirDialog(self, message=self.i18n.get("dialog_select_model_dir"), style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK: self.txt_dir.SetValue(dlg.GetPath())
        dlg.Destroy()

    def on_start(self, event):
        base_dir = self.txt_dir.GetValue()
        model_id = self.cb_model.GetStringSelection()
        if not model_id or self.i18n.get("dl_msg_searching") in model_id or self.i18n.get("dl_msg_fetch_failed") in model_id or self.i18n.get("dl_msg_no_results") in model_id: return
        
        repo_id = ModelManager.to_repo_id(model_id)
        # نفس اسم المجلد الذي يبحث عنه محرك التفريغ، حتى يجد النموذج بعد تحميله
        current_download_dir = os.path.join(base_dir, ModelManager.folder_name_for(repo_id))
        try:
            os.makedirs(current_download_dir, exist_ok=True)
        except Exception as e:
            wx.MessageBox(self.i18n.get("msg_download_error", error=str(e)), self.i18n.get("dialog_error_title"), wx.ICON_ERROR)
            return
        self.current_repo_id = repo_id
        
        self.panel_info.Hide()
        self.panel_manage.Hide()
        self.panel_selection.Disable()
        
        self.panel_progress.Show()
        self.btn_start.Hide()
        self.btn_hide.Show()
        
        self.progress_bar.SetValue(0)
        total_size_str = self.format_size(self.current_expected_size) if self.current_expected_size > 0 else "..."
        
        self.progress_list.SetItem(0, 1, self.i18n.get("dl_msg_init_conn"))
        self.progress_list.SetItem(1, 1, total_size_str)
        self.progress_list.SetItem(2, 1, "0%")
        self.progress_list.SetItem(3, 1, f"0 {self.i18n.get('unit_b_s', 'B/s')}")
        self.progress_list.SetItem(4, 1, f"0 {self.i18n.get('unit_b', 'B')}")
        self.progress_list.SetItem(5, 1, total_size_str)
        self.progress_list.SetItem(6, 1, "...")
        
        self.panel.Layout()
        self.is_downloading = True
        
        self.download_thread = ModelDownloadThread(self, repo_id, current_download_dir, self.current_expected_size, self.i18n)

    def on_download_progress(self, event):
        if not hasattr(self, 'is_downloading') or not self.is_downloading: return
        
        self.progress_bar.SetValue(event.percent)
        
        self.progress_list.SetItem(0, 1, self.i18n.get("dl_msg_receiving"))
        self.progress_list.SetItem(1, 1, event.total)
        self.progress_list.SetItem(2, 1, f"{event.percent}%")
        self.progress_list.SetItem(3, 1, event.speed)
        
        downloaded_text = f"{event.downloaded} {self.i18n.get('word_from', 'من')} {event.total}"
        self.progress_list.SetItem(4, 1, downloaded_text)
        
        self.progress_list.SetItem(5, 1, event.remaining)
        self.progress_list.SetItem(6, 1, event.eta)

    def on_download_result(self, event):
        if not hasattr(self, 'is_downloading'): return
        
        if event.status == "success":
            self.progress_bar.SetValue(100)
            self.progress_list.SetItem(0, 1, self.i18n.get("dl_msg_complete"))
            self.progress_list.SetItem(2, 1, "100%")
            self.progress_list.SetItem(5, 1, f"0 {self.i18n.get('unit_b', 'B')}")
            self.is_downloading = False
            self.offer_to_use_model(event.data)
            self.cleanup_and_destroy()
        elif event.status == "error":
            self.progress_bar.SetValue(0)
            self.progress_list.SetItem(0, 1, self.i18n.get("dl_msg_failed"))
            self.is_downloading = False
            wx.MessageBox(self.i18n.get("msg_download_error", error=event.data), self.i18n.get("dialog_error_title"), wx.ICON_ERROR)
            self.cleanup_and_destroy()

    def offer_to_use_model(self, save_dir):
        """بعد نجاح التحميل: سؤال المستخدم هل يريد اعتماد النموذج الجديد في التفريغ"""
        settings = getattr(self.parent_window, 'settings', None)
        msg = self.i18n.get("msg_download_success")
        if not settings:
            wx.MessageBox(msg, self.i18n.get("dialog_success_title"), wx.ICON_INFORMATION)
            return
        dlg = wx.MessageDialog(self, msg + "\n\n" + self.i18n.get("msg_use_downloaded_model"),
                               self.i18n.get("dialog_success_title"), wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            in_default_dir = os.path.normcase(os.path.dirname(os.path.abspath(save_dir))) == os.path.normcase(ModelManager.get_models_dir())
            settings.update({
                "model_size": getattr(self, 'current_repo_id', ""),
                # لو حُمّل في مجلد غير الافتراضي نحفظ مساره صراحة
                "local_model_path": "" if in_default_dir else save_dir,
            })
        dlg.Destroy()

    def on_hide(self, event):
        self.Hide()

    def on_cancel(self, event):
        self.Close()

    def on_close_window(self, event):
        if self.is_downloading:
            dlg = wx.MessageDialog(self, self.i18n.get("dl_msg_confirm_hide"), self.i18n.get("dialog_warning_title"), wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION)
            dlg.SetYesNoLabels(self.i18n.get("dl_btn_hide_bg"), self.i18n.get("dl_btn_stop_dl"))
            res = dlg.ShowModal()
            dlg.Destroy()
            if res == wx.ID_YES:
                self.on_hide(None)
                if isinstance(event, wx.CloseEvent) and event.CanVeto(): event.Veto()
                return
            elif res == wx.ID_NO:
                if self.download_thread: self.download_thread.abort()
                self.cleanup_and_destroy()
            else: 
                if isinstance(event, wx.CloseEvent) and event.CanVeto(): event.Veto()
                return 
        else: self.cleanup_and_destroy()

    def apply_theme(self, theme):
        if theme == "dark": bg_color, panel_bg, fg_color, input_bg = wx.Colour(15,19,28), wx.Colour(22,29,43), wx.Colour(241,241,241), wx.Colour(10,13,18)
        else: bg_color, panel_bg, fg_color, input_bg = wx.Colour(248,249,250), wx.Colour(255,255,255), wx.Colour(33,37,41), wx.Colour(255,255,255)
        self.SetBackgroundColour(bg_color)
        self.SetForegroundColour(fg_color)
        for child in self.GetChildren(): self.apply_theme_to_widget(child, panel_bg, fg_color, input_bg)
        self.Refresh()

    def apply_theme_to_widget(self, widget, bg_color, fg_color, input_bg):
        try:
            if isinstance(widget, (wx.TextCtrl, wx.ListCtrl, wx.Choice)): widget.SetBackgroundColour(input_bg)
            else: widget.SetBackgroundColour(bg_color)
            widget.SetForegroundColour(fg_color)
            for child in widget.GetChildren(): self.apply_theme_to_widget(child, bg_color, fg_color, input_bg)
        except: pass