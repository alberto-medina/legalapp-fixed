from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from database import get_connection
import session
import time


VIDEO_TIMEOUT_SEGUNDOS = 600  # 10 minutos


class DashboardScreen(Screen):

    def on_enter(self):

        user = session.current_user

        if user:
            self.ids.lbl_bienvenida.text = user[1] or user[2]

        Clock.schedule_interval(self.check_videollamada, 2)

    def on_leave(self):

        Clock.unschedule(self.check_videollamada)

    # =====================================================
    # CHECK VIDEO
    # =====================================================

    def check_videollamada(self, dt):

        user = session.current_user

        if not user:
            return

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, created_at
            FROM consultas
            WHERE user_email=?
            AND estado='videollamada'
            ORDER BY id DESC
            LIMIT 1
        """, (user[2],))

        row = cursor.fetchone()

        if not row:
            conn.close()

            if "btn_video" in self.ids:
                self.ids.btn_video.opacity = 0
                self.ids.btn_video.disabled = True

            return

        consulta_id, created_at = row

        if "btn_video" not in self.ids:
            conn.close()
            return

        # Verificar si expiró usando created_at
        if created_at:
            try:
                from datetime import datetime
                ts = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                ahora = datetime.now()
                diff = (ahora - ts).total_seconds()

                if diff > VIDEO_TIMEOUT_SEGUNDOS:
                    # EXPIRÓ: ocultar botón
                    self.ids.btn_video.opacity = 0
                    self.ids.btn_video.disabled = True
                    conn.close()
                    return
            except Exception:
                pass

        self.ids.btn_video.opacity = 1
        self.ids.btn_video.disabled = False
        self.ids.btn_video.consulta_id = consulta_id
        conn.close()

    # =====================================================
    # IR VIDEO
    # =====================================================

    def ir_video(self, consulta_id):

        if not consulta_id:
            consulta_id = getattr(self.ids.btn_video, 'consulta_id', 0)

        if not consulta_id:
            return

        session.current_consulta_id = consulta_id

        self.manager.current = "videollamada"

    # =====================================================
    # NAV
    # =====================================================

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