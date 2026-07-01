import supabase_config as fb

print("DB inicializada")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.utils import platform
from kivy.clock import Clock
from kivy.properties import NumericProperty, StringProperty, BooleanProperty
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
import threading
import time

import session

if platform != "android":
    Window.size = (360, 640)

from views.login import LoginScreen
from views.register import RegisterScreen
from views.register_abogado import RegisterAbogadoScreen
from views.pago_suscripcion import PagoSuscripcionScreen
from views.verification import VerificationScreen
from views.dashboard import DashboardScreen
from views.ubicacion import UbicacionScreen
from views.consulta_tipo import ConsultaTipoScreen
from views.consulta_especialidad import ConsultaEspecialidadScreen
from views.abogados import AbogadosScreen
from views.pago import PagoScreen
from views.pago_mp import PagoMPScreen
from views.chat import ChatScreen
from views.videollamada import VideollamadaScreen
from views.historial import HistorialScreen
from views.abogado_panel import AbogadoPanelScreen
from views.perfil import PerfilScreen
from views.resena import ResenaScreen
from views.admin_panel import AdminPanelScreen
from views.terms_screen import TermsScreen
from views.privacy_screen import PrivacyScreen


def _suscripcion_habilitada_local(user):
    if not user:
        return False

    if not user.get("suscripcion_activa", False):
        return False

    monto = user.get("suscripcion_monto", 0)
    try:
        monto_ok = float(monto or 0) > 0
    except Exception:
        monto_ok = False

    fecha_ok = bool(user.get("suscripcion_fecha"))
    return monto_ok and fecha_ok


class LegalAppPro(App):
    user_id = None
    user_data = None
    id_token = None
    consulta_actual = None

    # Propiedad reactiva para altura del teclado - usada en chat.kv y otros
    keyboard_height = NumericProperty(0)

    # True cuando no hay conexion a internet
    sin_conexion = BooleanProperty(False)
    _resume_en_proceso = False
    _ultimo_resume_ts = 0

    def build(self):

        Window.softinput_mode = 'below_target'

        # Bind para detectar cuando sube/baja el teclado virtual
        Window.bind(keyboard_height=self._on_keyboard_height)

        if platform == 'android':
            Window.bind(on_keyboard=self._on_android_back)

        self.sm = ScreenManager(transition=FadeTransition())

        kv_files = [
            "views/login.kv",
            "views/register.kv",
            "views/register_abogado.kv",
            "views/pago_suscripcion.kv",
            "views/verification.kv",
            "views/dashboard.kv",
            "views/ubicacion.kv",
            "views/consulta_tipo.kv",
            "views/consulta_especialidad.kv",
            "views/abogados.kv",
            "views/pago.kv",
            "views/pago_mp.kv",
            "views/chat.kv",
            "views/videollamada.kv",
            "views/historial.kv",
            "views/abogado_panel.kv",
            "views/perfil.kv",
            "views/resena.kv",
            "views/admin_panel.kv",
            "views/terms_screen.kv",
            "views/privacy_screen.kv",
        ]

        for kv in kv_files:
            Builder.load_file(kv)

        screens = [
            LoginScreen(name="login"),
            RegisterScreen(name="register"),
            RegisterAbogadoScreen(name="register_abogado"),
            PagoSuscripcionScreen(name="pago_suscripcion"),
            VerificationScreen(name="verification"),
            DashboardScreen(name="dashboard"),
            UbicacionScreen(name="ubicacion"),
            ConsultaTipoScreen(name="tipo"),
            ConsultaEspecialidadScreen(name="especialidad"),
            AbogadosScreen(name="abogados"),
            PagoScreen(name="pago"),
            PagoMPScreen(name="pago_mp"),
            ChatScreen(name="chat"),
            VideollamadaScreen(name="videollamada"),
            HistorialScreen(name="historial"),
            AbogadoPanelScreen(name="abogado_panel"),
            PerfilScreen(name="perfil"),
            ResenaScreen(name="resena"),
            AdminPanelScreen(name="admin_panel"),
            TermsScreen(name="terms_screen"),
            PrivacyScreen(name="privacy_screen"),
        ]

        for screen in screens:
            self.sm.add_widget(screen)

        # Restaurar sesion y redirigir a la pantalla correcta
        Clock.schedule_once(lambda dt: self._restaurar_sesion(), 0.5)

        if platform == 'android':
            try:
                from fcm_service import (
                    crear_canal_notificaciones,
                    obtener_fcm_token,
                    guardar_token_en_supabase
                )
                crear_canal_notificaciones()
                guardar_token_en_supabase()
                Clock.schedule_once(lambda dt: obtener_fcm_token(), 5)
                print("FCM iniciado")
            except Exception as e:
                print(f"Error iniciando FCM: {e}")

        # Monitor de conexion: chequea cada 10 segundos en background
        Clock.schedule_interval(lambda dt: self._check_conexion(), 10)

        return self.sm

    # ============================================================
    # MONITOR DE CONEXION
    # ============================================================

    def _check_conexion(self):
        """Chequea conexion en thread separado y muestra/oculta banner."""
        import threading as _t
        import supabase_config as _fb

        def _check():
            ok = _fb.check_conexion()
            Clock.schedule_once(lambda dt: self._set_conexion(ok), 0)

        _t.Thread(target=_check, daemon=True).start()

    def _set_conexion(self, ok):
        if not ok and not self.sin_conexion:
            self.sin_conexion = True
            self._mostrar_banner_offline()
        elif ok and self.sin_conexion:
            self.sin_conexion = False
            self._ocultar_banner_offline()

    def _mostrar_banner_offline(self):
        if hasattr(self, '_banner_offline'):
            return
        from kivy.core.window import Window as _Win
        banner = BoxLayout(
            size_hint=(1, None),
            height=36,
            pos=(0, _Win.height - 36),
        )
        with banner.canvas.before:
            Color(rgba=(0.85, 0.22, 0.22, 1))
            banner._rect = Rectangle(pos=banner.pos, size=banner.size)
        banner.bind(
            pos=lambda w, v: setattr(w._rect, "pos", v),
            size=lambda w, v: setattr(w._rect, "size", v),
        )
        lbl = Label(
            text="Sin conexion - verificando...",
            font_size="13sp",
            color=(1, 1, 1, 1),
            bold=True,
        )
        banner.add_widget(lbl)
        from kivy.core.window import Window as _Win2
        _Win2.add_widget(banner)
        self._banner_offline = banner

    def _ocultar_banner_offline(self):
        if hasattr(self, '_banner_offline'):
            from kivy.core.window import Window as _Win
            try:
                _Win.remove_widget(self._banner_offline)
            except Exception:
                pass
            del self._banner_offline

    # ============================================================
    # TECLADO VIRTUAL - actualiza keyboard_height reactivamente
    # ============================================================

    def _on_keyboard_height(self, window, height):
        self.keyboard_height = max(0, height or 0)
        try:
            screen = self.sm.current_screen
            if hasattr(screen, "on_keyboard_height_changed"):
                screen.on_keyboard_height_changed(self.keyboard_height)
        except Exception:
            pass

    # ============================================================
    # RESTAURAR SESION
    # ============================================================

    def _restaurar_sesion(self):
        Clock.schedule_once(lambda dt: self._restaurar_sesion_async(), 0)

    def _restaurar_sesion_async(self):
        if not session.cargar():
            print("No hay sesion guardada, quedamos en login")
            return

        print("Sesion restaurada, redirigiendo...")

        def _resolver():
            accion = self._resolver_estado_sesion()
            Clock.schedule_once(lambda dt: self._aplicar_estado_sesion(accion), 0)

        threading.Thread(target=_resolver, daemon=True).start()

    def _resolver_estado_sesion(self):
        accion = {"screen": None}

        if session.pending_uid:
            usuario_pendiente = None
            try:
                usuario_pendiente = fb.obtener_usuario(session.pending_uid)
            except Exception as e:
                print(f"ERROR obteniendo usuario pendiente: {e}")

            if usuario_pendiente and usuario_pendiente.get('email_verified', False):
                print("Sesion pendiente ya verificada, corrigiendo estado...")
                accion["pending_uid"] = None
                accion["pending_email"] = None

                if usuario_pendiente.get('rol') == 'abogado':
                    accion["abogado_registrando_uid"] = None
                    accion["current_user"] = usuario_pendiente

                    if not usuario_pendiente.get('suscripcion_activa', False):
                        accion["screen"] = 'pago_suscripcion'
                    elif not usuario_pendiente.get('aprobado', False):
                        accion["current_user"] = None
                        accion["screen"] = 'login'
                    else:
                        accion["screen"] = 'abogado_panel'
                else:
                    accion["current_user"] = usuario_pendiente
                    accion["screen"] = 'dashboard'
            else:
                print("Redirigiendo a verification")
                accion["screen"] = 'verification'
            return accion

        if session.abogado_registrando_uid:
            print("Redirigiendo a pago_suscripcion")
            accion["screen"] = 'pago_suscripcion'
            return accion

        if session.current_user:
            user = session.current_user
            uid = user.get('uid')
            if uid:
                try:
                    user = fb.obtener_usuario(uid) or user
                    accion["current_user"] = user
                except Exception as e:
                    print(f"ERROR refrescando sesion actual: {e}")

            rol = user.get('rol')
            print(f"Usuario logueado: {rol}")

            if rol == 'abogado':
                suscripcion_activa = _suscripcion_habilitada_local(user)
                email_verificado = user.get('email_verified', False)
                aprobado = user.get('aprobado', False)

                if not email_verificado:
                    accion["screen"] = 'verification'
                elif not suscripcion_activa:
                    accion["screen"] = 'pago_suscripcion'
                elif not aprobado:
                    accion["current_user"] = None
                    accion["screen"] = 'login'
                else:
                    accion["screen"] = 'abogado_panel'
            else:
                accion["screen"] = 'dashboard'

            return accion

        print("No hay usuario logueado, quedamos en login")
        accion["screen"] = 'login'
        return accion

    def _aplicar_estado_sesion(self, accion):
        if not accion:
            return

        if "pending_uid" in accion:
            session.pending_uid = accion["pending_uid"]
        if "pending_email" in accion:
            session.pending_email = accion["pending_email"]
        if "abogado_registrando_uid" in accion:
            session.abogado_registrando_uid = accion["abogado_registrando_uid"]
        if "current_user" in accion:
            session.current_user = accion["current_user"]

        if any(k in accion for k in ("pending_uid", "pending_email", "abogado_registrando_uid", "current_user")):
            session.guardar()

        destino = accion.get("screen")
        if destino:
            self.sm.current = destino

    # ============================================================
    # ANDROID BACK BUTTON
    # ============================================================

    def _on_android_back(self, window, key, scancode, codepoint, modifier):
        if key == 27:
            current = self.sm.current
            print(f"BACK: current={current}")

            screen = self.sm.current_screen
            if hasattr(screen, 'volver'):
                try:
                    screen.volver()
                    print(f"BACK: volver() executed, new current={self.sm.current}")
                    return True
                except Exception as e:
                    print(f"BACK: volver() error={e}")

            volver_screens = {
                "register": "login",
                "register_abogado": "login",
                "pago_suscripcion": "register_abogado",
                "verification": "login",
                "ubicacion": "dashboard",
                "tipo": "ubicacion",
                "especialidad": "tipo",
                "abogados": "especialidad",
                "pago": "abogados",
                "pago_mp": "pago",
                "chat": "dashboard",
                "videollamada": "chat",
                "historial": "dashboard",
                "resena": "historial",
                "terms_screen": "register",
                "privacy_screen": "register",
                "admin_panel": "login",
            }

            if current in volver_screens:
                destino = volver_screens[current]
                print(f"BACK: navigating {current} -> {destino}")
                self.sm.current = destino
                return True

            if current in {"login", "dashboard", "abogado_panel"}:
                print("BACK: closing app")
                return False

            print(f"BACK: fallback to login from {current}")
            self.sm.current = "login"
            return True

        return False

    # ============================================================
    # PAUSE / RESUME
    # ============================================================

    def on_pause(self):
        print("APP PAUSED")

        def _guardar_async():
            try:
                session.guardar()
            except Exception as e:
                print(f"ERROR guardando sesion async: {e}")

        threading.Thread(target=_guardar_async, daemon=True).start()
        return True

    def on_resume(self):
        print("APP RESUMED")

        ahora = time.time()
        if self._resume_en_proceso:
            print("RESUME ignorado: ya hay una reanudacion en curso")
            return

        if ahora - self._ultimo_resume_ts < 1.5:
            print("RESUME ignorado: llamado duplicado muy seguido")
            return

        self._resume_en_proceso = True
        self._ultimo_resume_ts = ahora

        def _resume_async():
            try:
                session.cargar()
            except Exception as e:
                print(f"ERROR cargando sesion async: {e}")

        threading.Thread(target=_resume_async, daemon=True).start()

        def _fin_resume(*_):
            self._resume_en_proceso = False

        def _aplicar_resume(dt):
            try:
                screen = self.sm.current_screen
                current = self.sm.current

                if hasattr(screen, 'on_app_resume'):
                    try:
                        screen.on_app_resume()
                    except Exception as e:
                        print(f"ERROR on_app_resume screen: {e}")

                if current == "pago_mp":
                    if hasattr(screen, 'verificar_pago'):
                        print("RESUME: auto-verificando pago...")
                        Clock.schedule_once(lambda dt: screen.verificar_pago(), 1.0)

                elif current == "pago_suscripcion":
                    if hasattr(screen, 'verificar_pago'):
                        print("RESUME: auto-verificando suscripcion...")
                        Clock.schedule_once(lambda dt: screen.verificar_pago(silencioso=True), 1.0)

                elif current == "videollamada":
                    print("RESUME: refrescando videollamada...")
                    if hasattr(screen, '_refresh_ui'):
                        Clock.schedule_once(lambda dt: screen._refresh_ui(), 0.8)

                elif current == "abogados":
                    print("RESUME: refrescando abogados...")
                    if hasattr(screen, 'cargar_abogados'):
                        Clock.schedule_once(lambda dt: screen.cargar_abogados(), 0.6)

                elif current == "especialidad":
                    print("RESUME: refrescando especialidades...")
                    if hasattr(screen, 'cargar_especialidades'):
                        from views.consulta_especialidad import ESPECIALIDADES
                        Clock.schedule_once(lambda dt: screen.cargar_especialidades(ESPECIALIDADES), 0.5)

                elif current == "dashboard" and session.current_user:
                    uid = (session.current_user or {}).get("uid")
                    print("RESUME: refrescando dashboard...")
                    if hasattr(screen, '_cargar_dashboard_async') and uid:
                        Clock.schedule_once(lambda dt, u=uid: screen._cargar_dashboard_async(u), 0.6)
                    if hasattr(screen, 'check_videollamada'):
                        Clock.schedule_once(lambda dt: screen.check_videollamada(0), 0.9)

                elif current == "login" and (session.current_user or session.pending_uid):
                    print("RESUME: restaurando sesion desde login...")
                    Clock.schedule_once(lambda dt: self._restaurar_sesion(), 0.8)
            finally:
                Clock.schedule_once(_fin_resume, 1.6)

        Clock.schedule_once(_aplicar_resume, 0.2)


if __name__ == "__main__":
    LegalAppPro().run()
