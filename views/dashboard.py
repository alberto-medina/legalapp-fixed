from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from database import get_connection
import session


class DashboardScreen(Screen):

    def on_enter(self):
        user = session.current_user
        if user:
            self.ids.lbl_bienvenida.text = user[1] or user[2]

        # 🔴 empieza a escuchar si hay videollamada
        Clock.schedule_interval(self.check_videollamada, 2)

    def on_leave(self):
        # 🔴 importante para no duplicar timers
        Clock.unschedule(self.check_videollamada)

    # =========================
    # 🎥 DETECCION VIDEOLLAMADA
    # =========================
    def check_videollamada(self, dt):
        user = session.current_user
        if not user:
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id
            FROM consultas
            WHERE user_email=? AND estado='videollamada'
            ORDER BY id DESC LIMIT 1
        """, (user[2],))

        row = cursor.fetchone()
        conn.close()

        # 🔧 FIX: evitar error si el botón no existe todavía
        if "btn_video" not in self.ids:
            return

        if row:
            self.ids.btn_video.opacity = 1
            self.ids.btn_video.disabled = False
            self.ids.btn_video.consulta_id = row[0]
        else:
            self.ids.btn_video.opacity = 0
            self.ids.btn_video.disabled = True

    # =========================
    # 🎥 IR A VIDEOLLAMADA
    # =========================
    def ir_video(self, consulta_id):
        session.current_consulta_id = consulta_id
        self.manager.current = "videollamada"

    # =========================
    # 🧭 NAVEGACION
    # =========================
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