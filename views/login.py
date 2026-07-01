from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.utils import platform
from kivy.core.window import Window
import threading

import supabase_config as fb
import session
from views.form_keyboard import FormKeyboardMixin


class LoginScreen(FormKeyboardMixin, Screen):

    _toques_titulo = 0
    _ultimo_toque = 0
    _login_en_proceso = False
    _prev_softinput_mode = None

    def on_enter(self):
        self._toques_titulo = 0
        self._ultimo_toque = 0
        self._login_en_proceso = False
        self._setup_form_keyboard("login_scroll")
        self._prev_softinput_mode = getattr(Window, "softinput_mode", "below_target")
        Window.softinput_mode = "resize"

        self.ids.error.text = ""

        if 'titulo_app' in self.ids:
            self.ids.titulo_app.bind(on_touch_down=self._on_titulo_touch)

    def on_leave(self):
        try:
            Window.softinput_mode = self._prev_softinput_mode or "below_target"
        except Exception:
            Window.softinput_mode = "below_target"

    def _on_titulo_touch(self, widget, touch):
        if widget.collide_point(*touch.pos):
            from time import time

            ahora = time()

            if ahora - self._ultimo_toque > 2:
                self._toques_titulo = 0

            self._toques_titulo += 1
            self._ultimo_toque = ahora

            if self._toques_titulo >= 7:
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
            text='Acceso Admin\nIngrese codigo secreto:'
        )

        txt = TextInput(
            password=True,
            multiline=False,
            hint_text='Codigo admin'
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
                lbl.text = 'Codigo incorrecto'
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
            self.ids.error.text = "Completa email y contrasena"
            self._login_en_proceso = False
            return

        try:
            self.ids.error.color = (0.35, 0.38, 0.50, 1)
            self.ids.error.text = "Ingresando..."

            def _worker():
                try:
                    ok, user_data, error = fb.login_usuario(email, password)
                    Clock.schedule_once(
                        lambda dt, ok=ok, data=user_data, err=error, mail=email: self._post_login(ok, data, err, mail),
                        0
                    )
                except Exception as e:
                    Clock.schedule_once(lambda dt, err=str(e): self._login_fallido_inesperado(err), 0)

            threading.Thread(target=_worker, daemon=True).start()
            return

        except Exception as e:

            print(f"ERROR LOGIN: {e}")

            self.ids.error.text = (
                "Error inesperado al iniciar sesion"
            )

            self._login_en_proceso = False

    def _post_login(self, ok, user_data, error, email):
        try:
            if ok and user_data:
                id_token = user_data.get('idToken')
                refresh_token = user_data.get('refreshToken')
                if id_token:
                    session.id_token = id_token
                    session.refresh_token = refresh_token
                    session.guardar()

                rol = user_data.get('rol', '')
                email_verificado = user_data.get('email_verified', False)
                suscripcion_activa = user_data.get('suscripcion_activa', False)
                aprobado = user_data.get('aprobado', False)

                if rol == 'abogado' and not email_verificado:
                    session.pending_uid = user_data.get('uid')
                    session.pending_email = user_data.get('email')
                    session.abogado_registrando_uid = user_data.get('uid')
                    session.guardar()

                    if id_token:
                        threading.Thread(
                            target=lambda: fb.enviar_codigo_verificacion(email, user_data.get('uid'), id_token=id_token),
                            daemon=True
                        ).start()

                    self.ids.error.color = (0.2, 0.6, 0.9, 1)
                    self.ids.error.text = "Verifica tu email para continuar..."
                    Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'verification'), 1.5)
                    self._login_en_proceso = False
                    return

                if rol == 'abogado' and email_verificado and not suscripcion_activa:
                    session.current_user = user_data
                    session.pending_uid = None
                    session.pending_email = None
                    session.abogado_registrando_uid = None
                    session.monto_suscripcion = 55000
                    session.guardar()

                    self.ids.error.color = (0.2, 0.6, 0.9, 1)
                    self.ids.error.text = "Completa tu suscripcion..."
                    Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'pago_suscripcion'), 1.5)
                    self._login_en_proceso = False
                    return

                if rol == 'abogado' and email_verificado and suscripcion_activa and not aprobado:
                    session.current_user = None
                    session.pending_uid = None
                    session.pending_email = None
                    session.abogado_registrando_uid = None
                    session.guardar()

                    self.ids.error.color = (0.90, 0.55, 0.10, 1)
                    self.ids.error.text = "Tu cuenta esta pendiente de aprobacion del administrador."
                    self._login_en_proceso = False
                    return

                if rol == 'cliente' and not email_verificado:
                    session.pending_uid = user_data.get('uid')
                    session.pending_email = user_data.get('email')
                    session.guardar()

                    if id_token:
                        threading.Thread(
                            target=lambda: fb.enviar_codigo_verificacion(email, user_data.get('uid'), id_token=id_token),
                            daemon=True
                        ).start()

                    self.ids.error.color = (0.2, 0.6, 0.9, 1)
                    self.ids.error.text = "Verifica tu email para continuar..."
                    Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'verification'), 1.5)
                    self._login_en_proceso = False
                    return

                session.current_user = user_data
                session.pending_uid = None
                session.pending_email = None
                session.abogado_registrando_uid = None
                session.guardar()

                self.ids.email.text = ""
                self.ids.password.text = ""

                if platform == 'android':
                    try:
                        from fcm_service import obtener_fcm_token, guardar_token_en_supabase
                        guardar_token_en_supabase()
                        Clock.schedule_once(lambda dt: obtener_fcm_token(), 2)
                    except Exception as e:
                        print(f"FCM error: {e}")

                self._login_en_proceso = False
                self.manager.current = "abogado_panel" if rol == "abogado" else "dashboard"
                return

            if error and ("verif" in error.lower() or "email" in error.lower()):
                usuario = fb.obtener_usuario_por_email(email)
                if usuario and not usuario.get('email_verified', False):
                    uid = usuario.get('uid')
                    session.pending_uid = uid
                    session.pending_email = email
                    if usuario.get('rol') == 'abogado':
                        session.abogado_registrando_uid = uid
                    session.guardar()

                    self.ids.error.color = (0.2, 0.6, 0.9, 1)
                    self.ids.error.text = "Reenviando verificación por email..."

                    threading.Thread(
                        target=lambda: fb.reenviar_codigo_verificacion(email, uid, id_token=getattr(session, 'id_token', None)),
                        daemon=True
                    ).start()

                    Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'verification'), 1.5)
                    self._login_en_proceso = False
                    return

            self.ids.error.color = (0.90, 0.25, 0.25, 1)
            self.ids.error.text = error or "Email o contrasena incorrectos"
            self._login_en_proceso = False
        except Exception as e:
            self._login_fallido_inesperado(str(e))

    def _login_fallido_inesperado(self, error):
        print(f"ERROR LOGIN: {error}")
        self.ids.error.color = (0.90, 0.25, 0.25, 1)
        self.ids.error.text = "Error inesperado al iniciar sesion"
        self._login_en_proceso = False

    def go_register(self):
        self.manager.current = 'register'

    def recuperar_password(self):
        """Muestra popup para recuperar contrasena via email."""
        from kivy.uix.popup import Popup as _Popup
        from kivy.uix.boxlayout import BoxLayout as _BL
        from kivy.uix.textinput import TextInput as _TI
        from kivy.uix.button import Button as _Btn
        from kivy.uix.label import Label as _Lbl

        layout = _BL(orientation='vertical', padding=16, spacing=12)

        lbl_info = _Lbl(
            text='Ingresa tu email para recibir un link de restablecimiento.',
            halign='center',
            font_size='13sp',
            color=(0.35, 0.38, 0.50, 1),
            size_hint_y=None,
            height=48,
        )
        lbl_info.bind(size=lambda s, *_: setattr(s, 'text_size', s.size))

        email_prefill = self.ids.email.text.strip().lower()
        txt_email = _TI(
            hint_text='tu@email.com',
            text=email_prefill,
            multiline=False,
            size_hint_y=None,
            height=46,
            font_size='15sp',
            background_normal='',
            background_active='',
            background_color=(0.95, 0.94, 0.97, 1),
            foreground_color=(0.10, 0.06, 0.14, 1),
            hint_text_color=(0.60, 0.57, 0.68, 1),
            cursor_color=(0.30, 0.23, 0.67, 1),
            padding=[14, 12],
        )

        lbl_resultado = _Lbl(
            text='',
            halign='center',
            font_size='12sp',
            color=(0.18, 0.80, 0.44, 1),
            size_hint_y=None,
            height=20,
        )
        lbl_resultado.bind(size=lambda s, *_: setattr(s, 'text_size', s.size))

        btn_enviar = _Btn(
            text='Enviar link de recuperacion',
            size_hint_y=None,
            height=50,
            bold=True,
            font_size='15sp',
            background_normal='',
            background_color=(0.30, 0.23, 0.67, 1),
            color=(1, 1, 1, 1),
        )

        btn_cerrar = _Btn(
            text='Cancelar',
            size_hint_y=None,
            height=38,
            font_size='13sp',
            background_normal='',
            background_color=(0, 0, 0, 0),
            color=(0.50, 0.47, 0.58, 1),
        )

        layout.add_widget(lbl_info)
        layout.add_widget(txt_email)
        layout.add_widget(lbl_resultado)
        layout.add_widget(btn_enviar)
        layout.add_widget(btn_cerrar)

        popup = _Popup(
            title='Recuperar contrasena',
            content=layout,
            size_hint=(0.88, None),
            height=300,
            separator_color=(0.30, 0.23, 0.67, 1),
        )

        def _enviar(instance):
            email_val = txt_email.text.strip().lower()
            if not email_val:
                lbl_resultado.color = (0.90, 0.25, 0.25, 1)
                lbl_resultado.text = 'Ingresa tu email'
                return

            btn_enviar.disabled = True
            lbl_resultado.color = (0.55, 0.50, 0.65, 1)
            lbl_resultado.text = 'Enviando...'

            try:
                ok, error = fb.enviar_reset_password(email_val)
                if ok:
                    lbl_resultado.color = (0.18, 0.80, 0.44, 1)
                    lbl_resultado.text = 'Listo. Revisa tu email.'
                    btn_cerrar.text = 'Cerrar'
                else:
                    lbl_resultado.color = (0.90, 0.25, 0.25, 1)
                    lbl_resultado.text = 'Email no encontrado' if error else 'No se pudo enviar'
                    btn_enviar.disabled = False
            except Exception as e:
                lbl_resultado.color = (0.90, 0.25, 0.25, 1)
                lbl_resultado.text = 'Error al enviar. Intenta de nuevo.'
                btn_enviar.disabled = False

        btn_enviar.bind(on_release=_enviar)
        txt_email.bind(on_text_validate=_enviar)
        btn_cerrar.bind(on_release=lambda x: popup.dismiss())

        popup.open()

    def reenviar_codigo(self):
        email = self.ids.email.text.strip().lower()

        if not email:
            self.ids.error.text = "Ingresa tu email primero"
            return

        try:
            usuario = fb.obtener_usuario_por_email(email)
            if not usuario:
                self.ids.error.text = "Email no encontrado"
                return

            if usuario.get('email_verified'):
                self.ids.error.text = "Este email ya esta verificado. Inicia sesion."
                return

            uid = usuario.get('uid')
            id_token = getattr(session, 'id_token', None)

            ok, metodo = fb.reenviar_codigo_verificacion(email, uid, id_token=id_token)

            if ok:
                session.pending_uid = uid
                session.pending_email = email

                if usuario.get('rol') == 'abogado':
                    session.abogado_registrando_uid = uid
                session.guardar()

                self.ids.error.color = (0.18, 0.80, 0.44, 1)
                self.ids.error.text = "Verificación reenviada. Revisa tu email..."

                Clock.schedule_once(
                    lambda dt: setattr(self.manager, 'current', 'verification'),
                    1.5
                )
            else:
                self.ids.error.text = "Error reenviando verificación"

        except Exception as e:
            print(f"ERROR reenviar_codigo: {e}")
            self.ids.error.text = "Error inesperado"
