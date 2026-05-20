from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
import firebase_config as fb
import session

ESTADOS_FILTRO = ["Todos", "pagado", "videollamada", "finalizado"]

TIPO_COLOR = {
    "chat":    (0.18, 0.80, 0.44, 1),
    "video":   (0.18, 0.55, 0.85, 1),
    "urgente": (0.91, 0.30, 0.24, 1),
}

ESTADO_COLOR = {
    "pagado":        (0.85, 0.62, 0.05, 1),
    "videollamada":  (0.18, 0.55, 0.85, 1),
    "finalizado":    (0.18, 0.80, 0.44, 1),
}


class HistorialScreen(Screen):

    _filtro = "Todos"

    def on_enter(self):
        self.ids.filtro_spinner.values = ESTADOS_FILTRO
        self.ids.filtro_spinner.text = self._filtro
        self.cargar_historial()

    def aplicar_filtro(self, valor):
        self._filtro = valor
        self.cargar_historial()

    def cargar_historial(self):
        self.ids.lista.clear_widgets()

        if not session.current_user:
            return

        uid = session.current_user.get('uid')

        consultas = fb.obtener_consultas_usuario(uid, 'cliente')

        if self._filtro != "Todos":
            consultas = [(cid, c) for cid, c in consultas if c.get('estado') == self._filtro]

        if not consultas:
            self.ids.lista.add_widget(Label(
                text="No hay consultas",
                color=(0.50, 0.55, 0.65, 1),
                font_size="15sp",
                size_hint_y=None,
                height=dp(70),
            ))
            return

        for cid, cdata in consultas:
            abogado_email = cdata.get('abogado_email', '')
            estado = cdata.get('estado', 'pagado')
            tipo = cdata.get('tipo_servicio', 'chat')

            self._add_card(cid, abogado_email, estado, tipo)

    def _add_card(self, cid, abogado, estado, tipo):
        card = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(96),
            spacing=dp(12),
            padding=[dp(14), dp(12)],
        )

        with card.canvas.before:
            Color(rgba=(1, 1, 1, 1))
            card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(18)])

        card.bind(
            pos=lambda w, v: setattr(w._bg, 'pos', v),
            size=lambda w, v: setattr(w._bg, 'size', v),
        )

        tipo_box = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(72))
        tipo_lbl = Label(
            text=tipo.upper(),
            font_size="12sp",
            bold=True,
            color=TIPO_COLOR.get(tipo, (0.5, 0.5, 0.5, 1)),
            halign="center",
            valign="middle",
        )
        tipo_lbl.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
        tipo_box.add_widget(tipo_lbl)

        info = BoxLayout(orientation="vertical", spacing=dp(4))

        abogado_lbl = Label(
            text=abogado,
            font_size="15sp",
            bold=True,
            color=(0.10, 0.12, 0.18, 1),
            halign="left",
            valign="middle",
        )
        abogado_lbl.bind(size=lambda s, *_: setattr(s, "text_size", s.size))

        estado_lbl = Label(
            text=estado.upper(),
            font_size="12sp",
            bold=True,
            color=ESTADO_COLOR.get(estado, (0.55, 0.58, 0.65, 1)),
            halign="left",
            valign="middle",
        )
        estado_lbl.bind(size=lambda s, *_: setattr(s, "text_size", s.size))

        info.add_widget(abogado_lbl)
        info.add_widget(estado_lbl)

        btns = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(90), spacing=dp(6))

        btn_chat = Button(
            text="Abrir",
            font_size="13sp",
            bold=True,
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=(0.24, 0.17, 0.55, 1),
            color=(1, 1, 1, 1),
        )
        btn_chat.bind(on_release=lambda x, c=cid: self.abrir_chat(c))
        btns.add_widget(btn_chat)

        if estado == "finalizado" and not fb.tiene_resena(cid):
            btn_resena = Button(
                text="Reseña",
                font_size="12sp",
                bold=True,
                size_hint_y=None,
                height=dp(36),
                background_normal="",
                background_color=(0.91, 0.30, 0.24, 1),
                color=(1, 1, 1, 1),
            )
            btn_resena.bind(on_release=lambda x, c=cid: self.ir_resena(c))
            btns.add_widget(btn_resena)

        card.add_widget(tipo_box)
        card.add_widget(info)
        card.add_widget(btns)

        self.ids.lista.add_widget(card)

    def abrir_chat(self, cid):
        session.current_consulta_id = cid
        self.manager.current = "chat"

    def ir_resena(self, cid):
        session.current_consulta_id = cid
        self.manager.current = "resena"

    def volver(self):
        self.manager.current = "dashboard"