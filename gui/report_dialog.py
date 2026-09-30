import wx
from core.i18n import LocalizationManager

class ReportDialog(wx.Dialog):
    def __init__(self, parent, i18n: LocalizationManager, report_data: dict):
        super().__init__(parent, title=i18n.get("report_title"), size=(700, 600), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.i18n = i18n
        i18n.apply_direction(self)
        self.report = report_data or {}
        self.setup_ui()
        self.CenterOnParent()

    def _summary_text(self):
        g = self.i18n.get
        r = self.report
        unknown = g('dl_val_unknown')
        stats = r.get('statistics', {})
        audio_info = r.get('audio_info', {})
        proc = r.get('processing_time', {})

        lines = [
            f"{g('report_file_name')} {r.get('file_name', unknown)}",
            f"{g('report_model')} {r.get('model_used', unknown)}",
            f"{g('report_audio_duration')} {audio_info.get('duration_formatted', unknown)}",
            f"{g('report_processing_time')} {proc.get('formatted', unknown)}",
        ]

        audio_sec = audio_info.get('duration_seconds', 0) or 0
        proc_sec = proc.get('total_seconds', 0) or 0
        if audio_sec > 0 and proc_sec > 0:
            # كم ثانية صوت تتم معالجتها في كل ثانية (أكبر من 1 = أسرع من الزمن الحقيقي)
            lines.append(f"{g('report_speed_ratio')} {audio_sec / proc_sec:.2f}x")

        lines += [
            f"{g('history_col_status')}: {r.get('status', unknown)}",
            "",
            f"{g('report_accuracy_score')} {r.get('score', 0)}%",
            f"{g('report_total_segments')}: {stats.get('total_segments', 0)}",
            f"{g('report_flagged_segments')} {r.get('flagged_segments', 0)}",
            f"{g('report_total_words')} {stats.get('total_words', 0)}",
            f"{g('report_words_per_minute')} {stats.get('words_per_minute', 0)}",
        ]

        errors = r.get('errors', [])
        if errors:
            lines += ["", f"{g('history_status_errors')}:"] + errors

        warnings = r.get('warnings', [])
        if warnings:
            lines += ["", f"{g('report_warnings')}:"] + warnings

        return "\n".join(lines)

    def setup_ui(self):
        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        text_ctrl = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        font = text_ctrl.GetFont()
        font.SetPointSize(11)
        text_ctrl.SetFont(font)
        text_ctrl.SetValue(self._summary_text())
        sizer.Add(text_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        details = self.report.get('segment_details') or []
        if details:
            lbl = wx.StaticText(panel, label=self.i18n.get("report_detailed_title"))
            sizer.Add(lbl, 0, wx.LEFT | wx.RIGHT, 10)

            self.list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES)
            self.list_ctrl.InsertColumn(0, self.i18n.get("report_col_time"), width=160)
            self.list_ctrl.InsertColumn(1, self.i18n.get("report_col_confidence"), width=110)
            self.list_ctrl.InsertColumn(2, self.i18n.get("report_col_status"), width=360)
            for idx, d in enumerate(details):
                self.list_ctrl.InsertItem(idx, d.get("time", ""))
                self.list_ctrl.SetItem(idx, 1, d.get("confidence", ""))
                self.list_ctrl.SetItem(idx, 2, d.get("status", ""))
                if d.get("flagged"):
                    self.list_ctrl.SetItemTextColour(idx, wx.Colour(200, 40, 40))
            sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        btn_close = wx.Button(panel, id=wx.ID_OK, label=self.i18n.get("btn_close"))
        sizer.Add(btn_close, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        panel.SetSizer(sizer)
        wx.CallAfter(text_ctrl.SetFocus)
