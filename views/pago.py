import session

from kivy.uix.screenmanager import Screen
from database import PRECIOS_CONSULTA


PRECIOS = {
    "chat": {
        "titulo": "Chat",
        "precio": 1000,
        "texto": "$1.000",
        "color": (0.18, 0.80, 0.44, 1),
    },

    "video": {
        "titulo": "Videollamada",
        "precio": 3000,
        "texto": "$3.000",
        "color": (0.18, 0.80, 0.44, 1),
    },

    "urgente": {
        "titulo": "URGENTE",
        "precio": 5000,
        "texto": "$5.000",
        "color": (0.91, 0.30, 0.24, 1),
    },
}


DESCRIPCIONES = {

    "chat":
    "Consulta por mensajes privados con el abogado.",

    "video":
    "Videollamada privada para explicar el caso en tiempo real.",

    "urgente":
    "Atencion inmediata prioritaria para situaciones urgentes.",
}


class PagoScreen(Screen):

    # =====================================================
    # ENTER
    # =====================================================

    def on_enter(self):

        tipo = getattr(session, "tipo_servicio", "chat") or "chat"

        abogado = (
            getattr(session, "abogado_seleccionado", "")
            or "No seleccionado"
        )

        area = (
            getattr(session, "area_legal", "")
            or "-"
        )

        data = PRECIOS.get(tipo, PRECIOS["chat"])

        # =================================================
        # INFO
        # =================================================

        self.ids.lbl_abogado_info.text = (
            f"Abogado: {abogado}\n"
            f"Especialidad: {area}"
        )

        self.ids.lbl_precio_grande.text = data["texto"]

        self.ids.lbl_tipo_desc.text = DESCRIPCIONES.get(
            tipo,
            ""
        )

        self.ids.btn_pago_unico.text = (
            f"CONFIRMAR {data['titulo']}  •  {data['texto']}"
        )

        self.ids.btn_pago_unico.background_color = data["color"]

        # =================================================
        # RESUMEN
        # =================================================

        precio = data["precio"]

        self.ids.lbl_resumen.text = (
            f"Servicio: {data['titulo']}\n"
            f"Precio: ${precio:,.0f}\n"
            f"Acceso inmediato luego del pago"
        )

        # =================================================
        # ERROR MP
        # =================================================

        self.ids.lbl_error_mp.text = ""

    # =====================================================
    # PAGAR
    # =====================================================

    def pagar(self):

        btn = self.ids.btn_pago_unico

        btn.disabled = True
        btn.text = "Procesando pago..."

        try:

            # ACA DESPUES VA MERCADOPAGO REAL
            self.manager.current = "pago_mp"

        except Exception as e:

            self.ids.lbl_error_mp.text = (
                f"Error al iniciar pago: {e}"
            )

        finally:

            btn.disabled = False

            tipo = getattr(
                session,
                "tipo_servicio",
                "chat"
            )

            data = PRECIOS.get(tipo, PRECIOS["chat"])

            btn.text = (
                f"CONFIRMAR {data['titulo']}  •  {data['texto']}"
            )

    # =====================================================
    # VOLVER
    # =====================================================

    def volver(self):

        self.manager.current = "tipo"