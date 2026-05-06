import session
from kivy.uix.screenmanager import Screen

SERVICIOS_HABILITADOS = {
    "disponible": {"chat", "video", "urgente"},
    "guardia":    {"urgente"},
    "ocupado":    set(),
}

PRECIOS = {
    "chat":    ("Chat",         "$1.000",  (0.18, 0.80, 0.44, 1)),
    "video":   ("Videollamada", "$3.000",  (0.18, 0.80, 0.44, 1)),
    "urgente": ("URGENTE",      "$5.000",  (0.91, 0.30, 0.24, 1)),
}

DESCRIPCIONES = {
    "chat":    "Consulta por mensajes de texto con el abogado",
    "video":   "Sesion por videollamada con el abogado",
    "urgente": "Atencion inmediata con prioridad maxima",
}


class PagoScreen(Screen):

    def on_enter(self):
        tipo    = getattr(session, "tipo_servicio", "chat") or "chat"
        abogado = session.abogado_seleccionado or ""

        self.ids.lbl_abogado_info.text = f"Abogado: {abogado}"

        nombre, precio, color = PRECIOS.get(tipo, PRECIOS["chat"])
        self.ids.btn_pago_unico.text             = f"{nombre}     {precio}"
        self.ids.btn_pago_unico.background_color = color
        self.ids.lbl_tipo_desc.text              = DESCRIPCIONES.get(tipo, "")
        self.ids.lbl_precio_grande.text          = precio

    def pagar(self):
        """Va a la pantalla de MercadoPago para procesar el pago real."""
        self.manager.current = "pago_mp"
