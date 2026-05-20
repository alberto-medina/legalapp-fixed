from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
import firebase_config as fb
import session


class RegisterScreen(Screen):

    def register(self):
        username = self.ids.username.text.strip()
        email = self.ids.email.text.strip()
        dni = self.ids.dni.text.strip()
        telefono = self.ids.telefono.text.strip()
        direccion = self.ids.direccion.text.strip()
        password = self.ids.password.text.strip()
        password_confirm = self.ids.password_confirm.text.strip()

        self.ids.error.color = (0.90, 0.25, 0.25, 1)

        if not all([username, email, password, password_confirm]):
            self.ids.error.text = "Completa todos los campos obligatorios (*)"
            return

        if len(username) < 3:
            self.ids.error.text = "El nombre debe tener al menos 3 caracteres"
            return

        if password != password_confirm:
            self.ids.error.text = "Las contraseñas no coinciden"
            return

        datos_extra = {
            'dni': dni,
            'direccion': direccion
        }

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
            if ok_codigo:
                session.pending_uid = uid
                session.pending_email = email
                self.ids.error.color = (0.18, 0.80, 0.44, 1)
                self.ids.error.text = "✅ Cuenta creada! Revisá tu email (o consola) para activarla."
                Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'verification'), 2)
            else:
                self.ids.error.color = (0.18, 0.80, 0.44, 1)
                self.ids.error.text = "✅ Cuenta creada! (No se pudo enviar código de verificación)"

            self.limpiar_campos()
        else:
            self.ids.error.text = f"❌ {error or 'Error al crear cuenta'}"

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