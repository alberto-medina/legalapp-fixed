from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
import firebase_config as fb
import session


class VerificationScreen(Screen):

    def on_enter(self):
        if session.pending_email:
            self.ids.info_label.text = f"Se envió un código a:\n{session.pending_email}\n\nIngresá el código de 6 dígitos:"
        self.ids.codigo.text = ""
        self.ids.error.text = ""

    def verificar_codigo(self):
        codigo = self.ids.codigo.text.strip()

        if not codigo:
            self.ids.error.text = "Ingresá el código"
            return

        if len(codigo) != 6 or not codigo.isdigit():
            self.ids.error.text = "El código debe tener 6 dígitos numéricos"
            return

        uid = session.pending_uid
        if not uid:
            self.ids.error.text = "Error de sesión. Volvé a registrarte."
            return

        ok, msg = fb.verificar_email_con_codigo(uid, codigo)

        if ok:
            self.ids.error.color = (0.18, 0.80, 0.44, 1)
            self.ids.error.text = f"✅ {msg}"
            session.pending_uid = None
            session.pending_email = None
            self._mostrar_exito()
            Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'login'), 3)
        else:
            self.ids.error.color = (0.90, 0.25, 0.25, 1)
            self.ids.error.text = f"❌ {msg}"

    def reenviar_codigo(self):
        uid = session.pending_uid
        email = session.pending_email

        if not uid or not email:
            self.ids.error.text = "Error de sesión. Volvé a registrarte."
            return

        ok, codigo = fb.reenviar_codigo_verificacion(email, uid)

        if ok:
            self.ids.error.color = (0.2, 0.6, 0.9, 1)
            self.ids.error.text = "📧 Nuevo código enviado. Revisá tu consola/email."
        else:
            self.ids.error.text = "❌ No se pudo reenviar el código"

    def ir_a_login(self):
        session.pending_uid = None
        session.pending_email = None
        self.manager.current = 'login'

    def _mostrar_exito(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        lbl = Label(
            text='✅ Email verificado correctamente!\n\nYa podés iniciar sesión.',
            color=(0.18, 0.80, 0.44, 1)
        )
        btn = Button(text='OK', size_hint_y=None, height=50)
        layout.add_widget(lbl)
        layout.add_widget(btn)
        popup = Popup(
            title='Verificación Completa',
            content=layout,
            size_hint=(0.8, 0.4),
            auto_dismiss=False
        )

        def cerrar(instance):
            popup.dismiss()

        btn.bind(on_release=cerrar)
        popup.open()