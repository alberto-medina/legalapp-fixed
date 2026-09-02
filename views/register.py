from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from datetime import datetime

import supabase_config as fb
import session
from views.form_keyboard import FormKeyboardMixin


class RegisterScreen(FormKeyboardMixin, Screen):

    _registro_en_proceso = False

    def on_enter(self):
        self._setup_form_keyboard("register_scroll")

    def on_leave(self):
        self._teardown_form_keyboard()

    def register(self):

        if self._registro_en_proceso:
            return

        self._registro_en_proceso = True

        username = self.ids.username.text.strip()
        email = self.ids.email.text.strip().lower()
        dni = self.ids.dni.text.strip()
        telefono = self.ids.telefono.text.strip()
        direccion = self.ids.direccion.text.strip()
        password = self.ids.password.text.strip()
        password_confirm = self.ids.password_confirm.text.strip()

        terms_accepted = self.ids.terms_check.active

        self.ids.error.color = (0.90, 0.25, 0.25, 1)
        self.ids.error.text = ""

        if not all([username, email, password, password_confirm]):
            self.ids.error.text = "Completa todos los campos obligatorios (*)"
            self._registro_en_proceso = False
            return

        if len(username) < 3:
            self.ids.error.text = "El nombre debe tener al menos 3 caracteres"
            self._registro_en_proceso = False
            return

        if password != password_confirm:
            self.ids.error.text = "Las contrasenas no coinciden"
            self._registro_en_proceso = False
            return

        if not terms_accepted:
            self.ids.error.text = "Debes aceptar los terminos y privacidad"
            self._registro_en_proceso = False
            return

        # FIX: Verificar si email ya existe pero no verificado
        try:
            usuario_existente = fb.obtener_usuario_por_email(email)

            if usuario_existente:
                uid_existente = usuario_existente.get('uid')
                email_verificado = usuario_existente.get('email_verified', False)

                # Si existe pero no verificó email, reenviar verificación
                if not email_verificado:

                    # Actualizar datos por si cambió algo
                    fb.actualizar_usuario(uid_existente, {
                        'username': username,
                        'telefono': telefono,
                        'dni': dni,
                        'direccion': direccion,
                    })

                    # Reenviar verificación (Firebase o fallback)
                    id_token = getattr(session, 'id_token', None)
                    ok, metodo = fb.reenviar_codigo_verificacion(email, uid_existente, id_token=id_token)

                    session.pending_uid = uid_existente
                    session.pending_email = email

                    self.ids.error.color = (0.2, 0.6, 0.9, 1)
                    self.ids.error.text = "Email ya registrado. Reenviando verificación..."

                    Clock.schedule_once(
                        lambda dt: setattr(self.manager, 'current', 'verification'),
                        1.5
                    )
                    self._registro_en_proceso = False
                    return

                # Si ya existe y está verificado
                else:
                    self.ids.error.text = "Este email ya está registrado. Iniciá sesión."
                    self._registro_en_proceso = False
                    return

        except Exception as e:
            print(f"ERROR check usuario existente: {e}")
            pass

        datos_extra = {
            'dni': dni,
            'direccion': direccion,
            'acepto_terminos': True,
            'fecha_aceptacion': datetime.now().isoformat(),
            'version_terminos': '1.0'
        }

        try:
            ok, uid, error = fb.crear_usuario(
                email=email,
                password=password,
                nombre=username,
                rol="cliente",
                telefono=telefono,
                datos_extra=datos_extra
            )

            if ok:
                # FIX: Obtener id_token Y refresh_token haciendo login con las credenciales recién creadas
                ok_login, auth_data, login_error = fb.login_usuario_auth(email, password)
                id_token = None
                refresh_token = None
                if ok_login:
                    id_token = auth_data.get('idToken')
                    refresh_token = auth_data.get('refreshToken')
                    session.id_token = id_token
                    session.refresh_token = refresh_token
                    session.guardar()

                # Enviar verificación por Firebase (o fallback si no hay id_token)
                ok_codigo, metodo = fb.enviar_codigo_verificacion(email, uid, id_token=id_token)

                session.pending_uid = uid
                session.pending_email = email

                self.ids.error.color = (0.18, 0.80, 0.44, 1)

                if ok_codigo:
                    self.ids.error.text = "Cuenta creada correctamente"
                else:
                    self.ids.error.text = "Cuenta creada. Error enviando email."

                self.limpiar_campos()

                Clock.schedule_once(
                    lambda dt: setattr(self.manager, 'current', 'verification'),
                    1.5
                )

            else:
                self.ids.error.text = error or "Error al crear cuenta"

        except Exception as e:
            print(f"ERROR REGISTER: {e}")
            self.ids.error.text = "Error inesperado al crear cuenta"

        self._registro_en_proceso = False

    def ir_registro_abogado(self):
        self.manager.current = 'register_abogado'

    def registrar_con_google(self):
        # No hay un flujo de alta separado para Google -- login_con_google
        # ya crea la cuenta automaticamente si es la primera vez (ver
        # supabase_config.login_con_google). Se reusa el mismo boton/logica
        # de LoginScreen en vez de duplicar el ruteo post-login (verificar
        # rol, suscripcion, etc.) aca.
        login_screen = self.manager.get_screen('login')
        self.manager.current = 'login'
        Clock.schedule_once(lambda dt: login_screen.login_con_google(), 0.1)

    def limpiar_campos(self):
        self.ids.username.text = ""
        self.ids.email.text = ""
        self.ids.dni.text = ""
        self.ids.telefono.text = ""
        self.ids.direccion.text = ""
        self.ids.password.text = ""
        self.ids.password_confirm.text = ""
        self.ids.terms_check.active = False

    def go_back(self):
        self.manager.current = 'login'

    def volver(self):
        self.manager.current = 'login'
