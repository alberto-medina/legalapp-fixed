from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.utils import platform
import threading

import supabase_config as fb
import session
from views.form_keyboard import FormKeyboardMixin


class LoginScreen(FormKeyboardMixin, Screen):

    # El formulario de login es corto y ya entra completo arriba del
    # teclado (padding con app.keyboard_height en login.kv) -- no hace
    # falta el scroll automatico al campo activo, que solo genera un
    # salto visible al cambiar de email a contrasena sin necesidad real.
    _form_scroll_habilitado = False

    _toques_titulo = 0
    _ultimo_toque = 0
    _login_en_proceso = False
    _email_next_bound = False
    _huella_en_progreso = False
    _huella_cancelada = False
    _email_focus_bound = False

    def on_enter(self):
        self._toques_titulo = 0
        self._ultimo_toque = 0
        self._login_en_proceso = False
        self._huella_cancelada = False
        self._setup_form_keyboard("login_scroll")

        self.ids.error.text = ""

        # Prellenar con las credenciales recordadas de un login anterior
        # (independiente del token de sesion -- esto sobrevive a un logout
        # a proposito, ver session.guardar_credenciales). Solo si el campo
        # esta vacio, para no pisar algo que el usuario ya este escribiendo.
        if not self.ids.email.text and not self.ids.password.text:
            email_guardado = session.cargar_email_guardado()
            if email_guardado:
                self.ids.email.text = email_guardado

                # Si ya hay una sesion COMPLETA guardada en disco (el
                # usuario seguia logueado y Android mato el proceso, p.ej.
                # a mitad de un pago con MercadoPago), no hay que disparar
                # el login con huella aca -- main.py._restaurar_sesion()
                # ya la lee y redirige solo a la pantalla correcta
                # (dashboard, pago_mp, etc). Sin este chequeo se ve pasar
                # un flash por dashboard antes de llegar a la pantalla
                # real, porque el login con huella termina antes y manda a
                # dashboard por su cuenta (confirmado en pruebas
                # 27/09/2026). El huella-login solo tiene sentido cuando
                # el usuario cerro sesion a proposito, caso en el que no
                # queda current_user guardado.
                session.cargar()

                if session.current_user:
                    pass
                elif session.hay_password_con_huella():
                    # La contrasena esta cifrada -- no se puede prellenar
                    # directo, hace falta la huella para descifrarla. Se
                    # dispara el prompt con una demora chica para que la
                    # pantalla ya este armada cuando aparezca.
                    Clock.schedule_once(lambda dt: self._intentar_login_con_huella(), 0.3)
                else:
                    self.ids.password.text = session.cargar_password_plano()

        if 'titulo_app' in self.ids:
            self.ids.titulo_app.bind(on_touch_down=self._on_titulo_touch)

        # El email queda arriba del scroll y la contrasena justo debajo:
        # con el teclado abierto tapando la mitad de la pantalla, la
        # contrasena quedaba oculta y habia que cerrar el teclado para
        # verla. Al validar el email (Enter/Siguiente), saltamos el foco
        # directo a contrasena para que se dispare el mismo scroll-a-campo-
        # activo pero sobre ese campo.
        if not self._email_next_bound and 'email' in self.ids and 'password' in self.ids:
            self.ids.email.bind(on_text_validate=self._ir_a_password)
            self._email_next_bound = True

        # El email es el campo mas arriba de la pantalla: ya esta visible
        # sin que haga falta scrollear cuando aparece el teclado (en la 133
        # queda quieta). FormKeyboardMixin igual programa un scroll para
        # cualquier campo que reciba foco (ver _on_form_input_focus); se
        # cancela ese scroll en el frame siguiente, mismo mecanismo que ya
        # se usa para la huella en contrasena.
        if not self._email_focus_bound and 'email' in self.ids:
            self.ids.email.bind(focus=self._on_email_focus)
            self._email_focus_bound = True

    def on_leave(self):
        self._teardown_form_keyboard()

    def _on_password_focus(self, widget, tiene_foco):
        # FIX: antes, cada vez que se tocaba el campo vacio se volvia a
        # disparar la huella -- si la cancelabas porque queria escribir a
        # mano, tocar el campo para escribir la relanzaba de nuevo,
        # atrapando al usuario en un loop sin poder llegar nunca al
        # teclado. Ahora el reintento automatico solo pasa una vez; despues
        # de cancelar, tocar el campo abre el teclado normal.
        if not tiene_foco or widget.text or self._huella_en_progreso:
            return
        if self._huella_cancelada:
            return
        if session.hay_password_con_huella():
            self._intentar_login_con_huella()
            # FIX: el prompt de huella es un dialogo nativo de Android, no
            # el teclado -- Kivy no se entera de que no hay teclado real
            # abierto y de todas formas programa un scroll (ver
            # FormKeyboardMixin._on_form_input_focus, ligado a este mismo
            # campo). Sin esto la pantalla se corria/bajaba sola cada vez
            # que aparecia la huella, sin ningun teclado que justifique el
            # movimiento (en la 133 esto no pasa, la pantalla queda quieta).
            # Se limpia el input activo en el frame siguiente -- despues de
            # que ambos manejadores de foco ya corrieron, pero antes de que
            # el scroll programado (con demora de 0.15s) llegue a ejecutarse.
            Clock.schedule_once(lambda dt: setattr(self, "_active_input", None), 0)

    def login_con_google(self):
        if self._login_en_proceso:
            return

        import google_signin
        if not google_signin.disponible():
            self.ids.error.color = (0.90, 0.25, 0.25, 1)
            self.ids.error.text = "Google Sign-In no disponible en este dispositivo"
            return

        self._login_en_proceso = True
        self.ids.error.color = (0.35, 0.38, 0.50, 1)
        self.ids.error.text = "Conectando con Google..."
        google_signin.iniciar_login(self._on_google_resultado)

    def _on_google_resultado(self, id_token, email, nombre):
        if not id_token:
            self._login_en_proceso = False
            self.ids.error.text = ""
            return

        self.ids.error.text = "Ingresando..."

        def _worker():
            try:
                ok, user_data, error = fb.login_con_google(id_token, nombre)
                Clock.schedule_once(
                    lambda dt, ok=ok, data=user_data, err=error, mail=email: self._post_login(ok, data, err, mail, es_google=True),
                    0
                )
            except Exception as e:
                Clock.schedule_once(lambda dt, err=str(e): self._login_fallido_inesperado(err), 0)

        threading.Thread(target=_worker, daemon=True).start()

    def _intentar_login_con_huella(self):
        self._huella_en_progreso = True
        session.cargar_password_con_huella(self._on_password_con_huella)

    def _on_password_con_huella(self, password):
        # password es None si el usuario cancelo, eligio "Usar contrasena",
        # o cualquier error -- en todos esos casos se deja el campo vacio
        # para que escriba a mano, sin mensaje de error (no fue un intento
        # fallido de login, fue simplemente no usar la huella).
        self._huella_en_progreso = False
        if password:
            self.ids.password.text = password
            self.login()
        else:
            self._huella_cancelada = True

    def _ir_a_password(self, widget):
        self.ids.password.focus = True

    def _on_email_focus(self, widget, tiene_foco):
        if tiene_foco:
            Clock.schedule_once(lambda dt: setattr(self, "_active_input", None), 0)

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
        # Antes esto tenia un codigo fijo ("LegalAdmin2024") escrito en este
        # archivo como atajo alternativo. Ese codigo viaja adentro del APK y
        # cualquiera que lo descompile puede leerlo, asi que se saco: la
        # unica forma de entrar al panel de administrador es haber logueado
        # con una cuenta que tenga rol='admin' en Supabase (asignado a mano
        # desde el SQL Editor, nunca desde la app).
        if session.current_user and session.current_user.get('rol') == 'admin':
            self.manager.current = 'admin_panel'
            return

        self.ids.error.text = 'Esta cuenta no tiene permisos de administrador.'

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

    def _post_login(self, ok, user_data, error, email, es_google=False):
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
                # Un login con Google no tiene contrasena escrita a mano --
                # no hay nada valido para guardar/cifrar aca. Se deja
                # intacto lo que ya haya guardado de un login anterior con
                # email/contrasena.
                if not es_google:
                    session.guardar_credenciales(email, self.ids.password.text.strip())

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

    def ir_registro_abogado(self):
        self.manager.current = 'register_abogado'

    def recuperar_password(self):
        """Muestra popup para recuperar contrasena via email."""
        from kivy.uix.boxlayout import BoxLayout as _BL
        from kivy.uix.label import Label as _Lbl
        from kivy.metrics import dp as _dp
        from views.popup_estilo import popup_estilizado, input_estilizado, boton_estilizado

        layout = _BL(orientation='vertical', spacing=_dp(12))

        lbl_info = _Lbl(
            text='Ingresa tu email para recibir un link de restablecimiento.',
            halign='center',
            font_size='13sp',
            color=(0.35, 0.38, 0.50, 1),
            size_hint_y=None,
            height=_dp(48),
        )
        lbl_info.bind(size=lambda s, *_: setattr(s, 'text_size', s.size))

        email_prefill = self.ids.email.text.strip().lower()
        txt_email = input_estilizado(hint_text='tu@email.com', text=email_prefill, height=_dp(46))

        lbl_resultado = _Lbl(
            text='',
            halign='center',
            font_size='12sp',
            color=(0.18, 0.80, 0.44, 1),
            size_hint_y=None,
            height=_dp(20),
        )
        lbl_resultado.bind(size=lambda s, *_: setattr(s, 'text_size', s.size))

        btn_enviar = boton_estilizado(text='Enviar link de recuperacion', height=_dp(50))

        btn_cerrar = boton_estilizado(
            text='Cancelar',
            height=_dp(38),
            font_size='13sp',
            fill_color=(0, 0, 0, 0),
            color=(0.50, 0.47, 0.58, 1),
        )

        layout.add_widget(lbl_info)
        layout.add_widget(txt_email)
        layout.add_widget(lbl_resultado)
        layout.add_widget(btn_enviar)
        layout.add_widget(btn_cerrar)

        popup = popup_estilizado('Recuperar contrasena', layout, size_hint=(0.88, None), height=_dp(380))

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
