import session
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
import threading
import supabase_config as fb

DESCRIPCIONES = {
    "chat": "Consulta por mensajes privados con el abogado.",
    "video": "Videollamada privada para explicar el caso en tiempo real.",
    "urgente": "Atencion inmediata prioritaria para situaciones urgentes.",
}


class PagoScreen(Screen):
    _cargando_pago = False
    _abogado_data_cache = None

    def obtener_precios(self):
        config = fb.obtener_configuracion() or {}

        def safe_int(v, default):
            try:
                return int(v)
            except:
                return default

        chat = safe_int(config.get("precio_chat", 1000), 1000)
        video = safe_int(config.get("precio_video", 3000), 3000)
        urgente = safe_int(config.get("precio_urgente", 5000), 5000)

        return {
            "chat": {
                "titulo": "Chat",
                "precio": chat,
                "texto": f"${chat:,}",
                "color": (0.18, 0.80, 0.44, 1),
            },
            "video": {
                "titulo": "Videollamada",
                "precio": video,
                "texto": f"${video:,}",
                "color": (0.18, 0.80, 0.44, 1),
            },
            "urgente": {
                "titulo": "URGENTE",
                "precio": urgente,
                "texto": f"${urgente:,}",
                "color": (0.91, 0.30, 0.24, 1),
            },
        }


    def on_enter(self):
        tipo = getattr(session, "tipo_servicio", "chat") or "chat"
        abogado = getattr(session, "abogado_seleccionado", "") or "No seleccionado"
        area = getattr(session, "area_legal", "") or "-"
        self.ids.lbl_abogado_info.text = f"Abogado: {abogado}\nEspecialidad: {area}"
        self.ids.lbl_precio_grande.text = "Cargando..."
        self.ids.lbl_tipo_desc.text = DESCRIPCIONES.get(tipo, "")
        self.ids.lbl_resumen.text = "Cargando resumen..."
        self.ids.btn_pago_unico.text = "Cargando pago..."
        self.ids.btn_pago_unico.disabled = True
        self.ids.lbl_error_mp.text = ""

        if self._cargando_pago:
            return

        self._cargando_pago = True

        def _fetch():
            payload = {"precios": None, "abogado_data": None}
            try:
                payload["precios"] = self.obtener_precios()
                if abogado and abogado != "No seleccionado":
                    payload["abogado_data"] = fb.obtener_usuario_por_email(abogado)
            except Exception as e:
                print(f"ERROR pago on_enter: {e}")
            finally:
                Clock.schedule_once(lambda dt, data=payload, srv=tipo: self._aplicar_on_enter(srv, data), 0)

        threading.Thread(target=_fetch, daemon=True).start()

    def _aplicar_on_enter(self, tipo, payload):
        self._cargando_pago = False
        PRECIOS = (payload or {}).get("precios") or self.obtener_precios()
        self._abogado_data_cache = (payload or {}).get("abogado_data")
        data = PRECIOS.get(tipo, PRECIOS["chat"])

        self.ids.lbl_precio_grande.text = data["texto"]
        self.ids.lbl_tipo_desc.text = DESCRIPCIONES.get(tipo, "")
        self.ids.btn_pago_unico.text = f"CONFIRMAR {data['titulo']}  •  {data['texto']}"
        self.ids.btn_pago_unico.background_color = data["color"]
        self.ids.btn_pago_unico.disabled = False

        precio = data["precio"]
        self.ids.lbl_resumen.text = (
            f"Servicio: {data['titulo']}\n"
            f"Precio: ${precio:,.0f}\n"
            f"Acceso inmediato luego del pago"
        )

        self._PRECIOS_CACHE = PRECIOS

    def pagar(self):
        btn = self.ids.btn_pago_unico
        btn.disabled = True
        btn.text = "Procesando pago..."

        try:
            tipo = getattr(session, "tipo_servicio", "chat") or "chat"
            user = session.current_user or {}
            abogado_email = getattr(session, "abogado_seleccionado", "") or ""

            if not user.get("uid") or not abogado_email:
                self.ids.lbl_error_mp.text = "Faltan datos de la consulta"
                return

            abogado_data = self._abogado_data_cache or fb.obtener_usuario_por_email(abogado_email)
            if not abogado_data:
                self.ids.lbl_error_mp.text = "No se encontro el abogado"
                return

            precios = self.obtener_precios()
            precio = precios.get(tipo, precios["chat"])["precio"]

            session.pago_tipo = "consulta"
            session.pago_pending_abogado_uid = abogado_data.get("uid")
            session.pago_pending_abogado_email = abogado_data.get("email", abogado_email)
            session.pago_pending_cliente_uid = user.get("uid")
            session.pago_pending_cliente_email = user.get("email", "")
            session.pago_pending_precio = precio
            session.current_consulta_id = None
            session.guardar()

            mp_screen = self.manager.get_screen("pago_mp")
            if hasattr(mp_screen, "preparar_pago_consulta"):
                mp_screen.preparar_pago_consulta({
                    "abogado_uid": abogado_data.get("uid"),
                    "abogado_email": abogado_data.get("email", abogado_email),
                    "cliente_uid": user.get("uid"),
                    "cliente_email": user.get("email", ""),
                    "tipo_servicio": tipo,
                    "monto": precio,
                    "area": getattr(session, "area_legal", "") or "",
                })

            self.manager.current = "pago_mp"
        except Exception as e:
            self.ids.lbl_error_mp.text = f"Error al iniciar pago: {e}"
        finally:
            btn.disabled = False

            tipo = getattr(session, "tipo_servicio", "chat")
            data = self._PRECIOS_CACHE.get(tipo, self._PRECIOS_CACHE["chat"])

            btn.text = f"CONFIRMAR {data['titulo']}  •  {data['texto']}"


    def volver(self):
        self.manager.current = "tipo"
