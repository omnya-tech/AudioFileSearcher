"""اختيار الملفات والمجلدات، السحب والإفلات، فتح ملفات الترجمة، والحفظ والتصدير"""
import wx
import os
import subprocess
import platform
from core.cross_file_search import AUDIO_EXTENSIONS, parse_subtitles, find_audio_for
from core.time_utils import format_range
from core.logger import log_error
from core import exporters

from gui.main.common import EXPORT_FORMATS, EXPORT_FORMAT_KEYS, list_audio_files, is_audio_file


class FilesMixin:
    """جزء من النافذة الرئيسية (MainWindow): اختيار الملفات والمجلدات، السحب والإفلات، فتح ملفات الترجمة، والحفظ والتصدير"""

    def on_files_dropped(self, filenames):
        if not filenames or self.transcription_thread_running(): return
        # ملف ترجمة واحد: يُفتح للمراجعة
        if len(filenames) == 1 and filenames[0].lower().endswith(('.srt', '.vtt')) and os.path.isfile(filenames[0]):
            self.load_srt_file(filenames[0])
            return
        # غير ذلك: كل الملفات الصوتية المُفلتة (ومحتوى أي مجلد مُفلت) تُفرّغ
        audio = []
        for path in filenames:
            if os.path.isdir(path):
                audio += list_audio_files(path)
            elif os.path.isfile(path) and is_audio_file(path):
                audio.append(path)
        if not audio:
            wx.MessageBox(self.i18n.get("msg_folder_no_audio"), self.i18n.get("dialog_error_title"), wx.ICON_WARNING)
        elif len(audio) == 1:
            self.set_single_file(audio[0])
            self.on_process(None)
        else:
            label = filenames[0] if len(filenames) == 1 else self.i18n.get("lbl_dropped_files", count=self.i18n.plural("n_audio_files", len(audio)))
            self.start_batch(audio, label, auto_start=True)

    def set_single_file(self, path):
        self.is_batch_mode = False
        self.batch_queue = []
        self.audio_path = path
        self.txt_file_path.SetValue(path)
        self.btn_process.Enable()

    def start_folder(self, folder_path, auto_start=False):
        files = list_audio_files(folder_path)
        if not files:
            wx.MessageBox(self.i18n.get("msg_folder_no_audio"), self.i18n.get("dialog_error_title"), wx.ICON_WARNING)
            return
        self.start_batch(files, folder_path, auto_start)

    def start_batch(self, files, label, auto_start=False):
        self.batch_queue = files
        self.is_batch_mode = True
        self.audio_path = os.path.dirname(files[0])
        self.txt_file_path.SetValue(label)
        self.btn_process.Enable()
        if auto_start:
            self.on_process(None)
        else:
            self.txt_file_path.SetFocus()

    def on_open_srt(self, event):
        wildcard = f"{self.i18n.get('wc_subtitles')} (*.srt;*.vtt)|*.srt;*.vtt|{self.i18n.get('wc_all')} (*.*)|*.*"
        dlg = wx.FileDialog(self, message=self.i18n.get("dialog_open_srt"), wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.load_srt_file(dlg.GetPath())
        dlg.Destroy()

    def load_srt_file(self, srt_path):
        if not self.confirm_discard_edits():
            return
        try:
            parsed = parse_subtitles(srt_path)
        except Exception as e:
            log_error(f"Failed to open subtitles {srt_path}: {e}")
            self.show_error(e)
            return
        if not parsed:
            wx.MessageBox(self.i18n.get("msg_srt_empty"), self.i18n.get("dialog_warning_title"), wx.ICON_WARNING)
            return

        self.all_segments = [(format_range(s, e), text, s, e, []) for s, e, text in parsed]
        self.txt_filter.ChangeValue("")
        self.update_list()
        self.txt_file_path.SetValue(srt_path)
        self.btn_export.Enable()
        self.mi_export.Enable(True)

        self.is_batch_mode = False
        self.batch_queue = []
        self.audio_path = find_audio_for(srt_path)
        self.btn_process.Enable(bool(self.audio_path))
        self.status_bar.SetStatusText(self.i18n.get("status_ready"))

    def on_select_audio(self, event):
        exts = ";".join(f"*{e}" for e in AUDIO_EXTENSIONS)
        wildcard = f"{self.i18n.get('wc_audio')} ({exts})|{exts}|{self.i18n.get('wc_all')} (*.*)|*.*"
        dlg = wx.FileDialog(self, message=self.i18n.get("dialog_open_audio"), wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.set_single_file(dlg.GetPath())
            self.txt_file_path.SetFocus()
        dlg.Destroy()

    def on_select_folder(self, event):
        dlg = wx.DirDialog(self, message=self.i18n.get("dialog_select_folder"), style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.start_folder(dlg.GetPath())
        dlg.Destroy()

    def on_export_srt(self, event):
        if not self.all_segments: return
        enabled = self.settings.get("export_formats", EXPORT_FORMATS) or EXPORT_FORMATS
        formats = [f for f in EXPORT_FORMATS if f in enabled]
        default_format = self.settings.get("default_export_format", "srt")
        # الصيغة الافتراضية تظهر أولاً في مربع الحفظ
        if default_format in formats:
            formats.remove(default_format)
            formats.insert(0, default_format)
        wildcard = "|".join(f"{self.i18n.get(EXPORT_FORMAT_KEYS[f])} (*.{f})|*.{f}" for f in formats)

        default_name = ""
        if self.audio_path and os.path.isfile(self.audio_path):
            default_name = os.path.splitext(os.path.basename(self.audio_path))[0] + "." + formats[0]

        dlg = wx.FileDialog(self, message=self.i18n.get("dialog_save_srt"), defaultFile=default_name,
                            wildcard=wildcard, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            ext = os.path.splitext(path)[1].lower().lstrip(".")
            if ext not in EXPORT_FORMATS:
                # المستخدم لم يكتب امتداداً: نعتمد الصيغة المختارة في مربع الحفظ
                ext = formats[dlg.GetFilterIndex()] if 0 <= dlg.GetFilterIndex() < len(formats) else "srt"
                path = f"{path}.{ext}"
            self.save_as(path, ext, show_msg=True)
        dlg.Destroy()

    def save_as(self, path, fmt, show_msg=True):
        try:
            exporters.export(path, fmt, self.all_segments, title=self.i18n.get("app_name"))
        except ImportError:
            wx.MessageBox(self.i18n.get("msg_docx_error"), self.i18n.get("dialog_error_title"), wx.ICON_ERROR)
            return False
        except Exception as e:
            log_error(f"Export to {path} failed: {e}")
            self.show_error(e)
            return False
        self.unsaved_edits = False
        if show_msg:
            wx.MessageBox(self.i18n.get("msg_export_success"), self.i18n.get("dialog_success_title"), wx.ICON_INFORMATION)
        return True

    def open_in_file_manager(self, path):
        try:
            if platform.system() == "Windows":
                if os.path.isfile(path): subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])
                else: os.startfile(os.path.normpath(path))
            elif platform.system() == "Darwin":
                subprocess.Popen(['open', '-R', path] if os.path.isfile(path) else ['open', path])
            else:
                subprocess.Popen(['xdg-open', os.path.dirname(path) if os.path.isfile(path) else path])
        except Exception as e:
            log_error(f"Failed to open file manager: {e}")

    def _output_dir_for(self, audio_path):
        output_dir = self.settings.get("output_directory", "")
        return output_dir if output_dir and os.path.isdir(output_dir) else os.path.dirname(audio_path)

    def auto_save_results(self):
        """حفظ النتائج تلقائياً. في وضع المجلد يتم الحفظ دائماً حتى لا تضيع نتائج الملفات السابقة"""
        if not (self.settings.get("auto_save", True) or self.is_batch_mode):
            return None
        default_format = self.settings.get("default_export_format", "srt")
        if default_format not in EXPORT_FORMATS: default_format = "srt"
        base_name = os.path.splitext(os.path.basename(self.audio_path))[0]
        save_path = os.path.join(self._output_dir_for(self.audio_path), f"{base_name}.{default_format}")
        return save_path if self.save_as(save_path, default_format, show_msg=False) else None
