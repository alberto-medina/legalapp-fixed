from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.utils import platform

import supabase_config as fb
import session


class LoginScreen(Screen):

    _toques_titulo = 0
    _ultimo_toque = 0
    _login_en_proceso = False

    def on_enter(self):
        self._toques_titulo = 0
        self._ultimo_toque = 0
        self._login_en_proceso = False

        self.ids.error.text = ""

        if 'titulo_app' in self.ids:
            self.ids.titulo_app.bind(on_touch_down=self._on_titulo_touch)

    def _on_titulo_touch(self, widget, touch):
        if widget.collide_point(*touch.pos):
            from time import time

            ahora = time()

            if ahora - self._ultimo_toque > 2:
                self._toques_titulo = 0

            self._toques_titulo += 1
            self._ultimo_toque = ahora

            if self._toques_titulo >= 5:
                self._toques_titulo = 0
                self._acceder_admin()
                return True

        return False

    def _acceder_admin(self):

        if session.current_user and session.current_user.get('rol') == 'admin':
            self.manager.current = 'admin_panel'
            return

        self._mostrar_login_admin()

    def _mostrar_login_admin(self):

        layout = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=10
        )

        lbl = Label(
            text='Acceso Admin\nIngrese código secreto:'
        )

        txt = TextInput(
            password=True,
            multiline=False,
            hint_text='Código admin'
        )

        btn = Button(
            text='Acceder',
            size_hint_y=None,
            height=50
        )

        layout.add_widget(lbl)
        layout.add_widget(txt)
        layout.add_widget(btn)

        popup = Popup(
            title='Panel Admin',
            content=layout,
            size_hint=(0.8, 0.4)
        )

        def verificar_codigo(instance):

            codigo = txt.text.strip()

            if codigo == 'LegalAdmin2024':
                popup.dismiss()
                self.manager.current = 'admin_panel'
            else:
                lbl.text = 'Código incorrecto'
                lbl.color = (0.9, 0.2, 0.2, 1)

        btn.bind(on_release=verificar_codigo)
        txt.bind(on_text_validate=verificar_codigo)

        popup.open()

    def login(self):

        if self._login_en_proceso:
            return

        self._login_en_proceso = True

        email = self.ids.email.text.strip().lower()
        password = self.ids.password.text.strip()

        self.ids.error.color = (0.90, 0.25, 0.25, 1)
        self.ids.error.text = ""

        if not email or not password:
            self.ids.error.text = "Completa email y contraseña"
            self._login_en_proceso = False
            return

        try:

            ok, user_data, error = fb.login_usuario(email, password)

            if ok and user_data:

                rol = user_data.get('rol', '')
                email_verified = user_data.get('email_verified', False)

                if rol == 'cliente' and not email_verified:

                    session.pending_uid = user_data.get('uid')
                    session.pending_email = user_data.get('email')

                    self.ids.error.text = (
                        "Tu email todavía no está verificado."
                    )

                    Clock.schedule_once(
                        lambda dt: setattr(
                            self.manager,
                            'current',
                            'verification'
                        ),
                        1.5
                    )

                    self._login_en_proceso = False
                    return

                session.current_user = user_data

                self.ids.email.text = ""
                self.ids.password.text = ""

                if platform == 'android':
                    try:
                        from fcm_service import obtener_fcm_token
                        Clock.schedule_once(
                            lambda dt: obtener_fcm_token(),
                            2
                        )
                    except Exception as e:
                        print(f"FCM error: {e}")

                self._login_en_proceso = False

                if rol == "abogado":
                    self.manager.current = "abogado_panel"
                else:
                    self.manager.current = "dashboard"

            else:

                self.ids.error.text = (
                    error or
                    "Email o contraseña incorrectos"
                )

                self._login_en_proceso = False

        except Exception as e:

            print(f"ERROR LOGIN: {e}")

            self.ids.error.text = (
                "Error inesperado al iniciar sesión"
            )

            self._login_en_proceso = False

    def go_register(self):
        self.manager.current = 'register'