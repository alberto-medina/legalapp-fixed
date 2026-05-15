from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle
from database import get_connection, solicitar_retiro
import session

ESTADOS = ["disponible", "guardia", "ocupado"]
ESTADO_CFG = {
    "disponible": {"label": "  DISPONIBLE  ", "bg": (0.10, 0.72, 0.38, 1), "text": (1,1,1,1)},
    "guardia":    {"label": "  EN GUARDIA  ", "bg": (0.85, 0.62, 0.05, 1), "text": (1,1,1,1)},
    "ocupado":    {"label": "  OCUPADO     ", "bg": (0.85, 0.18, 0.18, 1), "text": (1,1,1,1)},
}

TIPO_COLOR = {
    "chat":    (0.18, 0.80, 0.44, 1),
    "video":   (0.10, 0.55, 0.85, 1),
    "urgente": (0.91, 0.30, 0.24, 1),
}


class AbogadoPanelScreen(Screen):

    def on_enter(self):
        user = session.current_user
        if user:
            self.ids.lbl_nombre_abogado.text = user[1] or user[2]

        self.cargar_datos()
        self._actualizar_btn_estado()

        # FIX ANDROID: refresca layout para evitar superposición
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self._refresh_layout(), 0.1)

    def _refresh_layout(self):
        # Fuerza redraw (soluciona botones tapados en Android)
        for child in self.children:
            child.do_layout()

    def _get_estado_actual(self):
        user = session.current_user
        if not user:
            return "disponible"

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT estado_abogado FROM users WHERE email=?", (user[2],))
        row = c.fetchone()
        conn.close()

        est = row[0] if row and row[0] else "disponible"
        return est if est in ESTADOS else "disponible"

    def _actualizar_btn_estado(self):
        estado = self._get_estado_actual()
        cfg = ESTADO_CFG[estado]

        self.ids.btn_estado.text = cfg["label"]
        self.ids.btn_estado.background_color = cfg["bg"]
        self.ids.btn_estado.color = cfg["text"]

    def cambiar_estado(self):
        user = session.current_user
        if not user:
            return

        actual = self._get_estado_actual()
        nuevo = ESTADOS[(ESTADOS.index(actual) + 1) % len(ESTADOS)]

        conn = get_connection()
        c = conn.cursor()
        c.execute("UPDATE users SET estado_abogado=? WHERE email=?", (nuevo, user[2]))
        conn.commit()
        conn.close()

        self._actualizar_btn_estado()

    def cargar_datos(self):
        self.ids.lista_consultas.clear_widgets()

        user = session.current_user
        if not user:
            return

        email = user[2]

        conn = get_connection()
        c = conn.cursor()

        # saldo
        c.execute("SELECT saldo FROM users WHERE email=?", (email,))
        saldo_row = c.fetchone()
        saldo = saldo_row[0] if saldo_row and saldo_row[0] else 0.0

        # total consultas
        c.execute("SELECT COUNT(*) FROM consultas WHERE abogado=?", (email,))
        total = c.fetchone()[0]

        self.ids.lbl_consultas.text = str(total)
        self.ids.lbl_honorarios.text = f"${saldo:,.0f}"

        # consultas
        c.execute("""
            SELECT id, user_email, estado, tipo_servicio
            FROM consultas WHERE abogado=? ORDER BY id DESC
        """, (email,))
        consultas = c.fetchall()

        conn.close()

        if not consultas:
            self.ids.lista_consultas.add_widget(Label(
                text="No hay consultas aun",
                color=(0.50, 0.55, 0.65, 1),
                size_hint_y=None,
                height=60,
            ))
            return

        for cid, cliente, estado, tipo in consultas:
            card = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=80,
                spacing=10,
                padding=[16, 12],
            )

            with card.canvas.before:
                Color(rgba=(1, 1, 1, 1))
                card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[14])

            card.bind(
                pos=lambda w, v: setattr(w._bg, 'pos', v),
                size=lambda w, v: setattr(w._bg, 'size', v),
            )

            tipo_lbl = Label(
                text=(tipo or "?").upper(),
                size_hint_x=None,
                width=64,
                bold=True,
                font_size=13,
                color=TIPO_COLOR.get(tipo, (0.5, 0.5, 0.5, 1)),
            )

            info = BoxLayout(orientation="vertical")

            info.add_widget(Label(
                text=cliente,
                font_size=15,
                bold=True,
                color=(0.08, 0.12, 0.28, 1),
            ))

            estado_color = (0.10, 0.72, 0.38, 1) if estado == "finalizado" else (0.85, 0.62, 0.05, 1)

            info.add_widget(Label(
                text=estado.upper(),
                font_size=12,
                color=estado_color,
            ))

            btn = Button(
                text="Abrir",
                size_hint_x=None,
                width=72,
                bold=True,
                font_size=14,
                background_normal="",
                background_color=(0.10, 0.12, 0.18, 1),
                color=(1, 1, 1, 1),
            )

            btn.bind(on_release=lambda x, c=cid: self.abrir_chat(c))

            card.add_widget(tipo_lbl)
            card.add_widget(info)
            card.add_widget(btn)

            self.ids.lista_consultas.add_widget(card)

    def abrir_chat(self, consulta_id):
        session.current_consulta_id = consulta_id
        self.manager.current = "chat"

    def ir_perfil(self):
        self.manager.current = "perfil"

    def logout(self):
        session.current_user = None
        self.manager.current = "login"

    def solicitar_retiro_popup(self):
        user = session.current_user
        if not user:
            return

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT saldo, cuenta_bancaria FROM users WHERE email=?", (user[2],))
        row = c.fetchone()
        conn.close()

        saldo = row[0] if row and row[0] else 0.0
        cuenta = row[1] if row and row[1] else ""

        # =================================================
        # VALIDACION: SIN CUENTA BANCARIA
        # =================================================
        if not cuenta:
            content = BoxLayout(orientation="vertical", padding=20, spacing=12)

            content.add_widget(Label(
                text="Retiro no disponible",
                font_size=16,
                bold=True,
                color=(0.85, 0.18, 0.18, 1),
                size_hint_y=None,
                height=24,
            ))

            content.add_widget(Label(
                text="Falta CBU / Alias",
                font_size=14,
                bold=True,
                color=(0.85, 0.30, 0.30, 1),
                size_hint_y=None,
                height=20,
            ))

            content.add_widget(Label(
                text="Debes cargar tu cuenta bancaria en Perfil antes de retirar.",
                font_size=13,
                color=(0.55, 0.58, 0.65, 1),
                size_hint_y=None,
                height=40,
                halign="center",
                valign="middle",
                text_size=(None, None),
            ))

            popup = Popup(
                title="",
                content=content,
                size_hint=(0.85, None),
                height=240,
                auto_dismiss=False,
            )

            btn_ir = Button(
                text="Ir a Perfil",
                size_hint_y=None,
                height=48,
                bold=True,
                font_size=15,
                background_normal="",
                background_color=(0.24, 0.17, 0.55, 1),
                color=(1, 1, 1, 1),
            )
            btn_ir.bind(on_release=lambda x: (popup.dismiss(), self.ir_perfil()))

            btn_cancel = Button(
                text="Cancelar",
                size_hint_y=None,
                height=40,
                font_size=13,
                background_normal="",
                background_color=(0, 0, 0, 0),
                color=(0.55, 0.58, 0.65, 1),
            )
            btn_cancel.bind(on_release=popup.dismiss)

            content.add_widget(btn_ir)
            content.add_widget(btn_cancel)

            popup.open()
            return

        # =================================================
        # RETIRO NORMAL
        # =================================================
        content = BoxLayout(orientation="vertical", padding=20, spacing=14)

        content.add_widget(Label(
            text=f"Saldo disponible: ${saldo:,.0f}",
            font_size=17,
            bold=True,
        ))

        content.add_widget(Label(
            text=f"Destino: {cuenta}",
            font_size=13,
        ))

        monto_input = TextInput(
            hint_text="Monto a retirar",
            multiline=False,
            input_filter="float",
        )
        content.add_widget(monto_input)

        lbl_resultado = Label(text="")
        content.add_widget(lbl_resultado)

        popup = Popup(
            title="Solicitar retiro",
            content=content,
            size_hint=(0.9, None),
            height=360,
        )

        def confirmar(instance):
            txt = monto_input.text.strip()

            if not txt:
                lbl_resultado.text = "Ingresa un monto"
                return

            try:
                monto = float(txt)
            except:
                lbl_resultado.text = "Monto invalido"
                return

            ok, msg, _ = solicitar_retiro(user[2], monto, cuenta)
            lbl_resultado.text = msg

            if ok:
                self.cargar_datos()

        btn_ok = Button(text="Confirmar")
        btn_ok.bind(on_release=confirmar)

        btn_cancel = Button(text="Cancelar")
        btn_cancel.bind(on_release=popup.dismiss)

        content.add_widget(btn_ok)
        content.add_widget(btn_cancel)

        popup.open()