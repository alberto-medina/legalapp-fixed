from kivy.uix.button import Button
from kivy.uix.label import Label


class BotonPro(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_color = (0.20, 0.60, 1, 1)
        self.color = (1, 1, 1, 1)
        self.size_hint_y = None
        self.height = 50
        self.bold = True


class Titulo(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.font_size = 24
        self.bold = True
        self.color = (1, 1, 1, 1)