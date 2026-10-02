"""القوائم واختصاراتها، وفتح النوافذ الفرعية (الإعدادات، النماذج، القاموس، السجل...)"""
import wx
from core import dictionaries
from gui.settings_dialog import SettingsDialog
from gui.download_dialog import DownloadDialog
from gui.about_dialog import AboutDialog
from gui.history_dialog import HistoryDialog
from gui.custom_dict_dialog import CustomDictDialog
from gui import icons

from gui.main.common import SEEK_SECONDS


class MenusMixin:
    """جزء من النافذة الرئيسية (MainWindow): القوائم واختصاراتها، وفتح النوافذ الفرعية (الإعدادات، النماذج، القاموس، السجل...)"""

    def _menu_labels(self):
        """نصوص عناصر القوائم مع اختصاراتها (تُستخدم عند الإنشاء وعند تغيير اللغة)"""
        return {
            "mi_select_audio": self.i18n.get("btn_select_audio") + "\tCtrl+O",
            "mi_select_folder": self.i18n.get("btn_select_folder") + "\tCtrl+M",
            "mi_open_srt": self.i18n.get("menu_open_srt") + "\tCtrl+Shift+O",
            "mi_export": self.i18n.get("menu_export_srt") + "\tCtrl+S",
            "mi_exit": self.i18n.get("menu_exit") + "\tAlt+F4",
            "mi_focus_filter": self.i18n.get("menu_focus_search") + "\tCtrl+F",
            "mi_edit_segment": self.i18n.get("menu_edit_segment") + "\tF2",
            "mi_merge_next": self.i18n.get("menu_merge_next") + "\tCtrl+J",
            "mi_pause_audio": self.i18n.get("menu_pause_audio") + "\tF3",
            "mi_seek_back": self.i18n.get("menu_seek_back") + "\tAlt+Left",
            "mi_seek_forward": self.i18n.get("menu_seek_forward") + "\tAlt+Right",
            "mi_sentence_only": self.i18n.get("menu_sentence_only"),
            "mi_stop_audio": self.i18n.get("menu_stop_audio") + "\tF4",
            "mi_check_progress": self.i18n.get("menu_check_progress") + "\tCtrl+I",
            "mi_history": self.i18n.get("menu_history") + "\tCtrl+H",
            "mi_settings": self.i18n.get("menu_settings") + "\tCtrl+P",
            "mi_download_model": self.i18n.get("menu_download_model") + "\tCtrl+D",
            "mi_custom_dict": self.i18n.get("btn_custom_dictionary") + "\tCtrl+K",
            "mi_apply_dict": self.i18n.get("menu_apply_dictionary") + "\tCtrl+Shift+K",
            "mi_guide": self.i18n.get("menu_guide") + "\tF1",
            "mi_shortcuts": self.i18n.get("menu_shortcuts") + "\tShift+F1",
            "mi_about": self.i18n.get("menu_about"),
        }

    def setup_menu(self):
        labels = self._menu_labels()
        menubar = wx.MenuBar()
        file_menu = wx.Menu()
        self.mi_select_audio = icons.menu_item(file_menu, wx.ID_ANY, labels["mi_select_audio"], "audio_file")
        self.mi_select_folder = icons.menu_item(file_menu, wx.ID_ANY, labels["mi_select_folder"], "folder")
        self.mi_open_srt = icons.menu_item(file_menu, wx.ID_ANY, labels["mi_open_srt"], "subtitle")
        file_menu.AppendSeparator()
        self.mi_export = icons.menu_item(file_menu, wx.ID_ANY, labels["mi_export"], "save")
        file_menu.AppendSeparator()
        self.mi_exit = icons.menu_item(file_menu, wx.ID_EXIT, labels["mi_exit"], "exit")

        view_menu = wx.Menu()
        self.mi_focus_filter = icons.menu_item(view_menu, wx.ID_ANY, labels["mi_focus_filter"], "search")
        self.mi_edit_segment = icons.menu_item(view_menu, wx.ID_ANY, labels["mi_edit_segment"], "edit")
        self.mi_merge_next = icons.menu_item(view_menu, wx.ID_ANY, labels["mi_merge_next"], "merge")
        view_menu.AppendSeparator()
        self.mi_pause_audio = icons.menu_item(view_menu, wx.ID_ANY, labels["mi_pause_audio"], "pause")
        self.mi_seek_back = icons.menu_item(view_menu, wx.ID_ANY, labels["mi_seek_back"], "back")
        self.mi_seek_forward = icons.menu_item(view_menu, wx.ID_ANY, labels["mi_seek_forward"], "forward")
        # خيار دائم: Enter على سطر يشغّل الجملة ويتوقف في آخرها (للمراجعة)، أو يكمل لآخر الملف
        self.mi_sentence_only = view_menu.AppendCheckItem(wx.ID_ANY, labels["mi_sentence_only"])
        self.mi_sentence_only.Check(self.settings.get("play_sentence_only", True))
        self.mi_stop_audio = icons.menu_item(view_menu, wx.ID_ANY, labels["mi_stop_audio"], "stop")
        self.mi_check_progress = icons.menu_item(view_menu, wx.ID_ANY, labels["mi_check_progress"], "progress")
        view_menu.AppendSeparator()
        self.mi_history = icons.menu_item(view_menu, wx.ID_ANY, labels["mi_history"], "history")

        tools_menu = wx.Menu()
        self.mi_settings = icons.menu_item(tools_menu, wx.ID_ANY, labels["mi_settings"], "settings")
        tools_menu.AppendSeparator()
        self.mi_download_model = icons.menu_item(tools_menu, wx.ID_ANY, labels["mi_download_model"], "download")
        self.mi_custom_dict = icons.menu_item(tools_menu, wx.ID_ANY, labels["mi_custom_dict"], "dictionary")
        self.mi_apply_dict = icons.menu_item(tools_menu, wx.ID_ANY, labels["mi_apply_dict"], "apply")

        help_menu = wx.Menu()
        self.mi_guide = icons.menu_item(help_menu, wx.ID_ANY, labels["mi_guide"], "guide")
        self.mi_shortcuts = icons.menu_item(help_menu, wx.ID_ANY, labels["mi_shortcuts"], "keyboard")
        self.mi_about = icons.menu_item(help_menu, wx.ID_ANY, labels["mi_about"], "info")

        menubar.Append(file_menu, self.i18n.get("menu_file"))
        menubar.Append(view_menu, self.i18n.get("menu_view"))
        menubar.Append(tools_menu, self.i18n.get("menu_tools"))
        menubar.Append(help_menu, self.i18n.get("menu_help"))
        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.on_select_audio, self.mi_select_audio)
        self.Bind(wx.EVT_MENU, self.on_select_folder, self.mi_select_folder)
        self.Bind(wx.EVT_MENU, self.on_open_srt, self.mi_open_srt)
        self.Bind(wx.EVT_MENU, self.on_export_srt, self.mi_export)
        self.Bind(wx.EVT_MENU, self.open_settings, self.mi_settings)
        self.Bind(wx.EVT_MENU, self.on_focus_filter, self.mi_focus_filter)
        self.Bind(wx.EVT_MENU, self.on_edit_segment, self.mi_edit_segment)
        self.Bind(wx.EVT_MENU, self.on_merge_next, self.mi_merge_next)
        self.Bind(wx.EVT_MENU, lambda e: self.audio_player.on_play(None), self.mi_pause_audio)
        self.Bind(wx.EVT_MENU, lambda e: self.audio_player.seek_relative(-SEEK_SECONDS), self.mi_seek_back)
        self.Bind(wx.EVT_MENU, lambda e: self.audio_player.seek_relative(SEEK_SECONDS), self.mi_seek_forward)
        self.Bind(wx.EVT_MENU, lambda e: self.settings.set("play_sentence_only", self.mi_sentence_only.IsChecked()), self.mi_sentence_only)
        self.Bind(wx.EVT_MENU, self.on_stop_audio, self.mi_stop_audio)
        self.Bind(wx.EVT_MENU, self.on_check_progress, self.mi_check_progress)
        self.Bind(wx.EVT_MENU, self.on_open_download_dialog, self.mi_download_model)
        self.Bind(wx.EVT_MENU, self.on_open_custom_dict, self.mi_custom_dict)
        self.Bind(wx.EVT_MENU, self.on_apply_dictionary, self.mi_apply_dict)
        self.Bind(wx.EVT_MENU, self.on_open_history, self.mi_history)
        self.Bind(wx.EVT_MENU, self.on_guide, self.mi_guide)
        self.Bind(wx.EVT_MENU, self.on_shortcuts, self.mi_shortcuts)
        self.Bind(wx.EVT_MENU, self.on_about, self.mi_about)
        self.Bind(wx.EVT_MENU, self.on_exit, self.mi_exit)

        self.mi_export.Enable(False)

    def on_focus_filter(self, event):
        self.notebook.SetSelection(0)
        self.txt_filter.SetFocus()
        self.txt_filter.SelectAll()

    def open_settings(self, event):
        dlg = SettingsDialog(self, self.i18n, self.settings)
        dlg.ShowModal()
        dlg.Destroy()

    def on_open_download_dialog(self, event, preselect=None):
        if not getattr(self, 'download_dialog', None):
            self.download_dialog = DownloadDialog(self, self.i18n, preselect=preselect)
            self.download_dialog.Show()
        else:
            if self.download_dialog.IsIconized(): self.download_dialog.Restore()
            self.download_dialog.Show()
            self.download_dialog.Raise()

    def on_open_custom_dict(self, event):
        dlg = CustomDictDialog(self, self.i18n, self.settings)
        dlg.ShowModal()
        dlg.Destroy()
        self.refresh_dictionary_choice()

    def refresh_dictionary_choice(self):
        names = dictionaries.names(self.settings)
        self.cb_dictionary.Set(names)
        self.cb_dictionary.SetStringSelection(dictionaries.active_name(self.settings))
        self.transcription_panel.Layout()

    def on_dictionary_chosen(self, event):
        dictionaries.set_active(self.settings, self.cb_dictionary.GetStringSelection())
        self.status_bar.SetStatusText(self.i18n.get("status_dictionary_chosen", name=self.cb_dictionary.GetStringSelection()))

    def shortcuts_text(self):
        """قائمة الاختصارات تُبنى من القوائم نفسها، فتبقى صحيحة لو تغيّر أي اختصار"""
        lines = [self.i18n.get("shortcuts_menus_title")]
        for label in self._menu_labels().values():
            if "\t" in label:
                name, key = label.split("\t", 1)
                lines.append(f"{key}: {name}")
        lines += ["", self.i18n.get("shortcuts_more_title")]
        lines += [self.i18n.get(k) for k in ("shortcut_enter_play", "shortcut_context_menu", "shortcut_switch_tabs",
                                             "shortcut_edit_dialog", "shortcut_processing", "shortcut_dict_delete",
                                             "shortcut_escape")]
        return "\n".join(lines)

    def on_guide(self, event):
        """دليل الاستخدام بلغة الواجهة الحالية"""
        from core.guide import load_guide
        from gui.text_dialog import TextDialog
        dlg = TextDialog(self, self.i18n, self.i18n.get("menu_guide"), load_guide(self.i18n.language), size=(760, 640))
        dlg.ShowModal()
        dlg.Destroy()

    def on_shortcuts(self, event):
        from gui.text_dialog import TextDialog
        dlg = TextDialog(self, self.i18n, self.i18n.get("menu_shortcuts"), self.shortcuts_text())
        dlg.ShowModal()
        dlg.Destroy()

    def on_about(self, event):
        dlg = AboutDialog(self, self.i18n)
        dlg.ShowModal()
        dlg.Destroy()

    def on_open_history(self, event):
        dlg = HistoryDialog(self, self.i18n)
        dlg.ShowModal()
        dlg.Destroy()

    def on_check_progress(self, event):
        # التفريغ في الخلفية: Ctrl+I يعيد نافذة المعالجة، وفيها النسبة والنص حتى الآن
        if self.processing_dialog and not self.processing_dialog.IsShown():
            self.show_processing_dialog()
            return
        if self.current_percent is not None:
            msg_template = self.i18n.get("msg_progress_info")
            if "{percent}" in msg_template:
                msg = msg_template.format(percent=self.current_percent)
            else:
                msg = f"Progress: {self.current_percent}%"
            wx.MessageBox(msg, self.i18n.get("dialog_progress_title"), wx.ICON_INFORMATION)
        else:
            wx.MessageBox(self.i18n.get("msg_no_active_process"), self.i18n.get("dialog_progress_title"), wx.ICON_INFORMATION)

    def show_error(self, error):
        msg_temp = self.i18n.get("status_error")
        msg = msg_temp.format(error=str(error)) if "{error}" in msg_temp else str(error)
        wx.MessageBox(msg, self.i18n.get("dialog_error_title"), wx.ICON_ERROR)
