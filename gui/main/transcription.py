"""تشغيل التفريغ، وضع المجلد، النتائج أول بأول، الحفظ للاسترجاع والاستكمال، والإلغاء"""
import wx
import os
from core.audio_processor import TranscriptionThread
from core.time_utils import format_clock
from core.logger import log_error
from core import recovery
from core.model_manager import ModelManager
import time
from gui.report_dialog import ReportDialog
from gui.processing_dialog import ProcessingDialog

from gui.main.common import RECOVERY_SAVE_INTERVAL


class TranscriptionMixin:
    """جزء من النافذة الرئيسية (MainWindow): تشغيل التفريغ، وضع المجلد، النتائج أول بأول، الحفظ للاسترجاع والاستكمال، والإلغاء"""

    def transcription_thread_running(self):
        return bool(self.transcription_thread and self.transcription_thread.is_alive() and not self.transcription_thread.aborted)

    def _set_controls_busy(self, busy):
        self.btn_select.Enable(not busy)
        self.btn_select_folder.Enable(not busy)
        self.btn_process.Enable(not busy and bool(self.audio_path or self.batch_queue))
        has_results = bool(self.all_segments)
        self.btn_export.Enable(not busy and has_results)
        self.mi_export.Enable(not busy and has_results)
        self.mi_select_audio.Enable(not busy)
        self.mi_select_folder.Enable(not busy)
        self.mi_open_srt.Enable(not busy)

    def _close_processing_dialog(self):
        if self.processing_dialog:
            self.processing_dialog.Destroy()
            self.processing_dialog = None

    def on_process(self, event):
        if not self.audio_path and not self.batch_queue: return
        if self.transcription_thread_running(): return
        if not self.confirm_discard_edits(): return
        if not self.ensure_model_ready(): return
        if not self.is_batch_mode and not os.path.isfile(self.audio_path or ""):
            wx.MessageBox(self.i18n.get("msg_audio_not_found"), self.i18n.get("dialog_error_title"), wx.ICON_ERROR)
            return

        resume_segments = None
        if not self.is_batch_mode:
            proceed, resume_segments = self._ask_resume(self.audio_path)
            if not proceed:
                return

        self._set_controls_busy(True)
        self.result_list.SetFocus()

        self._close_processing_dialog()
        self.processing_dialog = ProcessingDialog(self, self.i18n)
        self.processing_dialog.Show()

        if self.is_batch_mode:
            self.batch_current_idx = 0
            self.batch_failed = 0
            self.process_next_in_batch()
        else:
            self.current_percent = 0
            self.on_stop_audio(None)

            title_template = self.i18n.get("window_title_progress")
            if "{percent}" in title_template and "{app_title}" in title_template:
                self.SetTitle(title_template.format(percent=0, app_title=self.get_base_title()))
            else:
                self.SetTitle(self.get_base_title())

            filename = os.path.basename(self.audio_path)
            self.processing_dialog.update_progress(0, 100, self.i18n.get("status_init_engine"), filename)
            self._start_transcription(self.audio_path, resume_segments)

    def _start_transcription(self, path, resume_segments=None):
        self.all_segments = list(resume_segments or [])
        self.txt_filter.ChangeValue("")
        self.update_list()
        if self.processing_dialog:
            if self.all_segments:
                self.processing_dialog.set_text([seg[1] for seg in self.all_segments], self.all_segments[-1][3])
            else:
                self.processing_dialog.clear_text()
        self._last_recovery_save = time.time()
        self._audio_duration = 0
        self.transcription_thread = TranscriptionThread(self, path, self.i18n, resume_segments=resume_segments)

    def _ask_resume(self, path):
        """لو فيه تفريغ ناقص لهذا الملف: استكمال، أو بدء من جديد، أو تراجع. ترجع (نكمل؟، المقاطع السابقة)"""
        if getattr(self, "_resume_confirmed", False):
            self._resume_confirmed = False
            saved = recovery.load(path)
            return True, (saved["segments"] if saved else None)
        saved = recovery.load(path)
        if not saved:
            return True, None
        msg = self.i18n.get("msg_resume_found", file=os.path.basename(path),
                            reached=format_clock(saved["last_end"]), total=format_clock(saved.get("duration") or 0),
                            count=self.i18n.plural("n_lines", len(saved["segments"])))
        dlg = wx.MessageDialog(self, msg, self.i18n.get("dialog_info_title"), wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_QUESTION)
        dlg.SetYesNoCancelLabels(self.i18n.get("btn_resume"), self.i18n.get("btn_restart"), self.i18n.get("btn_cancel"))
        res = dlg.ShowModal()
        dlg.Destroy()
        if res == wx.ID_YES:
            return True, saved["segments"]
        if res == wx.ID_NO:
            recovery.delete(path)
            return True, None
        return False, None

    def _save_recovery(self, force=False):
        """حفظ ما تم تفريغه حتى الآن، كل بضع ثوانٍ أو فوراً عند الإلغاء أو الخطأ"""
        if not self.all_segments or not self.audio_path or not os.path.isfile(self.audio_path):
            return
        if force or time.time() - getattr(self, "_last_recovery_save", 0) >= RECOVERY_SAVE_INTERVAL:
            recovery.save(self.audio_path, self.all_segments, getattr(self, "_audio_duration", 0))
            self._last_recovery_save = time.time()

    def ensure_model_ready(self, at_startup=False):
        """
        لو لا يوجد نموذج على الجهاز: شرح الموقف وعرض فتح مدير النماذج بالنموذج المقترح محدداً،
        بدلاً من أن يبدأ التفريغ في تحميل 1.5 جيجابايت بصمت. ترجع True لو النموذج جاهز.
        """
        if ModelManager.has_usable_model(self.settings):
            return True
        recommended = ModelManager.recommend_model()
        key = "msg_no_model_startup" if at_startup else "msg_no_model_before_start"
        dlg = wx.MessageDialog(self, self.i18n.get(key, model=recommended), self.i18n.get("dialog_info_title"),
                               wx.YES_NO | wx.YES_DEFAULT | wx.ICON_INFORMATION)
        dlg.SetYesNoLabels(self.i18n.get("btn_open_model_manager"), self.i18n.get("btn_later"))
        if dlg.ShowModal() == wx.ID_YES:
            self.on_open_download_dialog(None, preselect=recommended)
        dlg.Destroy()
        return False

    def check_pending_recovery(self):
        """عند فتح البرنامج: لو فيه تفريغ لم يكتمل (إغلاق مفاجئ أو إلغاء) نعرض استكماله"""
        pending = recovery.list_pending()
        if not pending:
            return
        saved = pending[0]
        msg = self.i18n.get("msg_pending_on_startup", file=os.path.basename(saved["audio_path"]),
                            reached=format_clock(saved["last_end"]), total=format_clock(saved.get("duration") or 0))
        dlg = wx.MessageDialog(self, msg, self.i18n.get("dialog_info_title"), wx.YES_NO | wx.YES_DEFAULT | wx.ICON_QUESTION)
        dlg.SetYesNoLabels(self.i18n.get("btn_resume"), self.i18n.get("btn_later"))
        res = dlg.ShowModal()
        dlg.Destroy()
        if res == wx.ID_YES:
            self.set_single_file(saved["audio_path"])
            self._resume_confirmed = True
            self.on_process(None)

    def append_segment(self, seg):
        """إضافة جملة للقائمة فور تفريغها، دون تحريك التركيز"""
        seg_index = len(self.all_segments)
        self.all_segments.append(seg)
        query = self.txt_filter.GetValue().strip().lower()
        if not query or query in seg[1].lower():
            row = self.result_list.InsertItem(self.result_list.GetItemCount(), "")
            self.result_list.SetItemData(row, seg_index)
            self._fill_row(row, seg_index)
            self.displayed_indices.append(seg_index)

    def process_next_in_batch(self):
        if self.batch_current_idx < len(self.batch_queue):
            current_file = self.batch_queue[self.batch_current_idx]
            self.audio_path = current_file
            self.txt_file_path.SetValue(current_file)
            self.current_percent = 0
            self.on_stop_audio(None)

            filename = os.path.basename(current_file)
            self.status_bar.SetStatusText(f"[{self.batch_current_idx + 1}/{len(self.batch_queue)}] {filename}")

            title_template = self.i18n.get("window_title_batch_progress")
            if "{current}" in title_template and "{total}" in title_template:
                self.SetTitle(title_template.format(current=self.batch_current_idx + 1, total=len(self.batch_queue), percent=0, app_title=self.get_base_title()))
            else:
                self.SetTitle(self.get_base_title())

            if self.processing_dialog:
                self.processing_dialog.set_batch(self.batch_current_idx + 1, len(self.batch_queue))
                self.processing_dialog.update_progress(0, 100, self.i18n.get("status_init_engine"), filename)

            # في وضع المجلد يُستكمل أي ملف توقف سابقاً تلقائياً، بدون سؤال عن كل ملف
            saved = recovery.load(current_file)
            self._start_transcription(current_file, saved["segments"] if saved else None)
        else:
            total = len(self.batch_queue)
            succeeded = total - self.batch_failed
            out_dir = self._output_dir_for(self.batch_queue[0]) if self.batch_queue else None
            self.is_batch_mode = False
            self.batch_queue = []
            self.update_title_with_tab()
            self.status_bar.SetStatusText(self.i18n.get("status_ready"))
            self._set_controls_busy(False)
            self._close_processing_dialog()

            msg = self.i18n.get("msg_batch_done", count=self.i18n.plural("n_files", succeeded))
            if self.batch_failed:
                msg += "\n" + self.i18n.get("msg_batch_failed_count", count=self.i18n.plural("n_files", self.batch_failed))
            self._call_attention()
            wx.MessageBox(msg, self.i18n.get("dialog_success_title"), wx.ICON_INFORMATION)
            if out_dir and succeeded and self.settings.get("open_folder_after_save", False):
                self.open_in_file_manager(out_dir)

    def on_transcription_update(self, event):
        # تجاهل أي حدث قادم من عملية قديمة تم إلغاؤها
        if event.source is not None and event.source is not self.transcription_thread:
            return
        if self.transcription_thread is not None and self.transcription_thread.aborted:
            return

        status = event.status
        filename = os.path.basename(self.audio_path) if self.audio_path else ""

        if status == "loading" or status == "loading_local":
            status_txt = self.i18n.get("status_loading_model") if status == "loading" else self.i18n.get("status_loading_local_model")
            self.status_bar.SetStatusText(status_txt)
            if self.processing_dialog:
                self.processing_dialog.update_progress(0, 100, status_txt, filename)

        elif status == "transcribing":
            if self.processing_dialog:
                self.processing_dialog.update_progress(0, 100, self.i18n.get("status_extracting"), filename)

        elif status == "segment":
            self._audio_duration = event.data.get("duration") or 0
            seg = event.data["segment"]
            self.append_segment(seg)
            if self.processing_dialog:
                self.processing_dialog.add_segment(seg[1], seg[3], self._audio_duration)
            self._save_recovery()

        elif status == "progress":
            self.current_percent = event.data
            if self.processing_dialog:
                self.processing_dialog.update_progress(event.data, 100, self.i18n.get("status_extracting"), filename)

            if self.is_batch_mode:
                title_template = self.i18n.get("window_title_batch_progress")
                if "{current}" in title_template:
                    self.SetTitle(title_template.format(current=self.batch_current_idx + 1, total=len(self.batch_queue), percent=event.data, app_title=self.get_base_title()))
            else:
                title_template = self.i18n.get("window_title_progress")
                if "{percent}" in title_template:
                    self.SetTitle(title_template.format(percent=event.data, app_title=self.get_base_title()))

            status_template = self.i18n.get("status_transcribing")
            if "{percent}" in status_template:
                self.status_bar.SetStatusText(status_template.format(percent=event.data))

        elif status == "done":
            self.current_percent = None
            self.transcription_thread = None
            # اكتمل الملف: لا حاجة لملف الاسترجاع بعد الآن
            recovery.delete(self.audio_path)
            self.all_segments = event.data["results"]
            self.txt_filter.ChangeValue("")
            self.update_list()

            status_template = self.i18n.get("status_done")
            status_txt = status_template.format(time=event.data["time"]) if "{time}" in status_template else "Done"

            if self.processing_dialog:
                self.processing_dialog.update_progress(100, 100, status_txt, filename)

            if not self.all_segments:
                # لا يوجد كلام في الملف: لا داعي لحفظ ملف فارغ
                saved_path = None
            else:
                saved_path = self.auto_save_results()

            if self.is_batch_mode:
                self.batch_current_idx += 1
                self.process_next_in_batch()
                return

            self.update_title_with_tab()
            self.status_bar.SetStatusText(status_txt)
            self._set_controls_busy(False)
            self._close_processing_dialog()
            # التركيز على أول سطر من النتائج: بعد إغلاق التقرير يسمع المستخدم أول جملة مباشرة
            self.result_list.SetFocus()
            if self.result_list.GetItemCount():
                self.result_list.Focus(0)
                self.result_list.Select(0)
            # تنبيه صوتي بانتهاء التفريغ، مفيد لمن يعمل في نافذة أخرى أثناء الانتظار
            wx.Bell()
            self._call_attention()

            if saved_path and self.settings.get("open_folder_after_save", False):
                self.open_in_file_manager(saved_path)

            if not self.all_segments:
                wx.MessageBox(self.i18n.get("report_no_segments"), self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION)
            elif event.data.get("report"):
                report_dlg = ReportDialog(self, self.i18n, event.data["report"])
                report_dlg.ShowModal()
                report_dlg.Destroy()

        elif status == "error":
            self.current_percent = None
            self.transcription_thread = None
            # ما تم تفريغه قبل الخطأ يُحفظ ليمكن الاستكمال لاحقاً
            self._save_recovery(force=True)

            if self.is_batch_mode:
                log_error(f"Batch item failed {filename}: {event.data}")
                self.batch_failed += 1
                msg_template = self.i18n.get("status_batch_error")
                if "{file}" in msg_template:
                    self.status_bar.SetStatusText(msg_template.format(file=filename, error=event.data))
                self.batch_current_idx += 1
                self.process_next_in_batch()
            else:
                self.update_title_with_tab()
                msg_template = self.i18n.get("status_error")
                msg = msg_template.format(error=event.data) if "{error}" in msg_template else f"Error: {event.data}"
                self.status_bar.SetStatusText(msg)
                self._close_processing_dialog()
                self._set_controls_busy(False)
                wx.MessageBox(msg, self.i18n.get("dialog_error_title"), wx.ICON_ERROR)
                self.result_list.SetFocus()

    def pause_processing(self):
        if self.transcription_thread:
            self.transcription_thread.pause()
        self.status_bar.SetStatusText(self.i18n.get("status_processing_paused"))

    def resume_processing(self):
        if self.transcription_thread:
            self.transcription_thread.resume()
        self.status_bar.SetStatusText(self.i18n.get("status_processing_resumed"))

    def send_processing_to_background(self):
        """إخفاء نافذة المعالجة والتفريغ مستمر: التقدم في شريط الحالة وعنوان النافذة، وCtrl+I يعيدها"""
        if not self.processing_dialog:
            return
        self.processing_dialog.Hide()
        self.status_bar.SetStatusText(self.i18n.get("status_processing_background"))
        self.result_list.SetFocus()

    def show_processing_dialog(self):
        if self.processing_dialog:
            self.processing_dialog.Show()
            self.processing_dialog.Raise()
            self.processing_dialog.list_ctrl.SetFocus()

    def _call_attention(self):
        """لو كان المستخدم في برنامج آخر: وميض زر البرنامج في شريط المهام حتى يعود"""
        if not self.IsActive():
            self.RequestUserAttention()

    def cancel_processing(self):
        if self.transcription_thread:
            self.transcription_thread.abort()
        self.transcription_thread = None
        # حفظ ما تم تفريغه: يبقى ظاهراً وقابلاً للتصدير، ويمكن استكماله لاحقاً من نفس النقطة
        self._save_recovery(force=True)
        saved_partial = bool(self.all_segments)
        # في وضع المجلد يبقى الملف الحالي محدداً، فيمكن استكماله بزر "بدء التفريغ"
        self.is_batch_mode = False
        self.batch_queue = []
        self.current_percent = None
        self.update_title_with_tab()
        self._close_processing_dialog()
        self._set_controls_busy(False)
        if saved_partial:
            msg = self.i18n.get("msg_canceled_saved", reached=format_clock(self.all_segments[-1][3]))
            self.status_bar.SetStatusText(msg)
            wx.MessageBox(msg, self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION)
            self.result_list.SetFocus()
        else:
            self.status_bar.SetStatusText(self.i18n.get("status_canceled"))
