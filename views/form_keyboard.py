from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.textinput import TextInput


class FormKeyboardMixin:
    _form_keyboard_ready = False
    _form_scroll_id = None
    _active_input = None

    def _setup_form_keyboard(self, scroll_id):
        self._form_scroll_id = scroll_id
        if self._form_keyboard_ready:
            return

        for widget in self._iter_text_inputs():
            widget.bind(focus=self._on_form_input_focus)
            widget.bind(on_text_validate=self._on_form_input_validate)

        self._form_keyboard_ready = True

    def _teardown_form_keyboard(self):
        if not self._form_keyboard_ready:
            return

        for widget in self._iter_text_inputs():
            try:
                widget.unbind(focus=self._on_form_input_focus)
                widget.unbind(on_text_validate=self._on_form_input_validate)
            except Exception:
                pass

        self._form_keyboard_ready = False
        self._active_input = None

    def _iter_text_inputs(self):
        stack = [self]
        while stack:
            widget = stack.pop()
            children = getattr(widget, "children", None) or []
            stack.extend(children)
            if isinstance(widget, TextInput):
                yield widget

    def _on_form_input_focus(self, widget, focused):
        if focused:
            self._active_input = widget
            self._schedule_scroll(0.15)
            return

        if self._active_input is widget:
            Clock.schedule_once(lambda dt: self._clear_active_input(widget), 0.05)

    def _on_form_input_validate(self, widget):
        widget.focus = False

    def _clear_active_input(self, widget):
        if self._active_input is widget and not widget.focus:
            self._active_input = None

    def on_keyboard_height_changed(self, height):
        if height and self._active_input and self._active_input.focus:
            self._schedule_scroll(0.1)

    def _schedule_scroll(self, delay):
        Clock.schedule_once(lambda dt: self._scroll_active_input(), delay)

    def _scroll_active_input(self):
        active = self._active_input
        if not active or not active.focus:
            return

        scroll = self.ids.get(self._form_scroll_id) if self._form_scroll_id else None
        if not scroll:
            return

        try:
            objetivo = active
            parent = getattr(active, "parent", None)
            if parent is not None and getattr(parent, "orientation", "") == "horizontal":
                objetivo = parent
            scroll.scroll_to(objetivo, padding=dp(40), animate=False)
        except Exception:
            pass
