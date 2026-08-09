from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

import supabase_config as fb
import session
from firebase_auth import refrescar_id_token, obtener_info_usuario


class VerificationScreen(Screen):

    _verificando = False
    _check_event = None

    def on_enter(self):
        self._verificando = False

        if session.pending_email:
            self.ids.info_label.text = (
                f"Te enviamos un email a:\n"
                f"{session.pending_email}\n\n"
                f"Tocá el link del email para verificar tu cuenta.\n"
                f"Después volvé a la app y tocá 'Ya abrí el link'."
            )

        self.ids.codigo.text = ""
        self.ids.error.text = ""

        # Iniciar polling cada 5 segundos
        self._iniciar_polling()

    def on_leave(self):
        if self._check_event:
            self._check_event.cancel()
            self._check_event = None

    def _iniciar_polling(self):
        if self._check_event:
            self._check_event.cancel()
        self._check_event = Clock.schedule_interval(self._chequear_verificacion_firebase, 5)

    def _obtener_id_token_valido(self):
        """
        Obtiene un id_token válido:
        1. Si hay id_token vigente, lo usa
        2. Si expiró, usa refresh_token para obtener uno nuevo
        3. Si no hay refresh_token, devuelve None
        """
        id_token = getattr(session, 'id_token', None)
        refresh_token = getattr(session, 'refresh_token', None)

        # Probar si el id_token actual sirve
        if id_token:
            ok, _, _ = obtener_info_usuario(id_token)
            if ok:
                return id_token

        # Si no sirve, intentar refrescar
        if refresh_token:
            ok, data, error = refrescar_id_token(refresh_token)
            if ok:
                session.id_token = data["id_token"]
                # Firebase a veces devuelve nuevo refresh_token, a veces no
                if data.get("refresh_token"):
                    session.refresh_token = data["refresh_token"]
                session.guardar()
                print(f"✅ Token refrescado exitosamente")
                return session.id_token
            else:
                print(f"❌ Error refrescando token: {error}")

        return None

    def _chequear_verificacion_firebase(self, dt):
        """Consulta Firebase si el email ya está verificado."""
        uid = session.pending_uid
        if not uid:
            return True

        id_token = self._obtener_id_token_valido()
        if not id_token:
            return True  # Seguir polling, aún no hay token válido

        try:
            ok, msg = fb.verificar_email_con_codigo(uid, id_token=id_token)
            if ok:
                # ¡Verificado! Detener polling y redirigir
                self._check_event.cancel()
                self._check_event = None

                self.ids.error.color = (0.18, 0.80, 0.44, 1)
                self.ids.error.text = f"✅ {msg}"

                destino = 'pago_suscripcion' if getattr(session, 'abogado_registrando_uid', None) else 'login'
                session.pending_uid = None
                if destino != 'pago_suscripcion':
                    session.pending_email = None
                session.guardar()

                Clock.schedule_once(
                    lambda dt, d=destino: setattr(self.manager, 'current', d),
                    1.5
                )
                return False  # Detener polling

        except Exception as e:
            print(f"ERROR polling verificación: {e}")

        return True  # Seguir polling

    def verificar_codigo(self):
        """
        Botón 'Ya verifiqué' — fuerza chequeo inmediato en Firebase.
        También acepta código de 6 dígitos como fallback.
        """
        if self._verificando:
            return

        self._verificando = True

        codigo = self.ids.codigo.text.strip()
        uid = session.pending_uid

        self.ids.error.color = (0.90, 0.25, 0.25, 1)

        if not uid:
            self.ids.error.text = "Sesion invalida. Registrate nuevamente."
            self._verificando = False
            return

        # Intentar obtener token válido (refresca si es necesario)
        id_token = self._obtener_id_token_valido()

        try:
            # Prioridad 1: Firebase nativo con token fresco
            if id_token:
                ok, msg = fb.verificar_email_con_codigo(uid, id_token=id_token)
                if ok:
                    self._procesar_verificacion_exitosa(msg)
                    return
                else:
                    # Si Firebase dice que no está verificado, mostrar mensaje específico
                    self.ids.error.text = msg or "Email no verificado aún. Revisá tu bandeja de entrada y tocá el link."

            # Prioridad 2: Código de 6 dígitos (fallback)
            if codigo and len(codigo) == 6 and codigo.isdigit():
                ok, msg = fb.verificar_email_con_codigo(uid, codigo=codigo)
                if ok:
                    self._procesar_verificacion_exitosa(msg)
                    return
                else:
                    self.ids.error.text = msg or "Código incorrecto"
            else:
                if not id_token:
                    self.ids.error.text = "Sesión expirada. Ingresá el código de 6 dígitos o volvé a registrarte."
                elif not codigo:
                    self.ids.error.text = "Email no verificado aún. Revisá tu bandeja de entrada."
                else:
                    self.ids.error.text = "Ingresá un código de 6 dígitos válido"

        except Exception as e:
            print(f"ERROR VERIFICACION: {e}")
            self.ids.error.text = "Error verificando. Intentá de nuevo."

        self._verificando = False

    def _procesar_verificacion_exitosa(self, msg):
        """Maneja el flujo post-verificación exitosa."""
        self.ids.error.color = (0.18, 0.80, 0.44, 1)
        self.ids.error.text = f"✅ {msg}"

        if self._check_event:
            self._check_event.cancel()
            self._check_event = None

        destino = 'pago_suscripcion' if getattr(session, 'abogado_registrando_uid', None) else 'login'
        session.pending_uid = None
        if destino != 'pago_suscripcion':
            session.pending_email = None
        session.guardar()

        Clock.schedule_once(
            lambda dt, d=destino: setattr(self.manager, 'current', d),
            2.0
        )

        self._verificando = False

    def reenviar_codigo(self):
        uid = session.pending_uid
        email = session.pending_email
        id_token = getattr(session, 'id_token', None)

        if not uid or not email:
            self.ids.error.text = "Sesion invalida"
            return

        try:
            ok, metodo = fb.reenviar_codigo_verificacion(email, uid, id_token=id_token)

            if ok:
                self.ids.error.color = (0.2, 0.6, 0.9, 1)
                if metodo == "firebase":
                    self.ids.error.text = "📧 Email de verificación reenviado. Revisá tu bandeja de entrada."
                else:
                    self.ids.error.text = "📧 Reenvío alternativo enviado"
            else:
                self.ids.error.color = (0.90, 0.25, 0.25, 1)
                self.ids.error.text = "No se pudo reenviar"

        except Exception as e:
            print(f"ERROR REENVIO: {e}")
            self.ids.error.text = "Error reenviando"

    def ir_a_login(self):
        if self._check_event:
            self._check_event.cancel()
            self._check_event = None

        session.pending_uid = None
        session.pending_email = None
        session.abogado_registrando_uid = None
        session.id_token = None
        session.refresh_token = None
        session.guardar()

        self.manager.current = 'login'
