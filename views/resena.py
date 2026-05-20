from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.clock import Clock
import firebase_config as fb
import session
from datetime import datetime


class ResenaScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._puntaje_sel = 5

    def on_enter(self):
        self._puntaje_sel = 5
        self._render_estrellas()
        self.ids.input_comentario.text = ""

        # Obtener datos de la consulta de Firebase
        consulta = fb.obtener_consulta(session.current_consulta_id)
        abogado_email = consulta.get('abogado_email', '') if consulta else ''

        nombre_corto = abogado_email.split("@")[0] if abogado_email else ""
        self.ids.lbl_abogado_resena.text = f"Abogado: {nombre_corto}"

    def _render_estrellas(self):
        box = self.ids.estrellas_box
        box.clear_widgets()

        for i in range(1, 6):
            seleccionado = i <= self._puntaje_sel
            btn = Button(
                text=str(i),
                bold=True,
                font_size="22sp",
                background_normal="",
                background_down="",
                background_color=(
                    (0.99, 0.84, 0.00, 1) if seleccionado else (0.15, 0.17, 0.30, 1)
                ),
                color=(
                    (0.00, 0.02, 0.12, 1) if seleccionado else (0.80, 0.82, 0.90, 1)
                ),
            )
            btn.bind(on_release=lambda x, v=i: self._set_puntaje(v))
            box.add_widget(btn)

    def _set_puntaje(self, val):
        self._puntaje_sel = val
        self._render_estrellas()

    def enviar_resena(self):
        consulta = fb.obtener_consulta(session.current_consulta_id)
        if not consulta:
            self.manager.current = "historial"
            return

        abogado_email = consulta.get('abogado_email', '')
        cliente_email = consulta.get('cliente_email', '')
        comentario = self.ids.input_comentario.text.strip()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

        try:
            fb.guardar_resena(
                session.current_consulta_id,
                abogado_email,
                cliente_email,
                self._puntaje_sel,
                comentario
            )
            print("RESENA GUARDADA:", self._puntaje_sel, comentario)
        except Exception as e:
            print("ERROR RESENA:", e)

        self.manager.current = "historial"

    def omitir(self):
        self.manager.current = "historial"