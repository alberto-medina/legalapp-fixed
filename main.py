import database
print("DB INICIALIZADA")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.utils import platform

# 👇 SOLO escritorio
if platform != "android":
    Window.size = (360, 640)

from views.login import LoginScreen
from views.register import RegisterScreen
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


class LegalAppPro(App):

    def build(self):
        # 🔥 DB + DEMO USERS
        database.create_tables()
        database.actualizar_db()
        database.crear_usuarios_demo()

        self.sm = ScreenManager(transition=FadeTransition())

        Builder.load_file("views/login.kv")
        Builder.load_file("views/register.kv")
        Builder.load_file("views/dashboard.kv")
        Builder.load_file("views/consulta_tipo.kv")
        Builder.load_file("views/consulta_especialidad.kv")
        Builder.load_file("views/abogados.kv")
        Builder.load_file("views/pago.kv")
        Builder.load_file("views/pago_mp.kv")
        Builder.load_file("views/chat.kv")
        Builder.load_file("views/videollamada.kv")
        Builder.load_file("views/historial.kv")
        Builder.load_file("views/abogado_panel.kv")
        Builder.load_file("views/perfil.kv")
        Builder.load_file("views/resena.kv")

        self.sm.add_widget(LoginScreen(name="login"))
        self.sm.add_widget(RegisterScreen(name="register"))
        self.sm.add_widget(DashboardScreen(name="dashboard"))
        self.sm.add_widget(ConsultaTipoScreen(name="tipo"))
        self.sm.add_widget(ConsultaEspecialidadScreen(name="especialidad"))
        self.sm.add_widget(AbogadosScreen(name="abogados"))
        self.sm.add_widget(PagoScreen(name="pago"))
        self.sm.add_widget(PagoMPScreen(name="pago_mp"))
        self.sm.add_widget(ChatScreen(name="chat"))
        self.sm.add_widget(VideollamadaScreen(name="videollamada"))
        self.sm.add_widget(HistorialScreen(name="historial"))
        self.sm.add_widget(AbogadoPanelScreen(name="abogado_panel"))
        self.sm.add_widget(PerfilScreen(name="perfil"))
        self.sm.add_widget(ResenaScreen(name="resena"))

        return self.sm


if __name__ == "__main__":
    LegalAppPro().run()