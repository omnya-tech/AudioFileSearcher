"""التعلم من تعديلات المستخدم، وتطبيق القاموس على النتائج الحالية"""
import wx

from core.learning import LearningStore
from core.text_corrector import TextCorrector
from core import dictionaries

# في الوضع التلقائي: لا نتعلم تصحيحاً إلا بعد تكراره، حتى لا نعمّم تصحيحاً كان صحيحاً في سياق واحد فقط
AUTO_LEARN_MIN_COUNT = 2
# الكلمات القصيرة جداً (مثل "و") غامضة: لا تُتعلَّم تلقائياً، فقط بموافقة صريحة
AUTO_LEARN_MIN_LENGTH = 3
LEARN_MODES = ["ask", "auto", "off"]


class LearningMixin:
    """جزء من النافذة الرئيسية (MainWindow): التعلم من التعديلات وتطبيق القاموس على النتائج"""

    @property
    def learning(self):
        if getattr(self, "_learning_store", None) is None:
            self._learning_store = LearningStore()
        return self._learning_store

    def learn_from_edit(self, seg_index, original, edited):
        """بعد تعديل جملة: استخراج ما صحّحه المستخدم، ثم التعلّم حسب الوضع المختار في الإعدادات"""
        # يُستدعى بعد لحظة من إغلاق نافذة التعديل: لو أُغلق البرنامج في هذه اللحظة لا نفعل شيئاً
        if not self or self.IsBeingDeleted():
            return
        mode = self.settings.get("learn_mode", "ask")
        if mode == "off":
            return
        seg = self.all_segments[seg_index]
        pairs = self.learning.record_edit(self.audio_path, seg[2], seg[3], original, edited)
        if not pairs:
            return

        if mode == "auto":
            learned = [(w, r) for w, r in pairs
                       if self.learning.count(w, r) >= AUTO_LEARN_MIN_COUNT and len(w) >= AUTO_LEARN_MIN_LENGTH]
            if learned:
                self._add_to_dictionary(learned)
                changed = self.apply_corrections(dict(learned), skip_index=seg_index)
                self.status_bar.SetStatusText(self.i18n.get("status_learned_auto", words=self._describe(learned),
                                                                    count=self.i18n.plural("n_lines", changed)))
            return

        dlg = wx.MessageDialog(self, self.i18n.get("msg_learn_ask", words=self._describe(pairs),
                                                   dictionary=dictionaries.active_name(self.settings)),
                               self.i18n.get("dialog_learn_title"), wx.YES_NO | wx.CANCEL | wx.YES_DEFAULT | wx.ICON_QUESTION)
        dlg.SetYesNoCancelLabels(self.i18n.get("btn_learn_and_apply"), self.i18n.get("btn_learn_only"), self.i18n.get("btn_dont_learn"))
        answer = dlg.ShowModal()
        dlg.Destroy()
        if answer == wx.ID_CANCEL:
            return
        self._add_to_dictionary(pairs)
        if answer == wx.ID_YES:
            changed = self.apply_corrections(dict(pairs), skip_index=seg_index)
            wx.MessageBox(self.i18n.get("msg_learn_applied", count=self.i18n.plural("n_lines", changed)) if changed
                          else self.i18n.get("msg_learn_saved"),
                          self.i18n.get("dialog_learn_title"), wx.ICON_INFORMATION)

    @staticmethod
    def _describe(pairs):
        return "، ".join(f"«{w}» ← «{r}»" for w, r in pairs)

    def _add_to_dictionary(self, pairs):
        """التصحيحات المتعلَّمة تدخل قاموس المجال المختار: تُطبق في كل تفريغ قادم وتُعطى للنموذج كتلميحات"""
        dictionaries.add_corrections(self.settings, pairs)

    def apply_corrections(self, dictionary, skip_index=None):
        """تطبيق تصحيحات على كل جمل النتائج الحالية. ترجع عدد الجمل التي تغيّرت"""
        if not dictionary or not self.all_segments:
            return 0
        corrector = TextCorrector(dictionary)
        level = self.settings.get("correction_level", "medium")
        changed = 0
        for i, seg in enumerate(self.all_segments):
            if i == skip_index:
                continue
            new_text = corrector.correct(seg[1], level=level)
            if new_text != seg[1]:
                # توقيتات الكلمات تبقى (التصحيح لا يغير عدد الجمل)، لكن علامة الشك تزول لأن الكلمة صُحّحت
                words = [w for w in (seg[4] if len(seg) > 4 else []) if w.get("word", "").strip() not in dictionary]
                self.all_segments[i] = (seg[0], new_text, seg[2], seg[3], words)
                changed += 1
        if changed:
            self.unsaved_edits = True
            self.update_list(self.displayed_indices)
        return changed

    def on_apply_dictionary(self, event):
        """تطبيق القاموس كله على النتائج الحالية (مثلاً بعد إضافة كلمات، أو على ملف ترجمة مفتوح)"""
        if self.transcription_thread_running() or not self.all_segments:
            return
        dictionary = dictionaries.active_corrections(self.settings)
        if not dictionary:
            wx.MessageBox(self.i18n.get("msg_dictionary_empty"), self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION)
            return
        changed = self.apply_corrections(dictionary)
        msg = self.i18n.get("msg_dictionary_applied", count=self.i18n.plural("n_lines", changed)) if changed \
            else self.i18n.get("msg_dictionary_nothing")
        wx.MessageBox(msg, self.i18n.get("dialog_info_title"), wx.ICON_INFORMATION)
