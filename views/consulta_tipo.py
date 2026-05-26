from kivy.uix.screenmanager import Screen
import supabase_config as fb
import session


SERVICIOS_HABILITADOS = {
    "disponible": {"chat", "video", "urgente"},
    "guardia": {"urgente"},
    "ocupado": set(),
}

PRECIOS = {
    "chat": 1000,
    "video": 3000,
    "urgente": 5000,
}

PRECIOS_LABEL = {
    "chat": "$1000",
    "video": "$3000",
    "urgente": "$5000",
}


class ConsultaTipoScreen(Screen):

    def on_enter(self):
        if not getattr(session, "abogado_seleccionado", None):
            self.manager.current = "abogados"
            return

        estado = (getattr(session, "estado_abogado", "disponible") or "disponible").lower()
        habilitados = SERVICIOS_HABILITADOS.get(estado, set())

        abogado_data = fb.obtener_usuario_por_email(session.abogado_seleccionado)
        nombre = abogado_data.get('username', '') or abogado_data.get('nombre', 'Abogado') if abogado_data else 'Abogado'
        especialidad = abogado_data.get('especialidad', '') if abogado_data else ''

        self.ids.lbl_abogado.text = nombre
        self.ids.lbl_especialidad.text = especialidad

        # CHAT
        chat_ok = "chat" in habilitados
        self.ids.btn_chat.disabled = not chat_ok
        self.ids.btn_chat.opacity = 1 if chat_ok else 0.45
        self.ids.btn_chat.background_color = (0.18, 0.80, 0.44, 1) if chat_ok else (0.55, 0.55, 0.55, 1)
        self.ids.lbl_chat_estado.text = f"Disponible - {PRECIOS_LABEL['chat']}" if chat_ok else "No disponible"
        self.ids.lbl_chat_estado.color = (0.18, 0.80, 0.44, 1) if chat_ok else (0.85, 0.30, 0.30, 1)

        # VIDEO
        video_ok = "video" in habilitados
        self.ids.btn_video.disabled = not video_ok
        self.ids.btn_video.opacity = 1 if video_ok else 0.45
        self.ids.btn_video.background_color = (0.18, 0.80, 0.44, 1) if video_ok else (0.55, 0.55, 0.55, 1)
        self.ids.lbl_video_estado.text = f"Disponible - {PRECIOS_LABEL['video']}" if video_ok else "No disponible"
        self.ids.lbl_video_estado.color = (0.18, 0.80, 0.44, 1) if video_ok else (0.85, 0.30, 0.30, 1)

        # URGENTE
        urgente_ok = "urgente" in habilitados
        self.ids.btn_urgente.disabled = not urgente_ok
        self.ids.btn_urgente.opacity = 1 if urgente_ok else 0.45
        self.ids.btn_urgente.background_color = (0.91, 0.30, 0.24, 1) if urgente_ok else (0.55, 0.55, 0.55, 1)
        self.ids.lbl_urgente_estado.text = f"Disponible - {PRECIOS_LABEL['urgente']}" if urgente_ok else "No disponible"
        self.ids.lbl_urgente_estado.color = (0.91, 0.30, 0.24, 1) if urgente_ok else (0.85, 0.30, 0.30, 1)

        # BANNER
        if estado == "guardia":
            self.ids.lbl_banner.text = "Abogado en guardia - Solo urgencias habilitadas"
            self.ids.lbl_banner.color = (0.90, 0.70, 0.10, 1)
        elif estado == "ocupado":
            self.ids.lbl_banner.text = "Abogado ocupado - No disponible actualmente"
            self.ids.lbl_banner.color = (0.85, 0.30, 0.30, 1)
        else:
            self.ids.lbl_banner.text = "Abogado disponible - Todos los servicios habilitados"
            self.ids.lbl_banner.color = (0.18, 0.80, 0.44, 1)

    def seleccionar(self, servicio):
        session.tipo_servicio = servicio

        user = session.current_user
        abogado_email = session.abogado_seleccionado

        if not user or not abogado_email:
            self.manager.current = "abogados"
            return

        abogado_data = fb.obtener_usuario_por_email(abogado_email)
        if not abogado_data:
            self.manager.current = "abogados"
            return

        abogado_uid = abogado_data.get('uid')
        abogado_email_val = abogado_data.get('email', '')
        cliente_uid = user.get('uid')
        cliente_email = user.get('email', '')
        precio = PRECIOS.get(servicio, 0)

        data = {
            "cliente_uid": cliente_uid,
            "cliente_email": cliente_email,
            "abogado_uid": abogado_uid,
            "abogado_email": abogado_email_val,
            "tipo_servicio": servicio,
            "descripcion": "",
            "estado": "pendiente",
            "precio": precio,
        }

        ok, consulta_id = fb.crear_consulta(data)

        if not ok:
            print(f"ERROR creando consulta: {consulta_id}")
            return

        session.current_consulta_id = consulta_id
        print(f"CONSULTA CREADA: id={consulta_id}, tipo={servicio}")

        self.manager.current = "pago"

    def volver(self):
        self.manager.current = "abogados"