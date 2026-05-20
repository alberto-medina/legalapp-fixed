from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.utils import platform
import firebase_config as fb
import session
import time

VIDEO_TIMEOUT_SEGUNDOS = 600


class DashboardScreen(Screen):

    def on_enter(self):
        user = session.current_user
        if user:
            self.ids.lbl_bienvenida.text = user.get('username', '') or user.get('email', '')

        Clock.schedule_interval(self.check_videollamada, 2)

    def on_leave(self):
        Clock.unschedule(self.check_videollamada)

    def check_videollamada(self, dt):
        user = session.current_user
        if not user:
            return

        uid = user.get('uid')
        email = user.get('email', '')

        consultas = fb.obtener_consultas_usuario(uid, 'cliente')

        videollamada = None
        for cid, cdata in consultas:
            if cdata.get('estado') == 'videollamada':
                created_at = cdata.get('created_at')
                if created_at:
                    try:
                        from datetime import datetime
                        if hasattr(created_at, 'timestamp'):
                            ts = created_at
                        else:
                            ts = datetime.strptime(str(created_at), "%Y-%m-%d %H:%M:%S")
                        ahora = datetime.now()
                        diff = (ahora - ts).total_seconds()
                        if diff > VIDEO_TIMEOUT_SEGUNDOS:
                            continue
                    except Exception:
                        pass
                videollamada = (cid, cdata)
                break

        if not videollamada:
            if "btn_video" in self.ids:
                self.ids.btn_video.opacity = 0
                self.ids.btn_video.disabled = True
            return

        cid, cdata = videollamada

        if "btn_video" in self.ids:
            self.ids.btn_video.opacity = 1
            self.ids.btn_video.disabled = False
            self.ids.btn_video.consulta_id = cid

    def ir_video(self, consulta_id):
        if not consulta_id:
            consulta_id = getattr(self.ids.btn_video, 'consulta_id', 0)
        if not consulta_id:
            return
        session.current_consulta_id = consulta_id
        self.manager.current = "videollamada"

    def nueva_consulta(self):
        self.manager.current = "especialidad"

    def ver_historial(self):
        self.manager.current = "historial"

    def ir_perfil(self):
        self.manager.current = "perfil"

    def cerrar_sesion(self):
        session.current_user = None
        try:
            ls = self.manager.get_screen("login")
            ls.ids.email.text = ""
            ls.ids.password.text = ""
            ls.ids.error.text = ""
        except Exception:
            pass
        self.manager.current = "login"