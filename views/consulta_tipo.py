from kivy.uix.screenmanager import Screen
from database import get_connection
import session


SERVICIOS_HABILITADOS = {
    "disponible": {"chat", "video", "urgente"},
    "guardia": {"urgente"},
    "ocupado": set(),
}

PRECIOS = {
    "chat": "$1000",
    "video": "$3000",
    "urgente": "$5000",
}


class ConsultaTipoScreen(Screen):

    # =====================================================
    # ENTER
    # =====================================================

    def on_enter(self):

        # =============================================
        # SEGURIDAD
        # =============================================

        if not getattr(session, "abogado_seleccionado", None):
            self.manager.current = "abogados"
            return

        estado = (
            getattr(session, "estado_abogado", "disponible")
            or "disponible"
        ).lower()

        habilitados = SERVICIOS_HABILITADOS.get(estado, set())

        # =============================================
        # DATOS ABOGADO
        # =============================================

        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            SELECT username, especialidad
            FROM users
            WHERE email=?
        """, (session.abogado_seleccionado,))

        row = c.fetchone()

        conn.close()

        nombre = "Abogado"
        especialidad = ""

        if row:
            nombre = row[0] or "Abogado"
            especialidad = row[1] or ""

        self.ids.lbl_abogado.text = nombre
        self.ids.lbl_especialidad.text = especialidad

        # =============================================
        # CHAT
        # =============================================

        chat_ok = "chat" in habilitados

        self.ids.btn_chat.disabled = not chat_ok
        self.ids.btn_chat.opacity = 1 if chat_ok else 0.45

        self.ids.btn_chat.background_color = (
            (0.18, 0.80, 0.44, 1)
            if chat_ok
            else
            (0.55, 0.55, 0.55, 1)
        )

        self.ids.lbl_chat_estado.text = (
            f"Disponible • {PRECIOS['chat']}"
            if chat_ok
            else
            "No disponible"
        )

        self.ids.lbl_chat_estado.color = (
            (0.18, 0.80, 0.44, 1)
            if chat_ok
            else
            (0.85, 0.30, 0.30, 1)
        )

        # =============================================
        # VIDEO
        # =============================================

        video_ok = "video" in habilitados

        self.ids.btn_video.disabled = not video_ok
        self.ids.btn_video.opacity = 1 if video_ok else 0.45

        self.ids.btn_video.background_color = (
            (0.18, 0.80, 0.44, 1)
            if video_ok
            else
            (0.55, 0.55, 0.55, 1)
        )

        self.ids.lbl_video_estado.text = (
            f"Disponible • {PRECIOS['video']}"
            if video_ok
            else
            "No disponible"
        )

        self.ids.lbl_video_estado.color = (
            (0.18, 0.80, 0.44, 1)
            if video_ok
            else
            (0.85, 0.30, 0.30, 1)
        )

        # =============================================
        # URGENTE
        # =============================================

        urgente_ok = "urgente" in habilitados

        self.ids.btn_urgente.disabled = not urgente_ok
        self.ids.btn_urgente.opacity = 1 if urgente_ok else 0.45

        self.ids.btn_urgente.background_color = (
            (0.91, 0.30, 0.24, 1)
            if urgente_ok
            else
            (0.55, 0.55, 0.55, 1)
        )

        self.ids.lbl_urgente_estado.text = (
            f"Disponible • {PRECIOS['urgente']}"
            if urgente_ok
            else
            "No disponible"
        )

        self.ids.lbl_urgente_estado.color = (
            (0.91, 0.30, 0.24, 1)
            if urgente_ok
            else
            (0.85, 0.30, 0.30, 1)
        )

        # =============================================
        # BANNER
        # =============================================

        if estado == "guardia":

            self.ids.lbl_banner.text = (
                "Abogado en guardia • Solo urgencias habilitadas"
            )

            self.ids.lbl_banner.color = (
                0.90, 0.70, 0.10, 1
            )

        elif estado == "ocupado":

            self.ids.lbl_banner.text = (
                "Abogado ocupado • No disponible actualmente"
            )

            self.ids.lbl_banner.color = (
                0.85, 0.30, 0.30, 1
            )

        else:

            self.ids.lbl_banner.text = (
                "Abogado disponible • Todos los servicios habilitados"
            )

            self.ids.lbl_banner.color = (
                0.18, 0.80, 0.44, 1
            )

    # =====================================================
    # SELECCIONAR
    # =====================================================

    def seleccionar(self, servicio):

        session.tipo_servicio = servicio

        self.manager.current = "pago"

    # =====================================================
    # VOLVER
    # =====================================================

    def volver(self):

        self.manager.current = "abogados"