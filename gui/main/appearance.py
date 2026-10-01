"""المظهر واللغة واتجاه الواجهة وحجم الخط والأيقونات، وعنوان النافذة ومقاسها ومكانها"""
import wx
from gui import icons, widgets



class AppearanceMixin:
    """جزء من النافذة الرئيسية (MainWindow): المظهر واللغة واتجاه الواجهة وحجم الخط والأيقونات، وعنوان النافذة ومقاسها ومكانها"""

    def restore_window_geometry(self):
        """فتح النافذة بنفس مقاسها ومكانها في المرة السابقة، بشرط أن يكون المكان ما زال داخل شاشة موجودة"""
        geo = self.settings.get("window_geometry") or {}
        try:
            x, y, w, h = (int(geo[k]) for k in ("x", "y", "w", "h"))
        except (KeyError, TypeError, ValueError):
            return
        if wx.Display.GetFromPoint(wx.Point(x + 40, y + 20)) == wx.NOT_FOUND:
            return  # الشاشة التي كانت عليها النافذة لم تعد موصولة
        self.SetSize(x, y, max(w, 600), max(h, 400))
        widgets.fit_to_screen(self)
        if geo.get("maximized"):
            self.Maximize()

    def save_window_geometry(self):
        maximized = self.IsMaximized()
        rect = self.GetRect() if not (maximized or self.IsIconized()) else None
        geo = dict(self.settings.get("window_geometry") or {})
        if rect is not None:
            geo.update(x=rect.x, y=rect.y, w=rect.width, h=rect.height)
        geo["maximized"] = maximized
        self.settings.set("window_geometry", geo)

    def get_base_title(self):
        return f"{self.i18n.get('app_name')} - {self.i18n.get('app_version')}"

    def update_title_with_tab(self):
        if hasattr(self, 'notebook'):
            sel = self.notebook.GetSelection()
            if sel != wx.NOT_FOUND:
                tab_name = self.notebook.GetPageText(sel)
                self.SetTitle(f"{self.get_base_title()} - {tab_name}")
                status_template = self.i18n.get("status_current_tab")
                if "{0}" in status_template:
                    self.status_bar.SetStatusText(status_template.format(tab_name))
                else:
                    self.status_bar.SetStatusText(f"[{tab_name}]")

    def on_tab_changed(self, event):
        self.update_title_with_tab()
        event.Skip()

    def on_key_press(self, event):
        keycode = event.GetKeyCode()
        ctrl_down = event.ControlDown()
        shift_down = event.ShiftDown()
        if ctrl_down and keycode == wx.WXK_TAB:
            self.switch_tab(-1 if shift_down else 1)
            return
        if ctrl_down and keycode == wx.WXK_RIGHT:
            self.switch_tab(1)
            return
        elif ctrl_down and keycode == wx.WXK_LEFT:
            self.switch_tab(-1)
            return
        event.Skip()

    def switch_tab(self, direction):
        if hasattr(self, 'notebook'):
            count = self.notebook.GetPageCount()
            if count > 1:
                current = self.notebook.GetSelection()
                next_tab = (current + direction) % count
                self.notebook.SetSelection(next_tab)
                self.update_title_with_tab()

    def apply_icons(self):
        """أيقونات الأزرار والتبويبات (تُعاد عند تغيير المظهر لأن لونها يتبع الفاتح/الداكن)"""
        for btn, name in ((self.btn_select, "audio_file"), (self.btn_select_folder, "folder"),
                          (self.btn_process, "transcribe"), (self.btn_export, "save")):
            icons.button(btn, name)
        # التبويبات يرسمها ويندوز فاتحة دائماً، فأيقوناتها بألوان المظهر الفاتح
        self._tab_images = icons.image_list(["transcribe", "search"], theme="light")
        self.notebook.SetImageList(self._tab_images)
        self.notebook.SetPageImage(0, 0)
        self.notebook.SetPageImage(1, 1)
        self.search_panel.apply_icons()
        self.audio_player.apply_icons()

    def setup_button_hover_effects(self):
        buttons = [self.btn_select, self.btn_select_folder, self.btn_process, self.btn_export]
        for btn in buttons:
            btn.Bind(wx.EVT_ENTER_WINDOW, self.on_button_hover)
            btn.Bind(wx.EVT_LEAVE_WINDOW, self.on_button_leave)

    def on_button_hover(self, event):
        btn = event.GetEventObject()
        if btn.IsEnabled():
            theme = self.settings.get("theme", "light")
            if theme == "dark": btn.SetBackgroundColour(wx.Colour(45, 56, 78))
            else: btn.SetBackgroundColour(wx.Colour(233, 236, 239))
            btn.Refresh()
        event.Skip()

    def on_button_leave(self, event):
        btn = event.GetEventObject()
        theme = self.settings.get("theme", "light")
        if theme == "dark": btn.SetBackgroundColour(wx.Colour(30, 38, 54))
        else: btn.SetBackgroundColour(wx.Colour(255, 255, 255))
        btn.Refresh()
        event.Skip()

    def apply_layout_direction(self):
        """العربية من اليمين لليسار والإنجليزية من اليسار لليمين، للنافذة وكل ما بداخلها. ترجع True لو تغيّر الاتجاه"""
        direction = wx.Layout_RightToLeft if self.i18n.language == "ar" else wx.Layout_LeftToRight
        if self.GetLayoutDirection() == direction:
            return False
        def apply(widget):
            widget.SetLayoutDirection(direction)
            for child in widget.GetChildren():
                apply(child)
        self.Freeze()
        try:
            apply(self)
            if self.GetStatusBar(): self.GetStatusBar().SetLayoutDirection(direction)
            self.i18n.fix_notebook(self.notebook)
        finally:
            self.Thaw()
        return True

    def refresh_ui_texts(self):
        direction_changed = self.apply_layout_direction()
        if hasattr(self, 'notebook'):
            self.notebook.SetPageText(0, self.i18n.get("tab_transcription"))
            self.notebook.SetPageText(1, self.i18n.get("tab_global_search"))

        menubar = self.GetMenuBar()
        if menubar:
            menubar.SetMenuLabel(0, self.i18n.get("menu_file"))
            menubar.SetMenuLabel(1, self.i18n.get("menu_view"))
            menubar.SetMenuLabel(2, self.i18n.get("menu_tools"))
            menubar.SetMenuLabel(3, self.i18n.get("menu_help"))
            for attr, label in self._menu_labels().items():
                getattr(self, attr).SetItemLabel(label)

        self.btn_select.SetLabel(self.i18n.get("btn_select_audio"))
        self.btn_select_folder.SetLabel(self.i18n.get("btn_select_folder"))
        self.btn_process.SetLabel(self.i18n.get("btn_process"))
        self.btn_export.SetLabel(self.i18n.get("btn_export"))
        self.lbl_filter.SetLabel(self.i18n.get("lbl_search"))
        self.lbl_file_path.SetLabel(self.i18n.get("lbl_selected_file"))
        self.lbl_results.SetLabel(self.i18n.get("lbl_results"))
        self.lbl_dictionary.SetLabel(self.i18n.get("lbl_dictionary"))

        if direction_changed:
            self._rebuild_result_list()
            self.search_panel.rebuild_list()
            self.apply_theme(getattr(self, "_theme", "light"))
            self.apply_font_size(self.settings.get("font_size", 10))
        else:
            self.result_list.ClearAll()
            self._insert_result_columns()
        self.update_list(self.displayed_indices)

        self.search_panel.refresh_ui_texts()
        self.audio_player.refresh_ui_texts()

        self.update_title_with_tab()
        self.status_bar.SetStatusText(self.i18n.get("status_ready"))
        # النصوص الجديدة أطول أو أقصر: إعادة حساب مقاس كل زر وعنوان حتى لا يُقص النص
        widgets.refit_texts(self.panel)
        # إعادة ترتيب كل لوحة داخلية (وليس الخارجية فقط)، وإلا تبقى القائمة الجديدة والأزرار بمقاساتها القديمة
        for pane in (self.transcription_panel, self.search_panel, self.audio_player, self.panel):
            pane.Layout()
        self.SendSizeEvent()
        self.Refresh()

    def apply_theme(self, theme):
        self._theme = theme
        if theme == "dark":
            bg_color = wx.Colour(15, 19, 28)
            panel_bg = wx.Colour(22, 29, 43)
            fg_color = wx.Colour(241, 241, 241)
            list_bg = wx.Colour(10, 13, 18)
            button_bg = wx.Colour(30, 38, 54)
        else:
            bg_color = wx.Colour(248, 249, 250)
            panel_bg = wx.Colour(255, 255, 255)
            fg_color = wx.Colour(33, 37, 41)
            list_bg = wx.Colour(255, 255, 255)
            button_bg = wx.Colour(255, 255, 255)

        self.SetBackgroundColour(bg_color)
        self.SetForegroundColour(fg_color)
        self.panel.SetBackgroundColour(panel_bg)
        self.panel.SetForegroundColour(fg_color)

        def apply_recursive(widget):
            if isinstance(widget, wx.ListCtrl):
                widget.SetBackgroundColour(list_bg)
                widget.SetForegroundColour(fg_color)
            elif isinstance(widget, wx.Button):
                widget.SetBackgroundColour(button_bg)
                widget.SetForegroundColour(fg_color)
            elif isinstance(widget, wx.TextCtrl):
                widget.SetBackgroundColour(list_bg if theme == "dark" else wx.Colour(255, 255, 255))
                widget.SetForegroundColour(fg_color)
            elif isinstance(widget, wx.Notebook):
                widget.SetBackgroundColour(bg_color)
                widget.SetForegroundColour(fg_color)
            else:
                widget.SetBackgroundColour(panel_bg)
                widget.SetForegroundColour(fg_color)
            for child in widget.GetChildren(): apply_recursive(child)

        apply_recursive(self.panel)
        # لون الأيقونات يتبع المظهر
        icons.set_theme(theme)
        self.apply_icons()
        # إعادة رسم الأسطر بلون المظهر الجديد (لون كل سطر يُحدد عند رسمه)
        self.update_list(self.displayed_indices)
        self.Refresh()

    def apply_font_size(self, size):
        try:
            size = int(size)
        except (TypeError, ValueError):
            size = 10
        font = wx.Font(size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        def set_font_recursive(widget):
            widget.SetFont(font)
            for child in widget.GetChildren(): set_font_recursive(child)
        set_font_recursive(self.panel)
        self.panel.Layout()
        self.Refresh()
