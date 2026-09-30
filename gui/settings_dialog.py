import wx
import os
import psutil
from core.i18n import LocalizationManager
from core.settings import SettingsManager
from core.model_manager import ModelManager

STANDARD_MODELS = ["tiny", "base", "small", "medium", "large-v3", "deepdml/faster-whisper-large-v3-turbo-ct2"]
# (الكود، الاسم المعروض) — "auto" تعني اكتشاف لغة الملف تلقائياً
TRANSCRIPTION_LANGUAGES = [("auto", None), ("ar", "العربية"), ("en", "English"), ("fr", "Français"),
                           ("es", "Español"), ("de", "Deutsch"), ("tr", "Türkçe"), ("fa", "فارسی"), ("ur", "اردو")]
COMPUTE_TYPES = ["int8", "int8_float16", "float16", "float32"]
CORRECTION_LEVELS = ["light", "medium", "aggressive"]
EXPORT_FORMATS = ["srt", "txt", "vtt", "json", "docx"]


TEMPERATURE_VALUES = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
NO_SPEECH_VALUES = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


class FloatChoice(wx.Choice):
    """قائمة أرقام عشرية بنفس واجهة SpinCtrlDouble (GetValue/SetValue) لكنها تُقرأ بقارئ الشاشة"""

    def __init__(self, parent, values):
        super().__init__(parent, choices=[f"{v:g}" for v in values])
        self.values = values

    def SetValue(self, value):
        # أقرب قيمة متاحة، حتى لو كانت القيمة المحفوظة من إصدار قديم خارج القائمة
        idx = min(range(len(self.values)), key=lambda i: abs(self.values[i] - float(value)))
        self.SetSelection(idx)

    def GetValue(self):
        return self.values[max(self.GetSelection(), 0)]


def readonly_note(parent, text):
    """ملاحظة نصية تُقرأ بقارئ الشاشة: حقل للقراءة فقط بدون إطار (يصل إليه Tab، عكس النص الثابت)"""
    ctrl = wx.TextCtrl(parent, value=text, style=wx.TE_READONLY | wx.BORDER_NONE | wx.TE_MULTILINE | wx.TE_NO_VSCROLL)
    ctrl.SetBackgroundColour(parent.GetBackgroundColour())
    ctrl.SetMinSize((-1, 40))
    return ctrl


class SettingsDialog(wx.Dialog):
    def __init__(self, parent, i18n: LocalizationManager, settings: SettingsManager):
        super().__init__(parent, title=i18n.get("settings_title"), size=(620, 720), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.i18n = i18n
        i18n.apply_direction(self)
        self.settings = settings
        self.parent_window = parent
        self.setup_ui()
        self.load_settings()
        self.CenterOnParent()

    def setup_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.notebook = wx.Notebook(panel)
        self.page_engine = wx.Panel(self.notebook)
        self.page_advanced = wx.ScrolledWindow(self.notebook)
        self.page_output = wx.Panel(self.notebook)
        self.page_correction = wx.Panel(self.notebook)
        self.page_appearance = wx.Panel(self.notebook)

        self.setup_engine_page()
        self.setup_advanced_page()
        self.setup_output_page()
        self.setup_correction_page()
        self.setup_appearance_page()

        self.notebook.AddPage(self.page_engine, self.i18n.get("tab_engine"))
        self.notebook.AddPage(self.page_advanced, self.i18n.get("tab_advanced"))
        self.notebook.AddPage(self.page_output, self.i18n.get("tab_output"))
        self.notebook.AddPage(self.page_correction, self.i18n.get("tab_correction"))
        self.notebook.AddPage(self.page_appearance, self.i18n.get("tab_appearance"))
        self.i18n.fix_notebook(self.notebook)

        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_reset = wx.Button(panel, label=self.i18n.get("btn_reset"))
        self.btn_save = wx.Button(panel, id=wx.ID_OK, label=self.i18n.get("btn_save"))
        self.btn_cancel = wx.Button(panel, id=wx.ID_CANCEL, label=self.i18n.get("btn_cancel"))

        btn_sizer.Add(self.btn_reset, 0, wx.ALL, 5)
        btn_sizer.AddStretchSpacer(1)
        btn_sizer.Add(self.btn_save, 0, wx.ALL, 5)
        btn_sizer.Add(self.btn_cancel, 0, wx.ALL, 5)

        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)
        panel.SetSizer(main_sizer)

        self.btn_reset.Bind(wx.EVT_BUTTON, self.on_reset)
        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)

    # ------------------------------------------------------------------ صفحة المحرك
    def setup_engine_page(self):
        page = self.page_engine
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl_mode = wx.StaticText(page, label=self.i18n.get("lbl_user_mode"))
        self.cb_mode = wx.Choice(page, choices=[self.i18n.get("mode_beginner"), self.i18n.get("mode_advanced")])
        self.cb_mode.Bind(wx.EVT_CHOICE, self.on_mode_changed)
        sizer.Add(lbl_mode, 0, wx.ALL, 5)
        sizer.Add(self.cb_mode, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        lbl_model = wx.StaticText(page, label=self.i18n.get("lbl_model_size"))
        self.cb_model = wx.Choice(page, choices=list(STANDARD_MODELS))
        self.btn_auto_suggest = wx.Button(page, label=self.i18n.get("btn_auto_suggest"))
        self.btn_auto_suggest.Bind(wx.EVT_BUTTON, self.on_auto_suggest)
        model_sizer = wx.BoxSizer(wx.HORIZONTAL)
        model_sizer.Add(self.cb_model, 1, wx.EXPAND | wx.RIGHT, 5)
        model_sizer.Add(self.btn_auto_suggest, 0)
        sizer.Add(lbl_model, 0, wx.ALL, 5)
        sizer.Add(model_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # حالة النموذج (مثبت أم لا) في حقل للقراءة فقط يصل إليه Tab بعد قائمة النماذج مباشرة
        lbl_state = wx.StaticText(page, label=self.i18n.get("lbl_model_state"))
        self.lbl_model_state = readonly_note(page, "")
        sizer.Add(lbl_state, 0, wx.LEFT | wx.RIGHT | wx.TOP, 5)
        sizer.Add(self.lbl_model_state, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        self.cb_model.Bind(wx.EVT_CHOICE, lambda e: self.update_model_state())

        lbl_local = wx.StaticText(page, label=self.i18n.get("lbl_local_model_path"))
        self.txt_local_model = wx.TextCtrl(page, style=wx.TE_READONLY)
        btn_browse_model = wx.Button(page, label=self.i18n.get("btn_browse_model"))
        btn_clear_model = wx.Button(page, label=self.i18n.get("btn_clear"))
        btn_browse_model.Bind(wx.EVT_BUTTON, self.on_browse_model)
        btn_clear_model.Bind(wx.EVT_BUTTON, self.on_clear_model)
        local_sizer = wx.BoxSizer(wx.HORIZONTAL)
        local_sizer.Add(self.txt_local_model, 1, wx.EXPAND | wx.RIGHT, 5)
        local_sizer.Add(btn_browse_model, 0, wx.RIGHT, 5)
        local_sizer.Add(btn_clear_model, 0)
        sizer.Add(lbl_local, 0, wx.ALL, 5)
        sizer.Add(local_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        lbl_lang = wx.StaticText(page, label=self.i18n.get("lbl_transcription_language"))
        self.cb_trans_lang = wx.Choice(page, choices=[name or self.i18n.get("lang_auto_detect") for _, name in TRANSCRIPTION_LANGUAGES])
        sizer.Add(lbl_lang, 0, wx.ALL, 5)
        sizer.Add(self.cb_trans_lang, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        lbl_device = wx.StaticText(page, label=self.i18n.get("lbl_device"))
        self.cb_device = wx.Choice(page, choices=["cpu", "cuda"])
        sizer.Add(lbl_device, 0, wx.ALL, 5)
        sizer.Add(self.cb_device, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        self.chk_memory = wx.CheckBox(page, label=self.i18n.get("lbl_keep_in_memory"))
        sizer.Add(self.chk_memory, 0, wx.ALL, 5)

        self.chk_local = wx.CheckBox(page, label=self.i18n.get("chk_use_local_model"))
        self.chk_local.SetToolTip(self.i18n.get("acc_chk_use_local_model"))
        sizer.Add(self.chk_local, 0, wx.ALL, 5)

        page.SetSizer(sizer)

    def update_model_state(self):
        """إظهار هل النموذج المختار موجود على الجهاز أم سيتم تحميله"""
        model = self.cb_model.GetStringSelection()
        if self.txt_local_model.GetValue():
            text = self.i18n.get("lbl_model_custom_path")
        elif model and ModelManager.find_local_model(model):
            text = self.i18n.get("lbl_model_installed")
        else:
            text = self.i18n.get("lbl_model_not_installed")
        self.lbl_model_state.SetValue(text)
        self.page_engine.Layout()

    def on_browse_model(self, event):
        dlg = wx.DirDialog(self, message=self.i18n.get("dialog_select_model_dir"), style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if ModelManager.is_valid_model_dir(path):
                self.txt_local_model.SetValue(path)
                self.update_model_state()
            else:
                wx.MessageBox(self.i18n.get("msg_invalid_model_dir"), self.i18n.get("dialog_error_title"), wx.ICON_ERROR)
        dlg.Destroy()

    def on_clear_model(self, event):
        self.txt_local_model.SetValue("")
        self.update_model_state()

    def on_auto_suggest(self, event):
        ram_gb = psutil.virtual_memory().total / (1024**3)
        if ram_gb >= 12:
            suggested_model = "large-v3"
        elif ram_gb >= 6:
            suggested_model = "deepdml/faster-whisper-large-v3-turbo-ct2"
        elif ram_gb >= 4:
            suggested_model = "medium"
        else:
            suggested_model = "small"

        self.cb_model.SetStringSelection(suggested_model)
        self.update_model_state()
        msg = self.i18n.get("msg_ram_scan_result", ram=f"{ram_gb:.1f}", model=suggested_model)
        wx.MessageBox(msg, self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION)

    # ------------------------------------------------------------------ الإعدادات المتقدمة
    def setup_advanced_page(self):
        page = self.page_advanced
        page.SetScrollRate(0, 10)
        sizer = wx.BoxSizer(wx.VERTICAL)

        # حقل للقراءة فقط بدلاً من نص ثابت: يصل إليه Tab فيُقرأ، بينما النص الثابت لا يُنطق
        self.lbl_advanced_note = readonly_note(page, self.i18n.get("lbl_advanced_note"))
        sizer.Add(self.lbl_advanced_note, 0, wx.EXPAND | wx.ALL, 5)

        grid = wx.FlexGridSizer(0, 2, 8, 10)
        grid.AddGrowableCol(1, 1)

        def add_row(label_key, make_ctrl):
            # العنوان يُنشأ قبل الحقل حتى يقرأه قارئ الشاشة كاسم له
            grid.Add(wx.StaticText(page, label=self.i18n.get(label_key)), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = make_ctrl()
            grid.Add(ctrl, 1, wx.EXPAND)
            return ctrl

        self.cb_compute = add_row("lbl_compute_type", lambda: wx.Choice(page, choices=COMPUTE_TYPES))
        self.spin_beam = add_row("lbl_beam_size", lambda: wx.SpinCtrl(page, min=1, max=10))
        # قوائم اختيار بدلاً من SpinCtrlDouble: الأخير مكوّن من عدة أجزاء فلا يقرأ قارئ الشاشة اسمه
        self.spin_temp = add_row("lbl_temperature", lambda: FloatChoice(page, TEMPERATURE_VALUES))
        cpu_count = os.cpu_count() or 8
        self.spin_threads = add_row("lbl_threads", lambda: wx.SpinCtrl(page, min=0, max=cpu_count))
        self.spin_no_speech = add_row("lbl_no_speech_threshold", lambda: FloatChoice(page, NO_SPEECH_VALUES))
        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 5)

        # فلتر الصمت يعمل في المستويين (المبسط والمتقدم)، لذلك لا يتم تعطيله مع باقي الإعدادات المتقدمة.
        # التنبيه المهم مكتوب في اسم الخانة نفسه، لأن التلميحات لا تُنطق عند التنقل بلوحة المفاتيح
        self.chk_vad = wx.CheckBox(page, label=self.i18n.get("chk_vad_filter"))
        self.chk_vad.SetToolTip(self.i18n.get("tip_vad_filter"))
        self.chk_word_ts = wx.CheckBox(page, label=self.i18n.get("chk_word_timestamps"))
        sizer.Add(self.chk_vad, 0, wx.ALL, 5)
        sizer.Add(self.chk_word_ts, 0, wx.ALL, 5)

        sizer.Add(wx.StaticText(page, label=self.i18n.get("lbl_initial_prompt")), 0, wx.ALL, 5)
        self.txt_prompt = wx.TextCtrl(page, style=wx.TE_MULTILINE, size=(-1, 70))
        sizer.Add(self.txt_prompt, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        page.SetSizer(sizer)

    def on_mode_changed(self, event=None):
        advanced = self.cb_mode.GetSelection() == 1
        for ctrl in (self.cb_compute, self.spin_beam, self.spin_temp, self.spin_threads, self.spin_no_speech,
                     self.chk_word_ts, self.txt_prompt):
            ctrl.Enable(advanced)
        self.lbl_advanced_note.Show(not advanced)
        self.page_advanced.Layout()

    # ------------------------------------------------------------------ الحفظ
    def setup_output_page(self):
        page = self.page_output
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl_dir = wx.StaticText(page, label=self.i18n.get("lbl_output_directory"))
        self.txt_dir = wx.TextCtrl(page)
        self.txt_dir.SetHint(self.i18n.get("hint_output_same_folder"))
        btn_browse = wx.Button(page, label=self.i18n.get("btn_browse"))
        btn_browse.Bind(wx.EVT_BUTTON, self.on_browse_output)

        dir_sizer = wx.BoxSizer(wx.HORIZONTAL)
        dir_sizer.Add(self.txt_dir, 1, wx.EXPAND | wx.RIGHT, 5)
        dir_sizer.Add(btn_browse, 0)

        sizer.Add(lbl_dir, 0, wx.ALL, 5)
        sizer.Add(dir_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        lbl_fmt = wx.StaticText(page, label=self.i18n.get("lbl_default_format"))
        self.cb_fmt = wx.Choice(page, choices=EXPORT_FORMATS)
        sizer.Add(lbl_fmt, 0, wx.ALL, 5)
        sizer.Add(self.cb_fmt, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        sizer.Add(wx.StaticText(page, label=self.i18n.get("lbl_export_formats")), 0, wx.ALL, 5)
        fmt_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_formats = {}
        for fmt in EXPORT_FORMATS:
            # الاسم الكامل (وليس "SRT" فقط) لأن قارئ الشاشة لا يربط الخانة بالعنوان الذي فوقها
            chk = wx.CheckBox(page, label=self.i18n.get("chk_export_format", fmt=fmt.upper()))
            self.chk_formats[fmt] = chk
            fmt_sizer.Add(chk, 0, wx.RIGHT, 10)
        sizer.Add(fmt_sizer, 0, wx.LEFT | wx.RIGHT, 5)

        self.chk_auto_save = wx.CheckBox(page, label=self.i18n.get("chk_auto_save"))
        self.chk_open_folder = wx.CheckBox(page, label=self.i18n.get("chk_open_folder"))
        sizer.Add(self.chk_auto_save, 0, wx.ALL, 5)
        sizer.Add(self.chk_open_folder, 0, wx.ALL, 5)

        page.SetSizer(sizer)

    # ------------------------------------------------------------------ التصحيح
    def setup_correction_page(self):
        page = self.page_correction
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.chk_enable_corr = wx.CheckBox(page, label=self.i18n.get("chk_enable_correction"))
        sizer.Add(self.chk_enable_corr, 0, wx.ALL, 5)

        sizer.Add(wx.StaticText(page, label=self.i18n.get("lbl_correction_level")), 0, wx.ALL, 5)
        self.cb_corr_level = wx.Choice(page, choices=[self.i18n.get(f"correction_{lvl}") for lvl in CORRECTION_LEVELS])
        sizer.Add(self.cb_corr_level, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        self.chk_hotwords = wx.CheckBox(page, label=self.i18n.get("chk_use_hotwords"))
        sizer.Add(self.chk_hotwords, 0, wx.ALL, 5)

        btn_dict = wx.Button(page, label=self.i18n.get("btn_custom_dictionary"))
        btn_dict.Bind(wx.EVT_BUTTON, self.on_open_dict)
        sizer.Add(btn_dict, 0, wx.ALL, 5)

        self.chk_enable_corr.Bind(wx.EVT_CHECKBOX, lambda e: self.on_correction_toggled())
        page.SetSizer(sizer)

    def on_correction_toggled(self):
        enabled = self.chk_enable_corr.GetValue()
        self.cb_corr_level.Enable(enabled)
        self.chk_hotwords.Enable(enabled)

    def on_open_dict(self, event):
        from gui.custom_dict_dialog import CustomDictDialog
        dlg = CustomDictDialog(self, self.i18n, self.settings)
        dlg.ShowModal()
        dlg.Destroy()

    # ------------------------------------------------------------------ المظهر
    def setup_appearance_page(self):
        page = self.page_appearance
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl_lang = wx.StaticText(page, label=self.i18n.get("lbl_language"))
        self.cb_lang = wx.Choice(page, choices=[self.i18n.get("lang_arabic"), self.i18n.get("lang_english")])
        sizer.Add(lbl_lang, 0, wx.ALL, 5)
        sizer.Add(self.cb_lang, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        lbl_theme = wx.StaticText(page, label=self.i18n.get("lbl_theme"))
        self.cb_theme = wx.Choice(page, choices=[self.i18n.get("theme_light"), self.i18n.get("theme_dark")])
        sizer.Add(lbl_theme, 0, wx.ALL, 5)
        sizer.Add(self.cb_theme, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        lbl_font = wx.StaticText(page, label=self.i18n.get("lbl_font_size"))
        self.spin_font = wx.SpinCtrl(page, min=8, max=24)
        sizer.Add(lbl_font, 0, wx.ALL, 5)
        sizer.Add(self.spin_font, 0, wx.LEFT | wx.RIGHT, 5)

        page.SetSizer(sizer)

    def on_browse_output(self, event):
        dlg = wx.DirDialog(self, message=self.i18n.get("dialog_select_folder"))
        if dlg.ShowModal() == wx.ID_OK:
            self.txt_dir.SetValue(dlg.GetPath())
        dlg.Destroy()

    # ------------------------------------------------------------------ تحميل وحفظ القيم
    def load_settings(self):
        s = self.settings
        self.cb_mode.SetSelection(0 if s.get("user_mode", "beginner") == "beginner" else 1)

        model_val = s.get("model_size", "large-v3")
        if model_val not in self.cb_model.GetItems():
            self.cb_model.Append(model_val)
        self.cb_model.SetStringSelection(model_val)

        local_path = s.get("local_model_path", "") or ""
        self.txt_local_model.SetValue(local_path if ModelManager.is_valid_model_dir(local_path) else "")

        trans_lang = "auto" if s.get("auto_detect_language", False) else s.get("transcription_language", "ar")
        codes = [code for code, _ in TRANSCRIPTION_LANGUAGES]
        self.cb_trans_lang.SetSelection(codes.index(trans_lang) if trans_lang in codes else 1)

        self.cb_device.SetStringSelection(s.get("device", "cpu"))
        self.chk_memory.SetValue(s.get("keep_in_memory", True))
        self.chk_local.SetValue(s.get("use_local_model", False))

        compute = s.get("compute_type", "int8")
        self.cb_compute.SetStringSelection(compute if compute in COMPUTE_TYPES else "int8")
        self.spin_beam.SetValue(int(s.get("beam_size", 5)))
        self.spin_temp.SetValue(float(s.get("temperature", 0.0)))
        self.spin_threads.SetValue(int(s.get("threads", 0)))
        self.spin_no_speech.SetValue(float(s.get("no_speech_threshold", 0.6)))
        self.chk_vad.SetValue(s.get("vad_filter", False))
        self.chk_word_ts.SetValue(s.get("word_timestamps", True))
        self.txt_prompt.SetValue(s.get("initial_prompt", "") or "")

        self.txt_dir.SetValue(s.get("output_directory", ""))
        self.cb_fmt.SetStringSelection(s.get("default_export_format", "srt"))
        enabled_formats = s.get("export_formats", EXPORT_FORMATS) or EXPORT_FORMATS
        for fmt, chk in self.chk_formats.items():
            chk.SetValue(fmt in enabled_formats)
        self.chk_auto_save.SetValue(s.get("auto_save", True))
        self.chk_open_folder.SetValue(s.get("open_folder_after_save", False))

        self.chk_enable_corr.SetValue(s.get("enable_correction", True))
        level = s.get("correction_level", "medium")
        self.cb_corr_level.SetSelection(CORRECTION_LEVELS.index(level) if level in CORRECTION_LEVELS else 1)
        self.chk_hotwords.SetValue(s.get("use_hotwords", True))

        self.cb_lang.SetSelection(0 if s.get("language", "ar") == "ar" else 1)
        self.cb_theme.SetSelection(0 if s.get("theme", "light") == "light" else 1)
        self.spin_font.SetValue(int(s.get("font_size", 10)))

        self.on_mode_changed()
        self.on_correction_toggled()
        self.update_model_state()

    def _cuda_available(self):
        try:
            import ctranslate2
            return ctranslate2.get_cuda_device_count() > 0
        except Exception:
            return False

    def on_save(self, event):
        device = self.cb_device.GetStringSelection() or "cpu"
        if device == "cuda" and not self._cuda_available():
            wx.MessageBox(self.i18n.get("msg_cuda_not_available"), self.i18n.get("dialog_warning_title"), wx.ICON_WARNING)
            device = "cpu"

        output_dir = self.txt_dir.GetValue().strip()
        if output_dir and not os.path.isdir(output_dir):
            wx.MessageBox(self.i18n.get("msg_output_dir_invalid"), self.i18n.get("dialog_error_title"), wx.ICON_ERROR)
            self.notebook.SetSelection(2)
            self.txt_dir.SetFocus()
            return

        export_formats = [fmt for fmt, chk in self.chk_formats.items() if chk.GetValue()] or ["srt"]
        default_fmt = self.cb_fmt.GetStringSelection() or "srt"
        if default_fmt not in export_formats:
            export_formats.append(default_fmt)

        trans_lang = TRANSCRIPTION_LANGUAGES[max(self.cb_trans_lang.GetSelection(), 0)][0]

        old_lang = self.settings.get("language", "ar")
        new_lang = "ar" if self.cb_lang.GetSelection() == 0 else "en"
        old_theme = self.settings.get("theme", "light")
        new_theme = "light" if self.cb_theme.GetSelection() == 0 else "dark"
        old_font = self.settings.get("font_size", 10)
        new_font = self.spin_font.GetValue()

        self.settings.update({
            "user_mode": "beginner" if self.cb_mode.GetSelection() == 0 else "advanced",
            "model_size": self.cb_model.GetStringSelection() or "large-v3",
            "local_model_path": self.txt_local_model.GetValue(),
            "transcription_language": "ar" if trans_lang == "auto" else trans_lang,
            "auto_detect_language": trans_lang == "auto",
            "device": device,
            "keep_in_memory": self.chk_memory.GetValue(),
            "use_local_model": self.chk_local.GetValue(),
            "compute_type": self.cb_compute.GetStringSelection() or "int8",
            "beam_size": self.spin_beam.GetValue(),
            "temperature": round(self.spin_temp.GetValue(), 2),
            "threads": self.spin_threads.GetValue(),
            "no_speech_threshold": round(self.spin_no_speech.GetValue(), 2),
            "vad_filter": self.chk_vad.GetValue(),
            "word_timestamps": self.chk_word_ts.GetValue(),
            "initial_prompt": self.txt_prompt.GetValue().strip(),
            "output_directory": output_dir,
            "default_export_format": default_fmt,
            "export_formats": export_formats,
            "auto_save": self.chk_auto_save.GetValue(),
            "open_folder_after_save": self.chk_open_folder.GetValue(),
            "enable_correction": self.chk_enable_corr.GetValue(),
            "correction_level": CORRECTION_LEVELS[max(self.cb_corr_level.GetSelection(), 0)],
            "use_hotwords": self.chk_hotwords.GetValue(),
            "language": new_lang,
            "theme": new_theme,
            "font_size": new_font,
        })

        if old_theme != new_theme and hasattr(self.parent_window, 'apply_theme'): self.parent_window.apply_theme(new_theme)
        if old_font != new_font and hasattr(self.parent_window, 'apply_font_size'): self.parent_window.apply_font_size(new_font)
        if old_lang != new_lang: self.i18n.set_language(new_lang)

        wx.MessageBox(self.i18n.get("msg_settings_saved"), self.i18n.get("dialog_success_title"), wx.ICON_INFORMATION)
        self.EndModal(wx.ID_OK)

    def on_reset(self, event):
        dlg = wx.MessageDialog(self, self.i18n.get("msg_reset_confirm"), self.i18n.get("dialog_warning_title"), wx.YES_NO | wx.ICON_WARNING)
        if dlg.ShowModal() == wx.ID_YES:
            # القاموس المخصص من بيانات المستخدم وليس إعداداً، فلا نمسحه مع الاستعادة
            custom_dict = self.settings.get("custom_dictionary", {})
            self.settings.reset_to_defaults()
            self.settings.set("custom_dictionary", custom_dict)
            self.load_settings()
            # تطبيق المظهر واللغة الافتراضيين فوراً حتى تتطابق الواجهة مع الإعدادات المحفوظة
            if hasattr(self.parent_window, 'apply_theme'): self.parent_window.apply_theme(self.settings.get("theme", "light"))
            if hasattr(self.parent_window, 'apply_font_size'): self.parent_window.apply_font_size(self.settings.get("font_size", 10))
            self.i18n.set_language(self.settings.get("language", "ar"))
        dlg.Destroy()

    def on_cancel(self, event):
        self.EndModal(wx.ID_CANCEL)
