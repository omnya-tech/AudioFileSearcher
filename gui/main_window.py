import wx
import pygame
from core.i18n import LocalizationManager
from core.settings import SettingsManager
from core.audio_processor import EVT_RESULT
from core.logger import log_error
from gui.audio_player import AudioPlayerPanel
from gui.search_panel import CrossFileSearchPanel
from gui import icons, widgets

from gui.main.common import AudioDropTarget
from gui.main.appearance import AppearanceMixin
from gui.main.menus import MenusMixin
from gui.main.files import FilesMixin
from gui.main.transcription import TranscriptionMixin
from gui.main.results import ResultsMixin
from gui.main.learning import LearningMixin


class MainWindow(AppearanceMixin, MenusMixin, FilesMixin, TranscriptionMixin, ResultsMixin, LearningMixin, wx.Frame):
    """
    النافذة الرئيسية. كل جانب من سلوكها في ملف مستقل داخل gui/main/:
    - appearance.py: المظهر واللغة واتجاه الواجهة وحجم الخط والأيقونات، وعنوان النافذة ومقاسها ومكانها
    - menus.py: القوائم واختصاراتها، وفتح النوافذ الفرعية (الإعدادات، النماذج، القاموس، السجل...)
    - files.py: اختيار الملفات والمجلدات، السحب والإفلات، فتح ملفات الترجمة، والحفظ والتصدير
    - transcription.py: تشغيل التفريغ، وضع المجلد، النتائج أول بأول، الحفظ للاسترجاع والاستكمال، والإلغاء
    - results.py: قائمة النتائج: العرض والبحث فيها، التعديل والدمج والتقسيم، وتشغيل الجمل
    - learning.py: التعلم من تعديلات المستخدم، وتطبيق القاموس على النتائج الحالية
    هذا الملف: بناء الواجهة، وربط الأجزاء ببعضها، واستقبال الملفات من نسخة ثانية، والإغلاق.
    """

    def __init__(self, i18n: LocalizationManager, settings: SettingsManager, parent=None):
        title = f"{i18n.get('app_name')} - {i18n.get('app_version')}"
        super().__init__(parent, title=title, size=(950, 700))
        self.i18n = i18n
        i18n.apply_direction(self)
        widgets.fit_to_screen(self)
        self.settings = settings
        self.audio_path = None
        self.all_segments = []
        self.displayed_indices = []
        self.unsaved_edits = False
        self.current_percent = None
        self.is_batch_mode = False
        self.batch_queue = []
        self.batch_current_idx = 0
        self.batch_failed = 0
        self.download_dialog = None
        self.processing_dialog = None
        self.transcription_thread = None

        try:
            pygame.mixer.init()
        except Exception as e:
            # لا توجد كارت صوت أو جهاز تشغيل: البرنامج يعمل، والتشغيل فقط هو المعطل
            log_error(f"Audio device init failed: {e}")
        self.i18n.add_observer(self.refresh_ui_texts)
        icons.set_theme(self.settings.get("theme", "light"))
        icons.set_window_icon(self)

        self.setup_menu()
        self.setup_ui()
        self.setup_accessibility()
        self.refresh_dictionary_choice()

        self.apply_theme(self.settings.get("theme", "light"))
        self.apply_font_size(self.settings.get("font_size", 10))

        EVT_RESULT(self, self.on_transcription_update)

        self.Center()
        self.restore_window_geometry()
        wx.CallAfter(self.update_title_with_tab)

    def setup_ui(self):
        self.panel = wx.Panel(self)
        self.panel.SetDropTarget(AudioDropTarget(self))
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.notebook = wx.Notebook(self.panel)
        self.notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_changed)

        self.transcription_panel = wx.Panel(self.notebook)
        self.transcription_panel.SetDropTarget(AudioDropTarget(self))
        trans_sizer = wx.BoxSizer(wx.VERTICAL)

        file_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_select = wx.Button(self.transcription_panel, label=self.i18n.get("btn_select_audio"))
        self.btn_select_folder = wx.Button(self.transcription_panel, label=self.i18n.get("btn_select_folder"))
        # قارئ الشاشة يأخذ اسم الحقل من النص الثابت الذي يسبقه مباشرة عند الإنشاء،
        # لذلك يُنشأ كل عنوان قبل الحقل التابع له مباشرة
        self.lbl_file_path = wx.StaticText(self.transcription_panel, label=self.i18n.get("lbl_selected_file"))
        self.txt_file_path = wx.TextCtrl(self.transcription_panel, style=wx.TE_READONLY)

        file_sizer.Add(self.btn_select, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        file_sizer.Add(self.btn_select_folder, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        file_sizer.Add(self.lbl_file_path, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        file_sizer.Add(self.txt_file_path, 1, wx.ALL | wx.EXPAND, 5)
        trans_sizer.Add(file_sizer, 0, wx.EXPAND | wx.ALL, 5)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_process = wx.Button(self.transcription_panel, label=self.i18n.get("btn_process"))
        self.btn_export = wx.Button(self.transcription_panel, label=self.i18n.get("btn_export"))
        self.btn_process.Disable()
        self.btn_export.Disable()
        # قاموس المجال المستخدم في التفريغ (قرآن، محاضرات...): يُختار قبل البدء
        self.lbl_dictionary = wx.StaticText(self.transcription_panel, label=self.i18n.get("lbl_dictionary"))
        self.cb_dictionary = wx.Choice(self.transcription_panel)
        self.cb_dictionary.Bind(wx.EVT_CHOICE, self.on_dictionary_chosen)
        btn_sizer.Add(self.btn_process, 0, wx.ALL, 5)
        btn_sizer.Add(self.btn_export, 0, wx.ALL, 5)
        btn_sizer.Add(self.lbl_dictionary, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 20)
        btn_sizer.Add(self.cb_dictionary, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        trans_sizer.Add(btn_sizer, 0, wx.CENTER | wx.ALL, 5)

        filter_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_filter = wx.StaticText(self.transcription_panel, label=self.i18n.get("lbl_search"))
        self.txt_filter = wx.TextCtrl(self.transcription_panel, style=wx.TE_PROCESS_ENTER)
        filter_sizer.Add(self.lbl_filter, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        filter_sizer.Add(self.txt_filter, 1, wx.ALL | wx.EXPAND, 5)
        trans_sizer.Add(filter_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.lbl_results = wx.StaticText(self.transcription_panel, label=self.i18n.get("lbl_results"))
        self.result_list = self._create_result_list()
        trans_sizer.Add(self.lbl_results, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        trans_sizer.Add(self.result_list, 1, wx.EXPAND | wx.ALL, 10)

        self.trans_sizer = trans_sizer
        self.transcription_panel.SetSizer(trans_sizer)

        self.search_panel = CrossFileSearchPanel(self.notebook, self.i18n, play_callback=self.play_audio_from_search)

        self.notebook.AddPage(self.transcription_panel, self.i18n.get("tab_transcription"))
        self.notebook.AddPage(self.search_panel, self.i18n.get("tab_global_search"))
        self.i18n.fix_notebook(self.notebook)

        main_sizer.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 5)

        self.audio_player = AudioPlayerPanel(self.panel, self.i18n,
                                             on_finished=lambda: self.status_bar.SetStatusText(self.i18n.get("status_ready")))
        self.audio_player.Hide()
        main_sizer.Add(self.audio_player, 0, wx.EXPAND | wx.ALL, 5)

        self.status_bar = self.CreateStatusBar()
        self.status_bar.SetStatusText(self.i18n.get("status_ready"))

        self.panel.SetSizer(main_sizer)

        self.btn_select.Bind(wx.EVT_BUTTON, self.on_select_audio)
        self.btn_select_folder.Bind(wx.EVT_BUTTON, self.on_select_folder)
        self.btn_process.Bind(wx.EVT_BUTTON, self.on_process)
        self.btn_export.Bind(wx.EVT_BUTTON, self.on_export_srt)
        self.txt_filter.Bind(wx.EVT_TEXT, self.on_filter_results)
        # الإفلات يعمل فوق القائمة وحقل الملف أيضاً، لا فقط فوق الخلفية
        self.txt_file_path.SetDropTarget(AudioDropTarget(self))
        self.Bind(wx.EVT_CLOSE, self.on_exit)

        self.setup_button_hover_effects()

    def setup_accessibility(self):
        # تنبيه: لا نستخدم SetAcceleratorTable هنا، لأنه في ويندوز يستبدل اختصارات القوائم كلها فتتعطل.
        # كل اختصار يجب أن يكون عنصراً في القوائم (مع \t في اسمه) ليعمل ويظهر للمستخدم.
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_press)
        self.btn_select.SetFocus()

    def start_instance_inbox(self):
        """استقبال الملفات التي تُفتح من نسخة ثانية للبرنامج (انظر core/single_instance.py)"""
        self._inbox_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_inbox_timer, self._inbox_timer)
        self._inbox_timer.Start(700)

    def _on_inbox_timer(self, event):
        from core import single_instance
        for paths in single_instance.take_requests():
            self.bring_to_front()
            if paths:
                if self.transcription_thread_running():
                    wx.MessageBox(self.i18n.get("msg_busy_try_later"), self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION)
                else:
                    self.on_files_dropped(paths)

    def bring_to_front(self):
        if self.IsIconized():
            self.Iconize(False)
        self.Show()
        self.Raise()
        # ويندوز قد يمنع برنامجاً من أخذ التركيز بنفسه، فنومض زره في شريط المهام على الأقل
        self.RequestUserAttention()

    def on_exit(self, event):
        if not self.confirm_discard_edits():
            if isinstance(event, wx.CloseEvent) and event.CanVeto(): event.Veto()
            return
        if getattr(self, 'download_dialog', None) and self.download_dialog.is_downloading:
            dlg = wx.MessageDialog(self, self.i18n.get("dl_msg_confirm_hide"), self.i18n.get("dialog_warning_title"), wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
            res = dlg.ShowModal()
            dlg.Destroy()
            if res != wx.ID_YES:
                if isinstance(event, wx.CloseEvent) and event.CanVeto(): event.Veto()
                return
            if getattr(self.download_dialog, 'download_thread', None): self.download_dialog.download_thread.abort()

        if self.transcription_thread:
            # حفظ آخر ما تم تفريغه ليُعرض استكماله عند الفتح القادم
            self._save_recovery(force=True)
            self.transcription_thread.abort()
        if getattr(self, "_inbox_timer", None):
            self._inbox_timer.Stop()
        self.i18n.remove_observer(self.refresh_ui_texts)
        self.save_window_geometry()
        self.audio_player.cleanup()
        try:
            if pygame.mixer.get_init(): pygame.mixer.quit()
        except Exception:
            pass
        self.Destroy()
