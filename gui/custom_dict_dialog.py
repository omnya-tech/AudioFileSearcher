import os
import wx
from gui import icons, widgets
from core.i18n import LocalizationManager
from core.learning import LearningStore
from core.settings import SettingsManager
from core import dictionaries


class CustomDictDialog(wx.Dialog):
    """
    إدارة قواميس المجالات: لكل مجال (قرآن، محاضرات...) تصحيحاته ومصطلحاته.
    التعديلات على نسخة، ولا تُحفظ إلا بـ «موافق»، والقاموس المختار عندها يصبح قاموس التفريغ.
    """

    def __init__(self, parent, i18n: LocalizationManager, settings: SettingsManager):
        super().__init__(parent, title=i18n.get("dialog_custom_dict_title"), size=(640, 560),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.i18n = i18n
        i18n.apply_direction(self)
        widgets.fit_to_screen(self)
        self.settings = settings
        self.profiles = dictionaries.all_profiles(settings)
        self.current = dictionaries.active_name(settings)
        self.learning = LearningStore()
        self._removed = set()
        self.setup_ui()
        self.refresh_profiles()
        self.apply_theme(self.settings.get("theme", "light"))
        self.CenterOnParent()

    @property
    def profile(self):
        return self.profiles.setdefault(self.current, dictionaries.empty())

    # ------------------------------------------------------------------ الواجهة
    def setup_ui(self):
        panel = wx.Panel(self)
        main = wx.BoxSizer(wx.VERTICAL)

        # اختيار القاموس وإدارته
        top = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(panel, label=self.i18n.get("lbl_dictionary"))
        self.cb_profile = wx.Choice(panel)
        top.Add(lbl, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        top.Add(self.cb_profile, 1, wx.ALL | wx.EXPAND, 5)
        main.Add(top, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        manage = wx.WrapSizer(wx.HORIZONTAL)
        self.btn_new = icons.button(wx.Button(panel, label=self.i18n.get("btn_dict_new")), "add")
        self.btn_rename = icons.button(wx.Button(panel, label=self.i18n.get("btn_dict_rename")), "edit")
        self.btn_delete_profile = icons.button(wx.Button(panel, label=self.i18n.get("btn_dict_delete")), "delete")
        self.btn_import = icons.button(wx.Button(panel, label=self.i18n.get("btn_dict_import")), "folder")
        self.btn_export = icons.button(wx.Button(panel, label=self.i18n.get("btn_dict_export")), "save")
        for b in (self.btn_new, self.btn_rename, self.btn_delete_profile, self.btn_import, self.btn_export):
            manage.Add(b, 0, wx.ALL, 3)
        main.Add(manage, 0, wx.LEFT | wx.RIGHT, 10)

        self.notebook = wx.Notebook(panel)
        self.page_corr = wx.Panel(self.notebook)
        self.page_terms = wx.Panel(self.notebook)
        self.setup_corrections_page(self.page_corr)
        self.setup_terms_page(self.page_terms)
        self.notebook.AddPage(self.page_corr, self.i18n.get("tab_corrections"))
        self.notebook.AddPage(self.page_terms, self.i18n.get("tab_terms"))
        self.i18n.fix_notebook(self.notebook)
        main.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 10)

        bottom = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_ok = icons.button(wx.Button(panel, id=wx.ID_OK, label=self.i18n.get("btn_ok")), "ok")
        # زر إلغاء صريح: يجعل مفتاح Esc يغلق النافذة دون حفظ
        self.btn_cancel = icons.button(wx.Button(panel, id=wx.ID_CANCEL, label=self.i18n.get("btn_cancel")), "cancel")
        bottom.AddStretchSpacer(1)
        bottom.Add(self.btn_ok, 0, wx.RIGHT, 10)
        bottom.Add(self.btn_cancel, 0)
        main.Add(bottom, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        panel.SetSizer(main)

        self.cb_profile.Bind(wx.EVT_CHOICE, self.on_profile_selected)
        self.btn_new.Bind(wx.EVT_BUTTON, self.on_new)
        self.btn_rename.Bind(wx.EVT_BUTTON, self.on_rename)
        self.btn_delete_profile.Bind(wx.EVT_BUTTON, self.on_delete_profile)
        self.btn_import.Bind(wx.EVT_BUTTON, self.on_import)
        self.btn_export.Bind(wx.EVT_BUTTON, self.on_export)
        self.btn_ok.Bind(wx.EVT_BUTTON, self.on_ok)

    def setup_corrections_page(self, page):
        sizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(2, 2, 8, 10)
        grid.AddGrowableCol(1, 1)
        grid.Add(wx.StaticText(page, label=self.i18n.get("lbl_wrong_word")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_wrong = wx.TextCtrl(page, style=wx.TE_PROCESS_ENTER)
        grid.Add(self.txt_wrong, 1, wx.EXPAND)
        grid.Add(wx.StaticText(page, label=self.i18n.get("lbl_correct_word")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_correct = wx.TextCtrl(page, style=wx.TE_PROCESS_ENTER)
        grid.Add(self.txt_correct, 1, wx.EXPAND)
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 8)

        self.btn_add = icons.button(wx.Button(page, label=self.i18n.get("btn_add_word")), "add")
        sizer.Add(self.btn_add, 0, wx.LEFT | wx.RIGHT, 8)

        sizer.Add(wx.StaticText(page, label=self.i18n.get("lbl_dict_words")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.dict_list = wx.ListCtrl(page, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES)
        self.dict_list.InsertColumn(0, self.i18n.get("lbl_wrong_word"), width=self.FromDIP(180))
        self.dict_list.InsertColumn(1, self.i18n.get("lbl_correct_word"), width=self.FromDIP(200))
        # كم مرة صحّح المستخدم هذه الكلمة بنفسه (0 = أُضيفت يدوياً)
        self.dict_list.InsertColumn(2, self.i18n.get("col_times_corrected"), width=self.FromDIP(90))
        widgets.auto_fit_first_column(self.dict_list, column=1, min_width=self.FromDIP(120))
        sizer.Add(self.dict_list, 1, wx.EXPAND | wx.ALL, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_remove = icons.button(wx.Button(page, label=self.i18n.get("btn_remove_word")), "delete")
        self.btn_clear = icons.button(wx.Button(page, label=self.i18n.get("btn_clear_dict")), "clear")
        row.Add(self.btn_remove, 0, wx.RIGHT, 10)
        row.Add(self.btn_clear, 0)
        sizer.Add(row, 0, wx.ALL, 8)
        page.SetSizer(sizer)

        # Enter في خانات الكتابة يضيف الكلمة (ولا يغلق النافذة بالخطأ)
        self.txt_wrong.Bind(wx.EVT_TEXT_ENTER, self.on_add)
        self.txt_correct.Bind(wx.EVT_TEXT_ENTER, self.on_add)
        self.btn_add.Bind(wx.EVT_BUTTON, self.on_add)
        self.btn_remove.Bind(wx.EVT_BUTTON, self.on_remove)
        self.btn_clear.Bind(wx.EVT_BUTTON, self.on_clear)
        self.dict_list.Bind(wx.EVT_KEY_DOWN, self.on_list_key)

    def setup_terms_page(self, page):
        sizer = wx.BoxSizer(wx.VERTICAL)
        # شرح قصير يصل إليه Tab (نص للقراءة فقط)، لأن الفرق بين المصطلحات والتصحيحات غير بديهي
        note = wx.TextCtrl(page, value=self.i18n.get("terms_explanation"),
                           style=wx.TE_READONLY | wx.TE_MULTILINE | wx.BORDER_NONE | wx.TE_NO_VSCROLL)
        note.SetBackgroundColour(page.GetBackgroundColour())
        note.SetMinSize((-1, note.FromDIP(48)))
        sizer.Add(note, 0, wx.EXPAND | wx.ALL, 8)

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(wx.StaticText(page, label=self.i18n.get("lbl_term")), 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        self.txt_term = wx.TextCtrl(page, style=wx.TE_PROCESS_ENTER)
        row.Add(self.txt_term, 1, wx.ALL | wx.EXPAND, 5)
        self.btn_add_term = icons.button(wx.Button(page, label=self.i18n.get("btn_add_word")), "add")
        row.Add(self.btn_add_term, 0, wx.ALL, 5)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 3)

        sizer.Add(wx.StaticText(page, label=self.i18n.get("lbl_terms_list")), 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
        self.terms_list = wx.ListCtrl(page, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER)
        self.terms_list.InsertColumn(0, self.i18n.get("lbl_term"), width=self.FromDIP(400))
        widgets.auto_fit_first_column(self.terms_list)
        sizer.Add(self.terms_list, 1, wx.EXPAND | wx.ALL, 8)

        self.btn_remove_term = icons.button(wx.Button(page, label=self.i18n.get("btn_remove_word")), "delete")
        sizer.Add(self.btn_remove_term, 0, wx.ALL, 8)
        page.SetSizer(sizer)

        self.txt_term.Bind(wx.EVT_TEXT_ENTER, self.on_add_term)
        self.btn_add_term.Bind(wx.EVT_BUTTON, self.on_add_term)
        self.btn_remove_term.Bind(wx.EVT_BUTTON, self.on_remove_term)
        self.terms_list.Bind(wx.EVT_KEY_DOWN, self.on_terms_key)

    # ------------------------------------------------------------------ عرض المحتوى
    def refresh_profiles(self):
        names = list(self.profiles)
        self.cb_profile.Set(names)
        self.cb_profile.SetSelection(names.index(self.current) if self.current in names else 0)
        self.current = self.cb_profile.GetStringSelection()
        self.btn_delete_profile.Enable(len(names) > 1)
        self.populate_list()
        self.populate_terms()

    def populate_list(self):
        self.dict_list.DeleteAllItems()
        counts = {}
        for entry in self.learning.corrections():
            counts[entry["wrong"]] = counts.get(entry["wrong"], 0) + entry.get("count", 0)
        for wrong, correct in self.profile["corrections"].items():
            idx = self.dict_list.InsertItem(self.dict_list.GetItemCount(), wrong)
            self.dict_list.SetItem(idx, 1, correct)
            self.dict_list.SetItem(idx, 2, str(counts.get(wrong, 0)))

    def populate_terms(self):
        self.terms_list.DeleteAllItems()
        for term in self.profile["terms"]:
            self.terms_list.InsertItem(self.terms_list.GetItemCount(), term)

    @staticmethod
    def _reselect(lst, index, fallback):
        """إبقاء التركيز في القائمة على السطر التالي بعد الحذف، حتى لا يضيع مكان مستخدم قارئ الشاشة"""
        count = lst.GetItemCount()
        if count:
            index = min(index, count - 1)
            lst.Select(index); lst.Focus(index); lst.SetFocus()
        else:
            fallback.SetFocus()

    # ------------------------------------------------------------------ التصحيحات
    def on_add(self, event):
        wrong = self.txt_wrong.GetValue().strip()
        correct = self.txt_correct.GetValue().strip()
        if not wrong:
            self.txt_wrong.SetFocus(); return
        if not correct:
            self.txt_correct.SetFocus(); return
        if wrong != correct:
            self.profile["corrections"][wrong] = correct
            self.populate_list()
            self.txt_wrong.SetValue("")
            self.txt_correct.SetValue("")
            self.txt_wrong.SetFocus()

    def on_list_key(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE:
            self.on_remove(None)
        else:
            event.Skip()

    def on_remove(self, event):
        sel = self.dict_list.GetFirstSelected()
        if sel == -1:
            return
        wrong = self.dict_list.GetItemText(sel)
        if self.profile["corrections"].pop(wrong, None) is not None:
            self._removed.add(wrong)
        self.populate_list()
        self._reselect(self.dict_list, sel, self.txt_wrong)

    def on_clear(self, event):
        if not self.profile["corrections"]:
            return
        dlg = wx.MessageDialog(self, self.i18n.get("msg_clear_dict_confirm"), self.i18n.get("dialog_warning_title"),
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
        if dlg.ShowModal() == wx.ID_YES:
            self._removed.update(self.profile["corrections"])
            self.profile["corrections"].clear()
            self.populate_list()
            self.txt_wrong.SetFocus()
        dlg.Destroy()

    # ------------------------------------------------------------------ المصطلحات
    def on_add_term(self, event):
        term = self.txt_term.GetValue().strip()
        if not term:
            return
        if term not in self.profile["terms"]:
            self.profile["terms"].append(term)
            self.populate_terms()
        self.txt_term.SetValue("")
        self.txt_term.SetFocus()

    def on_terms_key(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE:
            self.on_remove_term(None)
        else:
            event.Skip()

    def on_remove_term(self, event):
        sel = self.terms_list.GetFirstSelected()
        if sel == -1:
            return
        term = self.terms_list.GetItemText(sel)
        if term in self.profile["terms"]:
            self.profile["terms"].remove(term)
        self.populate_terms()
        self._reselect(self.terms_list, sel, self.txt_term)

    # ------------------------------------------------------------------ إدارة القواميس
    def on_profile_selected(self, event):
        self.current = self.cb_profile.GetStringSelection()
        self.populate_list()
        self.populate_terms()

    def _ask_name(self, title_key, value=""):
        """اسم قاموس جديد أو معدل: غير فارغ وغير مكرر. ترجع None لو تراجع المستخدم"""
        original = value
        while True:
            dlg = wx.TextEntryDialog(self, self.i18n.get("msg_dict_name"), self.i18n.get(title_key), value)
            ok = dlg.ShowModal() == wx.ID_OK
            name = dlg.GetValue().strip()
            dlg.Destroy()
            if not ok:
                return None
            if name and (name == original or name not in self.profiles):
                return name
            wx.MessageBox(self.i18n.get("msg_dict_name_taken" if name else "msg_dict_name_empty"),
                          self.i18n.get("dialog_warning_title"), wx.ICON_WARNING)
            value = name

    def on_new(self, event):
        name = self._ask_name("btn_dict_new")
        if name:
            self.profiles[name] = dictionaries.empty()
            self.current = name
            self.refresh_profiles()
            self.txt_wrong.SetFocus()

    def on_rename(self, event):
        name = self._ask_name("btn_dict_rename", self.current)
        if name and name != self.current:
            # الحفاظ على ترتيب القواميس
            self.profiles = {(name if k == self.current else k): v for k, v in self.profiles.items()}
            self.current = name
            self.refresh_profiles()

    def on_delete_profile(self, event):
        if len(self.profiles) <= 1:
            return
        dlg = wx.MessageDialog(self, self.i18n.get("msg_dict_delete_confirm", name=self.current),
                               self.i18n.get("dialog_warning_title"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
        if dlg.ShowModal() == wx.ID_YES:
            self._removed.update(self.profile["corrections"])
            del self.profiles[self.current]
            self.current = next(iter(self.profiles))
            self.refresh_profiles()
            self.cb_profile.SetFocus()
        dlg.Destroy()

    def on_import(self, event):
        wildcard = (f"{self.i18n.get('wc_dictionary')} (*.json;*.csv;*.txt)|*.json;*.csv;*.txt|"
                    f"{self.i18n.get('wc_all')} (*.*)|*.*")
        dlg = wx.FileDialog(self, self.i18n.get("btn_dict_import"), wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        path = dlg.GetPath() if dlg.ShowModal() == wx.ID_OK else None
        dlg.Destroy()
        if path:
            self.import_path(path)

    def import_path(self, path):
        try:
            name, imported = dictionaries.import_file(path)
        except (OSError, ValueError, UnicodeDecodeError) as e:
            wx.MessageBox(self.i18n.get("msg_dict_import_failed", error=e), self.i18n.get("dialog_error_title"), wx.ICON_ERROR)
            return

        if name in self.profiles:
            # قاموس بنفس الاسم موجود: دمج فيه، أو قاموس جديد منفصل
            ask = wx.MessageDialog(self, self.i18n.get("msg_dict_import_exists", name=name), self.i18n.get("btn_dict_import"),
                                   wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_QUESTION)
            ask.SetYesNoCancelLabels(self.i18n.get("btn_dict_merge"), self.i18n.get("btn_dict_as_new"), self.i18n.get("btn_cancel"))
            answer = ask.ShowModal()
            ask.Destroy()
            if answer == wx.ID_CANCEL:
                return
            if answer == wx.ID_YES:
                self.profiles[name] = dictionaries.merge(self.profiles[name], imported)
            else:
                n = 2
                while f"{name} ({n})" in self.profiles:
                    n += 1
                name = f"{name} ({n})"
                self.profiles[name] = imported
        else:
            self.profiles[name] = imported
        self.current = name
        self.refresh_profiles()
        wx.MessageBox(self.i18n.get("msg_dict_imported", name=name,
                                    corrections=self.i18n.plural("n_corrections", len(imported["corrections"])),
                                    terms=self.i18n.plural("n_terms", len(imported["terms"]))),
                      self.i18n.get("dialog_success_title"), wx.ICON_INFORMATION)

    def on_export(self, event):
        wildcard = f"{self.i18n.get('wc_dictionary')} (*.json)|*.json"
        dlg = wx.FileDialog(self, self.i18n.get("btn_dict_export"), defaultFile=f"{self.current}.json", wildcard=wildcard,
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if not path.lower().endswith(".json"):
                path += ".json"
            try:
                dictionaries.export_file(path, self.current, self.profile)
                wx.MessageBox(self.i18n.get("msg_dict_exported", path=os.path.basename(path)),
                              self.i18n.get("dialog_success_title"), wx.ICON_INFORMATION)
            except OSError as e:
                wx.MessageBox(self.i18n.get("status_error", error=e), self.i18n.get("dialog_error_title"), wx.ICON_ERROR)
        dlg.Destroy()

    # ------------------------------------------------------------------ الحفظ
    def on_ok(self, event):
        # القاموس المختار هنا يصبح قاموس التفريغ
        dictionaries.save_all(self.settings, self.profiles, self.current)
        # الكلمات المحذوفة من كل القواميس يُنسى تعلّمها أيضاً، حتى لا تُعطى للنموذج كتلميح بعد الآن
        still_used = {w for p in self.profiles.values() for w in p["corrections"]}
        for wrong in self._removed - still_used:
            self.learning.forget(wrong)
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Hide()

    # ------------------------------------------------------------------ المظهر
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
        if isinstance(widget, wx.Notebook):
            pass  # التبويبات يرسمها ويندوز، وتلوينها يدوياً يفسد شكلها
        elif isinstance(widget, (wx.TextCtrl, wx.ListCtrl)):
            widget.SetBackgroundColour(input_bg)
        else:
            widget.SetBackgroundColour(bg_color)
        widget.SetForegroundColour(fg_color)
        for child in widget.GetChildren():
            self.apply_theme_to_widget(child, bg_color, fg_color, input_bg)
