from kivy.uix.screenmanager import Screen

from views.perfil_common import PerfilBaseMixin


class PerfilClienteScreen(PerfilBaseMixin, Screen):

    def _aplicar_datos_rol(self, user_data):
        self.ids.lbl_rol_badge.text = "CLIENTE"
        self.ids.lbl_rol_badge.color = (0.60, 0.85, 1.00, 1)

    def volver(self):
        self.manager.current = "dashboard"
