from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
import threading
import supabase_config as fb
import session
from views.utils_avatar import set_avatar_image


SERVICIOS_HABILITADOS = {
    "disponible": {"chat", "video", "urgente"},
    "guardia": {"urgente"},
    "ocupado": set(),
}


class ConsultaTipoScreen(Screen):
    _cargando_tipo = False
    _abogado_data_cache = None

    def obtener_precios(self):
        """
        Trae precios dinámicos desde Supabase con fallback seguro
        """
        config = fb.obtener_configuracion() or {}

        try:
            precio_chat = int(config.get("precio_chat", 1000))
        except:
            precio_chat = 1000

        try:
            precio_video = int(config.get("precio_video", 3000))
        except:
            precio_video = 3000

        try:
            precio_urgente = int(config.get("precio_urgente", 5000))
        except:
            precio_urgente = 5000

        return {
            "chat": precio_chat,
            "video": precio_video,
            "urgente": precio_urgente,
        }

    def on_enter(self):

        if not getattr(session, "abogado_seleccionado", None):
            self.manager.current = "abogados"
            return

        if self._cargando_tipo:
            return

        self._cargando_tipo = True
        self.ids.lbl_abogado.text = "Cargando..."
        self.ids.lbl_especialidad.text = ""
        self.ids.lbl_banner.text = "Cargando servicios..."
        self.ids.btn_chat.disabled = True
        self.ids.btn_video.disabled = True
        self.ids.btn_urgente.disabled = True

        abogado_email = session.abogado_seleccionado

        def _fetch():
            payload = {"abogado_data": None, "precios": None}
            try:
                payload["abogado_data"] = fb.obtener_usuario_por_email(abogado_email)
                payload["precios"] = self.obtener_precios()
            except Exception as e:
                print(f"ERROR consulta_tipo on_enter: {e}")
            finally:
                Clock.schedule_once(lambda dt, data=payload: self._aplicar_on_enter(data), 0)

        threading.Thread(target=_fetch, daemon=True).start()

    def _aplicar_on_enter(self, payload):
        self._cargando_tipo = False
        abogado_data = (payload or {}).get("abogado_data")
        self._abogado_data_cache = abogado_data

        estado = (
            (abogado_data or {}).get("estado_abogado")
            or getattr(session, "estado_abogado", "disponible")
            or "disponible"
        ).lower()
        habilitados = SERVICIOS_HABILITADOS.get(estado, set())

        session.estado_abogado = estado
        session.guardar()

        nombre = (
            abogado_data.get('username', '')
            or abogado_data.get('nombre', 'Abogado')
            if abogado_data else 'Abogado'
        )

        especialidad = abogado_data.get('especialidad', '') if abogado_data else ''
        foto = abogado_data.get('foto_url', '') if abogado_data else ''

        self.ids.lbl_abogado.text = nombre
        self.ids.lbl_especialidad.text = especialidad
        set_avatar_image(
            self.ids.img_abogado,
            foto,
            (abogado_data or {}).get('email', '')
        )

        # PRECIOS DINÁMICOS
        self.precios = (payload or {}).get("precios") or self.obtener_precios()

        self.precios_label = {
            "chat": f"${self.precios['chat']}",
            "video": f"${self.precios['video']}",
            "urgente": f"${self.precios['urgente']}",
        }

        # CHAT
        chat_ok = "chat" in habilitados
        self.ids.btn_chat.disabled = not chat_ok
        self.ids.btn_chat.opacity = 1 if chat_ok else 0.45
        self.ids.btn_chat.background_color = (0.18, 0.80, 0.44, 1) if chat_ok else (0.55, 0.55, 0.55, 1)

        self.ids.lbl_chat_estado.text = (
            f"Disponible - {self.precios_label['chat']}"
            if chat_ok else "No disponible"
        )

        self.ids.lbl_chat_estado.color = (
            (0.18, 0.80, 0.44, 1) if chat_ok else (0.85, 0.30, 0.30, 1)
        )

        # VIDEO
        video_ok = "video" in habilitados
        self.ids.btn_video.disabled = not video_ok
        self.ids.btn_video.opacity = 1 if video_ok else 0.45
        self.ids.btn_video.background_color = (0.18, 0.80, 0.44, 1) if video_ok else (0.55, 0.55, 0.55, 1)

        self.ids.lbl_video_estado.text = (
            f"Disponible - {self.precios_label['video']}"
            if video_ok else "No disponible"
        )

        self.ids.lbl_video_estado.color = (
            (0.18, 0.80, 0.44, 1) if video_ok else (0.85, 0.30, 0.30, 1)
        )

        # URGENTE
        urgente_ok = "urgente" in habilitados
        self.ids.btn_urgente.disabled = not urgente_ok
        self.ids.btn_urgente.opacity = 1 if urgente_ok else 0.45
        self.ids.btn_urgente.background_color = (0.91, 0.30, 0.24, 1) if urgente_ok else (0.55, 0.55, 0.55, 1)

        self.ids.lbl_urgente_estado.text = (
            f"Disponible - {self.precios_label['urgente']}"
            if urgente_ok else "No disponible"
        )

        self.ids.lbl_urgente_estado.color = (
            (0.91, 0.30, 0.24, 1) if urgente_ok else (0.85, 0.30, 0.30, 1)
        )

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
        """
        Guardar datos en session para que MercadoPago cree la consulta
        pendiente y luego la marque pagada al confirmar.
        """
        session.pago_tipo = "consulta"
        session.tipo_servicio = servicio

        user = session.current_user
        abogado_email = session.abogado_seleccionado

        if not user or not abogado_email:
            self.manager.current = "abogados"
            return

        abogado_data = self._abogado_data_cache or fb.obtener_usuario_por_email(abogado_email)

        if not abogado_data:
            self.manager.current = "abogados"
            return

        # Guardar datos en session para crear consulta pendiente en pago_mp
        session.pago_pending_abogado_uid = abogado_data.get('uid')
        session.pago_pending_abogado_email = abogado_data.get('email', '')
        session.pago_pending_cliente_uid = user.get('uid')
        session.pago_pending_cliente_email = user.get('email', '')
        session.current_consulta_id = None
        session.pago_external_reference = None
        session.pago_preference_id = None
        session.pago_init_point = None

        # Precio
        config = fb.obtener_configuracion() or {}
        precios = {
            "chat": int(config.get("precio_chat", 1000)),
            "video": int(config.get("precio_video", 3000)),
            "urgente": int(config.get("precio_urgente", 5000)),
        }
        session.pago_pending_precio = precios.get(servicio, 0)
        session.guardar()

        self.manager.current = "pago"

    def volver(self):
        self.manager.current = "abogados"
