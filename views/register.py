from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from datetime import datetime

import supabase_config as fb
import session


class RegisterScreen(Screen):

    _registro_en_proceso = False

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
                ok_codigo, codigo = fb.enviar_codigo_verificacion(email, uid)

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

    def limpiar_campos(self):
        self.ids.username.text = ""
        self.ids.email.text = ""
        self.ids.dni.text = ""
        self.ids.telefono.text = ""
        self.ids.direccion.text = ""
        self.ids.password.text = ""
        self.ids.password_confirm.text = ""

    def go_back(self):
        self.manager.current = 'login'