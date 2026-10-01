"""قائمة النتائج: العرض والبحث فيها، التعديل والدمج والتقسيم، وتشغيل الجمل"""
import wx
import os
from core.audio_processor import WEAK_WORD_THRESHOLD
from core.time_utils import format_range
from gui.edit_segment_dialog import EditSegmentDialog, ID_SPLIT
from core import segments as seg_ops
from gui import icons, widgets

from gui.main.common import AudioDropTarget


class ResultsMixin:
    """جزء من النافذة الرئيسية (MainWindow): قائمة النتائج: العرض والبحث فيها، التعديل والدمج والتقسيم، وتشغيل الجمل"""

    def _create_result_list(self):
        lst = wx.ListCtrl(self.transcription_panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        lst.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_play_segment)
        lst.Bind(wx.EVT_CONTEXT_MENU, self.on_list_context_menu)
        lst.SetDropTarget(AudioDropTarget(self))
        self.result_list = lst
        self._insert_result_columns()
        widgets.auto_fit_first_column(lst)
        return lst

    def _rebuild_result_list(self):
        """
        تغيير اتجاه القائمة وهي مفتوحة يترك رؤوس الأعمدة بالترتيب القديم في ويندوز،
        فنُنشئ القائمة من جديد بالاتجاه الصحيح مكان القديمة
        """
        old = self.result_list
        new = self._create_result_list()
        self.trans_sizer.Replace(old, new)
        old.Destroy()
        # ترتيب التنقل: بعد عنوانها مباشرة، ليقرأ قارئ الشاشة العنوان كاسم لها
        new.MoveAfterInTabOrder(self.lbl_results)

    def _insert_result_columns(self):
        # عمود النص أولاً: قارئ الشاشة ينطق العمود الأول عند التنقل بالأسهم، فيُسمع الكلام قبل التوقيت
        self.result_list.InsertColumn(0, self.i18n.get("list_header_text"), width=self.FromDIP(600))
        self.result_list.InsertColumn(1, self.i18n.get("list_header_time"), width=self.FromDIP(130))
        # الحالة مكتوبة نصاً (وليس باللون فقط) حتى يسمعها مستخدم قارئ الشاشة
        self.result_list.InsertColumn(2, self.i18n.get("list_header_review"), width=self.FromDIP(220))
        widgets.fit_first_column(self.result_list)

    @staticmethod
    def _weak_words(seg):
        """الكلمات التي لم يكن النموذج متأكداً منها في هذا المقطع"""
        words = seg[4] if len(seg) > 4 and seg[4] else []
        return [w.get("word", "").strip() for w in words if w.get("probability", 1.0) < WEAK_WORD_THRESHOLD]

    @classmethod
    def _is_weak(cls, seg):
        return bool(cls._weak_words(seg))

    def _fill_row(self, row, seg_index):
        seg = self.all_segments[seg_index]
        self.result_list.SetItem(row, 0, seg[1].replace("\n", " "))
        self.result_list.SetItem(row, 1, format_range(seg[2], seg[3]))
        weak = self._weak_words(seg)
        review = self.i18n.get("report_weak_words", words="، ".join(weak)) if weak else ""
        self.result_list.SetItem(row, 2, review)
        # الأسطر العادية بلا لون خاص (تتبع لون القائمة في المظهرين)، والمشكوك فيها أحمر واضح في المظهرين
        weak_colour = wx.Colour(255, 120, 120) if getattr(self, "_theme", "light") == "dark" else wx.Colour(200, 40, 40)
        self.result_list.SetItemTextColour(row, weak_colour if weak else self.result_list.GetForegroundColour())
        # خلفية السطر صراحةً بلون القائمة، وإلا يظهر شريط رمادي بعد إعادة بناء القائمة أو تغيير المظهر
        self.result_list.SetItemBackgroundColour(row, self.result_list.GetBackgroundColour())

    def update_list(self, indices=None):
        """عرض المقاطع. indices أرقام المقاطع داخل all_segments (الكل لو None)"""
        if indices is None:
            indices = list(range(len(self.all_segments)))
        self.result_list.Freeze()
        try:
            self.result_list.DeleteAllItems()
            self.displayed_indices = indices
            for seg_index in indices:
                row = self.result_list.InsertItem(self.result_list.GetItemCount(), "")
                # كل سطر يحمل رقم المقطع الأصلي، فالتشغيل والتعديل يعملان حتى أثناء البحث
                self.result_list.SetItemData(row, seg_index)
                self._fill_row(row, seg_index)
        finally:
            self.result_list.Thaw()

    def on_filter_results(self, event):
        query = self.txt_filter.GetValue().strip().lower()
        if not query:
            self.update_list()
            return
        self.update_list([i for i, seg in enumerate(self.all_segments) if query in seg[1].lower()])

    def _selected_segment_index(self):
        row = self.result_list.GetFirstSelected()
        if row == -1:
            return None, None
        seg_index = self.result_list.GetItemData(row)
        return (row, seg_index) if 0 <= seg_index < len(self.all_segments) else (None, None)

    def _can_play(self):
        return not self.is_batch_mode and self.audio_path and os.path.isfile(self.audio_path)

    def on_list_context_menu(self, event):
        row, seg_index = self._selected_segment_index()
        if seg_index is None:
            return
        menu = wx.Menu()
        mi_play = icons.menu_item(menu, wx.ID_ANY, self.i18n.get("menu_play_segment"), "play")
        mi_edit = icons.menu_item(menu, wx.ID_ANY, self.i18n.get("menu_edit_segment") + "\tF2", "edit")
        mi_merge = icons.menu_item(menu, wx.ID_ANY, self._menu_labels()["mi_merge_next"], "merge")
        mi_play.Enable(bool(self._can_play()))
        self.Bind(wx.EVT_MENU, lambda e: self._play(self.audio_path, *self.all_segments[seg_index][2:4]), mi_play)
        self.Bind(wx.EVT_MENU, self.on_edit_segment, mi_edit)
        self.Bind(wx.EVT_MENU, self.on_merge_next, mi_merge)
        self.result_list.PopupMenu(menu)
        menu.Destroy()

    def on_edit_segment(self, event):
        if self.transcription_thread_running():
            return
        row, seg_index = self._selected_segment_index()
        if seg_index is None:
            # F2 من القائمة بدون سطر محدد: نوضح السبب بدلاً من عدم حدوث أي شيء
            if self.all_segments:
                wx.MessageBox(self.i18n.get("msg_select_segment_first"), self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION)
            return
        seg = self.all_segments[seg_index]
        play = (lambda: self._play(self.audio_path, seg[2], seg[3])) if self._can_play() else None
        dlg = EditSegmentDialog(self, self.i18n, format_range(seg[2], seg[3]), seg[1], play)
        result = dlg.ShowModal()
        if result == ID_SPLIT:
            # التقسيم يطبق على النص كما هو في مربع الكتابة (بما فيه أي تعديل لم يُحفظ بعد)
            edited = (seg[0], dlg.txt.GetValue(), seg[2], seg[3], seg[4] if dlg.txt.GetValue() == seg[1] else [])
            parts = seg_ops.split(edited, dlg.split_pos)
            if parts:
                self.all_segments[seg_index:seg_index + 1] = list(parts)
                self._after_structure_change(seg_index, "status_segment_split")
        elif result == wx.ID_OK:
            new_text = dlg.get_text()
            if new_text and new_text != seg[1]:
                # توقيتات الكلمات القديمة لم تعد تطابق النص، والمراجعة البشرية تلغي علامة الشك
                self.all_segments[seg_index] = (seg[0], new_text, seg[2], seg[3], [])
                self._fill_row(row, seg_index)
                self.unsaved_edits = True
                self.status_bar.SetStatusText(self.i18n.get("status_segment_edited"))
                # التعلم مما صحّحه المستخدم (بعد إغلاق نافذة التعديل حتى لا تتداخل النوافذ)
                wx.CallAfter(self.learn_from_edit, seg_index, seg[1], new_text)
        dlg.Destroy()
        self.result_list.SetFocus()

    def on_merge_next(self, event):
        """دمج السطر المحدد مع الجملة التي تليه في التفريغ"""
        if self.transcription_thread_running():
            return
        row, seg_index = self._selected_segment_index()
        if seg_index is None:
            if self.all_segments:
                wx.MessageBox(self.i18n.get("msg_select_segment_first"), self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION)
            return
        if seg_index + 1 >= len(self.all_segments):
            wx.MessageBox(self.i18n.get("msg_nothing_to_merge"), self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION)
            return
        merged = seg_ops.merge(self.all_segments[seg_index], self.all_segments[seg_index + 1])
        self.all_segments[seg_index:seg_index + 2] = [merged]
        self._after_structure_change(seg_index, "status_segments_merged")

    def _after_structure_change(self, seg_index, status_key):
        """بعد تقسيم أو دمج: إعادة عرض القائمة (مع البحث الحالي) وإبقاء التحديد على نفس الجملة"""
        self.unsaved_edits = True
        self.on_filter_results(None)
        for row in range(self.result_list.GetItemCount()):
            if self.result_list.GetItemData(row) == seg_index:
                self.result_list.Select(row)
                self.result_list.Focus(row)
                self.result_list.EnsureVisible(row)
                break
        self.status_bar.SetStatusText(self.i18n.get(status_key))
        self.result_list.SetFocus()

    def confirm_discard_edits(self):
        """يُستدعى قبل أي عملية تستبدل النتائج الحالية. يرجع False لو المستخدم تراجع"""
        if not getattr(self, 'unsaved_edits', False):
            return True
        dlg = wx.MessageDialog(self, self.i18n.get("msg_unsaved_edits"), self.i18n.get("dialog_warning_title"),
                               wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_QUESTION)
        dlg.SetYesNoCancelLabels(self.i18n.get("btn_save"), self.i18n.get("btn_discard"), self.i18n.get("btn_cancel"))
        res = dlg.ShowModal()
        dlg.Destroy()
        if res == wx.ID_YES:
            self.on_export_srt(None)
            return not self.unsaved_edits
        if res == wx.ID_NO:
            self.unsaved_edits = False
            return True
        return False

    def _play(self, audio_path, start_time, end_time=None):
        if not audio_path or not os.path.isfile(audio_path):
            wx.MessageBox(self.i18n.get("msg_audio_not_found"), self.i18n.get("dialog_error_title"), wx.ICON_WARNING)
            return
        if not self.audio_player.IsShown():
            self.audio_player.Show()
            self.panel.Layout()
        ok, error = self.audio_player.load_and_play(audio_path, start_time or 0, end_time)
        if ok:
            self.status_bar.SetStatusText(self.i18n.get("status_playing"))
        else:
            wx.MessageBox(self.i18n.get("msg_playback_failed", error=error), self.i18n.get("dialog_error_title"), wx.ICON_WARNING)

    def on_play_segment(self, event):
        if not self._can_play(): return
        seg_index = self.result_list.GetItemData(event.GetIndex())
        if 0 <= seg_index < len(self.all_segments):
            seg = self.all_segments[seg_index]
            self._play(self.audio_path, seg[2], seg[3] if self.mi_sentence_only.IsChecked() else None)

    def on_stop_audio(self, event):
        self.audio_player.on_stop(None)
        if self.audio_player.IsShown():
            self.audio_player.Hide()
            self.panel.Layout()
        self.status_bar.SetStatusText(self.i18n.get("status_ready"))

    def play_audio_from_search(self, audio_path, start_time):
        self._play(audio_path, start_time)
