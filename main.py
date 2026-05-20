import firebase_config as fb
print("DB INICIALIZADA")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.utils import platform
from kivy.clock import Clock

if platform != "android":
    Window.size = (360, 640)

from views.login import LoginScreen
from views.register import RegisterScreen
from views.verification import VerificationScreen
from views.dashboard import DashboardScreen
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


class LegalAppPro(App):
    user_id = None
    user_data = None
    id_token = None
    consulta_actual = None

    def build(self):
        Window.softinput_mode = 'below_target'
        if platform == 'android':
            Window.bind(on_keyboard=self._on_android_back)

        self.sm = ScreenManager(transition=FadeTransition())

        for kv in ["views/login.kv", "views/register.kv", "views/verification.kv",
                   "views/dashboard.kv",
                   "views/consulta_tipo.kv", "views/consulta_especialidad.kv",
                   "views/abogados.kv", "views/pago.kv", "views/pago_mp.kv",
                   "views/chat.kv", "views/videollamada.kv", "views/historial.kv",
                   "views/abogado_panel.kv", "views/perfil.kv", "views/resena.kv",
                   "views/admin_panel.kv"]:
            Builder.load_file(kv)

        for screen in [LoginScreen(name="login"), RegisterScreen(name="register"),
                       VerificationScreen(name="verification"),
                       DashboardScreen(name="dashboard"), ConsultaTipoScreen(name="tipo"),
                       ConsultaEspecialidadScreen(name="especialidad"), AbogadosScreen(name="abogados"),
                       PagoScreen(name="pago"), PagoMPScreen(name="pago_mp"), ChatScreen(name="chat"),
                       VideollamadaScreen(name="videollamada"), HistorialScreen(name="historial"),
                       AbogadoPanelScreen(name="abogado_panel"), PerfilScreen(name="perfil"),
                       ResenaScreen(name="resena"),
                       AdminPanelScreen(name="admin_panel")]:
            self.sm.add_widget(screen)

        # Inicializar FCM en Android
        if platform == 'android':
            from fcm_service import crear_canal_notificaciones, obtener_fcm_token
            crear_canal_notificaciones()
            # Obtener token después de un delay para que Firebase esté listo
            Clock.schedule_once(lambda dt: obtener_fcm_token(), 5)

        return self.sm

    def _on_android_back(self, window, key, scancode, codepoint, modifier):
        if key == 27:
            if self.sm.current in {"login", "dashboard", "abogado_panel"}:
                return False
            screen = self.sm.current_screen
            if hasattr(screen, 'volver') and callable(getattr(screen, 'volver')):
                try:
                    screen.volver()
                    return True
                except Exception:
                    pass
            self.sm.current = "dashboard" if self.sm.has_screen("dashboard") else "login"
            return True
        return False


if __name__ == "__main__":
    LegalAppPro().run()