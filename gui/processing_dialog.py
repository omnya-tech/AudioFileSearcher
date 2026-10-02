import time
import wx
from gui import icons, widgets
from core.i18n import LocalizationManager
from core.time_utils import format_clock

# لا نعرض تقديراً للوقت المتبقي قبل مرور هذه المدة وهذا القدر من التقدم (التقدير المبكر غير دقيق)
ETA_MIN_SECONDS = 15
ETA_MIN_PERCENT = 2
# كل كم جزء من الثانية يتحرك الشريط المتحرك قبل أول تقدم فعلي، ويتحدث سطر التفاصيل (الوقت المنقضي)
TIMER_MS = 250
# سطور القائمة: الملف، والنسبة (يُنطق عند تغيّره لأنه السطر المحدد)، والتفاصيل (تتحدث بصمت)
ROW_FILE, ROW_PERCENT, ROW_DETAILS = range(3)


class ProcessingDialog(wx.Dialog):
    """
    نافذة التقدم أثناء التفريغ: نسبة تُعلَن كل 10%، وتفاصيل (الموضع في الصوت، والوقت المنقضي، وعدد الجمل)،
    والنص يظهر أولاً بأول، وأزرار للإيقاف المؤقت والعمل في الخلفية والإلغاء.
    """

    def __init__(self, parent, i18n: LocalizationManager):
        super().__init__(parent, title=i18n.get("dialog_processing_title"), size=(640, 460),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.i18n = i18n
        i18n.apply_direction(self)
        widgets.fit_to_screen(self)
        self.parent_win = parent
        self.is_canceling = False
        self.is_paused = False
        self.percent = 0
        self.filename = ""
        self.batch = None
        self.position = 0.0
        self.duration = 0.0
        self.segment_count = 0
        # الوقت المنقضي دون فترات الإيقاف المؤقت
        self._started = time.time()
        self._paused_at = None
        self._paused_total = 0.0

        self.setup_ui()
        if hasattr(parent, 'settings'):
            self.apply_theme(parent.settings.get("theme", "light"))

        self._place_above_results(parent)

        # توجيه التركيز فوراً إلى سطر النسبة ليقرأه قارئ الشاشة
        wx.CallAfter(self.list_ctrl.SetFocus)
        wx.CallAfter(self.list_ctrl.Focus, ROW_PERCENT)
        wx.CallAfter(self.list_ctrl.Select, ROW_PERCENT)

        # Ctrl+I يعلن نسبة التقدم من داخل هذه النافذة أيضاً (اختصارات النافذة الرئيسية لا تعمل هنا).
        # هذه النافذة بلا قوائم، فلا خطر من أن يستبدل جدول الاختصارات اختصارات أخرى
        id_progress = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.on_announce_progress, id=id_progress)
        self.SetAcceleratorTable(wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('I'), id_progress)]))

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(TIMER_MS)

    def _place_above_results(self, parent):
        """أعلى نافذة البرنامج بدلاً من منتصفها: تبقى قائمة النتائج ظاهرة والجمل تُضاف إليها أثناء التفريغ"""
        if not parent:
            self.CenterOnScreen()
            return
        px, py = parent.GetScreenPosition()
        pw, _ = parent.GetSize()
        self.SetPosition((px + (pw - self.GetSize().width) // 2, py + self.FromDIP(60)))

    def on_announce_progress(self, event):
        if hasattr(self.parent_win, 'on_check_progress'):
            self.parent_win.on_check_progress(None)

    def setup_ui(self):
        g = self.i18n.get
        self.panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 1. رسالة الانتظار (صديقة لقارئ الشاشة)
        self.lbl_title = wx.TextCtrl(self.panel, value=g("dialog_processing_msg"),
                                     style=wx.TE_READONLY | wx.BORDER_NONE | wx.TE_CENTER)
        title_font = self.lbl_title.GetFont()
        title_font.SetPointSize(11)
        title_font.MakeBold()
        self.lbl_title.SetFont(title_font)
        main_sizer.Add(self.lbl_title, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)

        # 2. القائمة: عمود واحد عريض، وكل سطر جملة كاملة لا يُقص، وقارئ الشاشة يقرأ السطر كاملاً.
        # سطر النسبة (عليه التركيز) يتغير اسمه مع التقدم، فينطقه قارئ الشاشة تلقائياً
        self.list_ctrl = wx.ListCtrl(self.panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_NO_HEADER)
        self.list_ctrl.InsertColumn(0, g("proc_col_status"), width=self.FromDIP(560))
        self.list_ctrl.InsertItem(ROW_FILE, f"{g('proc_item_file')} {g('proc_val_waiting')}")
        self.list_ctrl.InsertItem(ROW_PERCENT, f"{g('proc_item_percent')} 0% - {g('status_init_engine').replace('...', '')}")
        self.list_ctrl.InsertItem(ROW_DETAILS, "")
        self._last_announced = None
        self.list_ctrl.SetMinSize((-1, self.list_ctrl.FromDIP(72)))
        main_sizer.Add(self.list_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 15)

        # 3. شريط التقدم: يتحرك ذهاباً وإياباً حتى أول تقدم فعلي (تحميل النموذج وأول مقطع)، ثم يتبع النسبة
        self.gauge = wx.Gauge(self.panel, range=100, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        self.gauge.SetMinSize((-1, self.gauge.FromDIP(22)))
        main_sizer.Add(self.gauge, 0, wx.EXPAND | wx.ALL, 15)

        # 4. النص أولاً بأول
        main_sizer.Add(wx.StaticText(self.panel, label=g("proc_live_text")), 0, wx.LEFT | wx.RIGHT, 15)
        self.live_text = wx.TextCtrl(self.panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        self.live_text.SetMinSize((-1, self.live_text.FromDIP(120)))
        main_sizer.Add(self.live_text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        # 5. الأزرار
        line = wx.StaticLine(self.panel)
        main_sizer.Add(line, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)
        self.btn_pause = icons.button(wx.Button(self.panel, label=g("btn_pause_processing")), "pause")
        self.btn_background = icons.button(wx.Button(self.panel, label=g("btn_processing_background")), "hide")
        self.btn_cancel = icons.button(wx.Button(self.panel, id=wx.ID_CANCEL, label=g("btn_cancel")), "cancel")
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for b in (self.btn_pause, self.btn_background):
            buttons.Add(b, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer(1)
        buttons.Add(self.btn_cancel)
        main_sizer.Add(buttons, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 15)

        self.btn_pause.Bind(wx.EVT_BUTTON, self.on_pause)
        self.btn_background.Bind(wx.EVT_BUTTON, self.on_background)
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        # إغلاق النافذة (زر X أو Esc) يعني إلغاء العملية، بدلاً من إخفائها والعملية مستمرة
        self.Bind(wx.EVT_CLOSE, self.on_cancel)

        self.panel.SetSizer(main_sizer)

    # ---------- التقدم ----------

    def set_batch(self, current, total):
        """وضع المجلد: الملف الحالي من العدد الكلي. ملف جديد يعني نصاً وتفاصيل جديدة"""
        self.batch = (current, total)
        self.clear_text()
        self._refresh_file_row()

    def _refresh_file_row(self):
        display_name = self.filename if len(self.filename) <= 45 else self.filename[:20] + "..." + self.filename[-20:]
        text = f"{self.i18n.get('proc_item_file')} {display_name or self.i18n.get('proc_val_waiting')}"
        if self.batch:
            text += " - " + self.i18n.get("proc_batch", current=self.batch[0], total=self.batch[1])
        if self.list_ctrl.GetItemText(ROW_FILE) != text:
            self.list_ctrl.SetItemText(ROW_FILE, text)

    def update_progress(self, percent, total, status, filename):
        if self.is_canceling:
            return
        self.percent = percent
        if filename != self.filename:
            self.filename = filename
            self._refresh_file_row()

        if percent > 0:
            self.gauge.SetValue(percent)

        if self.is_paused:
            return

        eta = self._estimate_remaining(percent, filename)
        eta_text = self.format_eta(eta) if eta is not None else ""

        # الإعلان كل 10% أو عند تغيّر الخطوة فقط، حتى لا يقاطع قارئ الشاشة المستخدم مع كل 1%
        clean_status = status.replace("...", "").strip()
        announcement = (percent // 10 * 10, clean_status)
        if announcement != self._last_announced:
            self._last_announced = announcement
            parts = [f"{self.i18n.get('proc_item_percent')} {percent}%", clean_status, eta_text]
            self.list_ctrl.SetItemText(ROW_PERCENT, " - ".join(p for p in parts if p))
        widgets.fit_first_column(self.list_ctrl, min_width=100)

        # عنوان النافذة يعرض الحالة الحالية (يُقرأ عند طلبه بـ NVDA+T)
        self.SetTitle(f"{percent}% - {clean_status} - {self.i18n.get('dialog_processing_title')}")
        self.panel.Layout()

    def add_segment(self, text, end, duration):
        """جملة جديدة اكتمل تفريغها: تُضاف للنص، ويتقدم الموضع"""
        self.position, self.duration = end, duration or self.duration
        self.segment_count += 1
        self.live_text.AppendText(("\n" if self.live_text.GetLastPosition() else "") + text)
        self._refresh_details()

    def set_text(self, texts, end=0.0, duration=0.0):
        """عند الاستكمال: الجمل المفرغة سابقاً تظهر أولاً"""
        self.clear_text()
        self.live_text.SetValue("\n".join(texts))
        self.live_text.SetInsertionPointEnd()
        self.segment_count = len(texts)
        self.position, self.duration = end, duration
        self._refresh_details()

    def clear_text(self):
        self.live_text.Clear()
        self.segment_count = 0
        self.position = self.duration = 0.0
        self._started, self._paused_at, self._paused_total = time.time(), None, 0.0
        self._eta_start = None
        self._refresh_details()

    def elapsed(self):
        paused = self._paused_total + ((time.time() - self._paused_at) if self._paused_at else 0)
        return max(0.0, time.time() - self._started - paused)

    def _refresh_details(self):
        g = self.i18n.get
        parts = []
        if self.duration:
            parts.append(g("proc_position", position=format_clock(self.position), duration=format_clock(self.duration)))
        parts.append(g("proc_elapsed", elapsed=format_clock(self.elapsed())))
        if self.segment_count:
            parts.append(self.i18n.plural("n_lines", self.segment_count))
        text = "، ".join(parts) if self.i18n.is_rtl else ", ".join(parts)
        if self.list_ctrl.GetItemText(ROW_DETAILS) != text:
            self.list_ctrl.SetItemText(ROW_DETAILS, text)

    def on_timer(self, event):
        if self.is_canceling:
            return
        # قبل أول تقدم فعلي (تحميل النموذج، وأول مقطع) الشريط يتحرك ليبيّن أن العمل جارٍ
        if self.percent == 0 and not self.is_paused:
            self.gauge.Pulse()
        self._refresh_details()

    def _estimate_remaining(self, percent, filename):
        """الوقت المتبقي بالثواني من سرعة التقدم الفعلية منذ بداية الملف الحالي (أو منذ نقطة الاستكمال أو الإيقاف)"""
        now = time.time()
        start = getattr(self, "_eta_start", None)
        # بداية ملف جديد (وضع المجلد) أو أول تقدم فعلي: نعيد ضبط نقطة القياس
        if start is None or start[0] != filename or percent < start[2]:
            self._eta_start = (filename, now, percent)
            return None
        _, t0, p0 = start
        done = percent - p0
        elapsed = now - t0
        if done < ETA_MIN_PERCENT or elapsed < ETA_MIN_SECONDS or percent >= 100:
            return None
        return elapsed * (100 - percent) / done

    def format_eta(self, seconds):
        minutes = int(round(seconds / 60))
        if minutes < 1:
            return self.i18n.get("eta_less_than_minute")
        hours, mins = divmod(minutes, 60)
        parts = []
        if hours:
            parts.append(self.i18n.plural("unit_hours", hours))
        if mins:
            parts.append(self.i18n.plural("unit_minutes", mins))
        return self.i18n.get("eta_about", time=self.i18n.get("word_and").join(parts))

    # ---------- الأزرار ----------

    def on_pause(self, event):
        if self.is_canceling:
            return
        if self.is_paused:
            self.set_paused(False)
            if hasattr(self.parent_win, 'resume_processing'):
                self.parent_win.resume_processing()
        else:
            self.set_paused(True)
            if hasattr(self.parent_win, 'pause_processing'):
                self.parent_win.pause_processing()

    def set_paused(self, paused):
        g = self.i18n.get
        if paused == self.is_paused:
            return
        self.is_paused = paused
        if paused:
            self._paused_at = time.time()
            self.btn_pause.SetLabel(g("btn_resume_processing"))
            icons.button(self.btn_pause, "play")
            msg = g("proc_paused", percent=self.percent)
            self.list_ctrl.SetItemText(ROW_PERCENT, msg)
            self.SetTitle(f"{msg} - {g('dialog_processing_title')}")
        else:
            if self._paused_at:
                self._paused_total += time.time() - self._paused_at
            self._paused_at = None
            # التقدير يبدأ من جديد بعد الاستئناف: فترة الإيقاف ليست بطئاً
            self._eta_start = None
            self._last_announced = None
            self.btn_pause.SetLabel(g("btn_pause_processing"))
            icons.button(self.btn_pause, "pause")
            self.update_progress(self.percent, 100, g("status_extracting"), self.filename)
        self.panel.Layout()

    def on_background(self, event):
        if hasattr(self.parent_win, 'send_processing_to_background'):
            self.parent_win.send_processing_to_background()
        else:
            self.Hide()

    def on_cancel(self, event):
        if self.is_canceling:
            return
        self.is_canceling = True
        self.timer.Stop()
        for b in (self.btn_cancel, self.btn_pause, self.btn_background):
            b.Disable()

        # إعلام المستخدم بالإلغاء في الجدول وعنوان النافذة
        cancel_msg = self.i18n.get("proc_step_cancel")
        self.list_ctrl.SetItemText(ROW_PERCENT, cancel_msg)
        self.list_ctrl.SetItemBackgroundColour(ROW_PERCENT, wx.Colour(255, 230, 230))  # تمييز صف الإلغاء بلون مختلف

        self.SetTitle(cancel_msg)
        self.gauge.Pulse()
        self.panel.Layout()

        if hasattr(self.parent_win, 'cancel_processing'):
            wx.CallAfter(self.parent_win.cancel_processing)

    def Destroy(self):
        if getattr(self, "timer", None):
            self.timer.Stop()
        return super().Destroy()

    def apply_theme(self, theme):
        if theme == "dark":
            bg_color = wx.Colour(22, 29, 43)
            fg_color = wx.Colour(241, 241, 241)
            list_bg = wx.Colour(30, 38, 56)
        else:
            bg_color = wx.Colour(248, 249, 250)
            fg_color = wx.Colour(33, 37, 41)
            list_bg = wx.Colour(255, 255, 255)

        self.SetBackgroundColour(bg_color)
        self.SetForegroundColour(fg_color)
        self.panel.SetBackgroundColour(bg_color)
        self.panel.SetForegroundColour(fg_color)

        # تلوين حقل النص ليتماشى مع الخلفية
        self.lbl_title.SetBackgroundColour(bg_color)
        self.lbl_title.SetForegroundColour(fg_color)

        # تلوين القائمة ونص التفريغ
        for ctrl in (self.list_ctrl, self.live_text):
            ctrl.SetBackgroundColour(list_bg)
            ctrl.SetForegroundColour(fg_color)

        # الأزرار بنفس ألوان المظهر، وإلا تختفي أيقوناتها الفاتحة على خلفية الأزرار الفاتحة
        for btn, icon in ((self.btn_cancel, "cancel"), (self.btn_pause, "play" if self.is_paused else "pause"),
                          (self.btn_background, "hide")):
            btn.SetBackgroundColour(wx.Colour(30, 38, 54) if theme == "dark" else wx.Colour(255, 255, 255))
            btn.SetForegroundColour(fg_color)
            icons.button(btn, icon, theme=theme)

        self.Refresh()
