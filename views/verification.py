from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

import supabase_config as fb
import session


class VerificationScreen(Screen):

    _verificando = False

    def on_enter(self):

        self._verificando = False

        if session.pending_email:

            self.ids.info_label.text = (
                f"Se envió un código a:\n"
                f"{session.pending_email}\n\n"
                f"Ingresá el código de 6 dígitos:"
            )

        self.ids.codigo.text = ""
        self.ids.error.text = ""

    def verificar_codigo(self):

        if self._verificando:
            return

        self._verificando = True

        codigo = self.ids.codigo.text.strip()

        self.ids.error.color = (0.90, 0.25, 0.25, 1)

        if not codigo:

            self.ids.error.text = "Ingresá el código"
            self._verificando = False
            return

        if len(codigo) != 6 or not codigo.isdigit():

            self.ids.error.text = (
                "El código debe tener 6 dígitos"
            )

            self._verificando = False
            return

        uid = session.pending_uid

        if not uid:

            self.ids.error.text = (
                "Sesión inválida. Registrate nuevamente."
            )

            self._verificando = False
            return

        try:

            ok, msg = fb.verificar_email_con_codigo(
                uid,
                codigo
            )

            if ok:

                self.ids.error.color = (
                    0.18,
                    0.80,
                    0.44,
                    1
                )

                self.ids.error.text = f"✅ {msg}"

                session.pending_uid = None
                session.pending_email = None

                self._mostrar_exito()

                Clock.schedule_once(
                    lambda dt: setattr(
                        self.manager,
                        'current',
                        'login'
                    ),
                    2.5
                )

            else:

                self.ids.error.text = (
                    msg or
                    "Código inválido"
                )

        except Exception as e:

            print(f"ERROR VERIFICACION: {e}")

            self.ids.error.text = (
                "Error verificando código"
            )

        self._verificando = False

    def reenviar_codigo(self):

        uid = session.pending_uid
        email = session.pending_email

        if not uid or not email:

            self.ids.error.text = (
                "Sesión inválida"
            )

            return

        try:

            ok, codigo = fb.reenviar_codigo_verificacion(
                email,
                uid
            )

            if ok:

                self.ids.error.color = (
                    0.2,
                    0.6,
                    0.9,
                    1
                )

                self.ids.error.text = (
                    "📧 Nuevo código enviado"
                )

            else:

                self.ids.error.color = (
                    0.90,
                    0.25,
                    0.25,
                    1
                )

                self.ids.error.text = (
                    "No se pudo reenviar"
                )

        except Exception as e:

            print(f"ERROR REENVIO: {e}")

            self.ids.error.text = (
                "Error reenviando código"
            )

    def ir_a_login(self):

        session.pending_uid = None
        session.pending_email = None

        self.manager.current = 'login'

    def _mostrar_exito(self):

        layout = BoxLayout(
            orientation='vertical',
            padding=20,
            spacing=10
        )

        lbl = Label(
            text='✅ Email verificado correctamente',
            color=(0.18, 0.80, 0.44, 1)
        )

        btn = Button(
            text='OK',
            size_hint_y=None,
            height=50
        )

        layout.add_widget(lbl)
        layout.add_widget(btn)

        popup = Popup(
            title='Verificación Completa',
            content=layout,
            size_hint=(0.8, 0.4),
            auto_dismiss=False
        )

        btn.bind(
            on_release=lambda x: popup.dismiss()
        )

        popup.open()