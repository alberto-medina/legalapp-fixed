"""
pago_mp.py  --  Integracion MercadoPago
------------------------------------------------
Flujo:
  1. Al entrar genera una preferencia MP via API REST
  2. Muestra el link de pago dentro de la app (WebView en Android,
     o abre el navegador en desktop como fallback)
  3. El boton "Ya pague" confirma el pago y avanza al chat

Para produccion reemplaza ACCESS_TOKEN con tu token real de MP.
En sandbox usa el token de prueba de tu cuenta de desarrollador:
  https://www.mercadopago.com.ar/developers
"""

import json
import session
from database import get_connection
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

# -- CONFIGURACION ------------------------------------------------
# Reemplazar con tu Access Token real de MercadoPago
MP_ACCESS_TOKEN = "TEST-TU-ACCESS-TOKEN-AQUI"

MP_API_URL = "https://api.mercadopago.com/checkout/preferences"

PRECIOS_NUM = {
    "chat":    1000,
    "video":   3000,
    "urgente": 5000,
}

PRECIOS_STR = {
    "chat":    "$1.000",
    "video":   "$3.000",
    "urgente": "$5.000",
}
# -----------------------------------------------------------------


def _crear_preferencia(tipo, abogado, user_email):
    """
    Llama a la API de MercadoPago y devuelve (init_point, preference_id).
    Devuelve (None, None) si falla.
    """
    try:
        import urllib.request
        monto = PRECIOS_NUM.get(tipo, 1000)
        body  = json.dumps({
            "items": [{
                "title":      f"Consulta {tipo} - Legal App",
                "quantity":   1,
                "unit_price": monto,
                "currency_id": "ARS",
            }],
            "payer": {"email": user_email},
            "external_reference": f"{user_email}|{abogado}|{tipo}",
            "back_urls": {
                "success": "https://legalapp.example/success",
                "failure": "https://legalapp.example/failure",
            },
            "auto_return": "approved",
        }).encode("utf-8")

        req = urllib.request.Request(
            MP_API_URL,
            data=body,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("init_point"), data.get("id")
    except Exception as e:
        print("MP ERROR:", e)
        return None, None


def _abrir_url(url):
    """Abre el link de pago: WebView en Android, navegador en desktop."""
    try:
        # Android / iOS con plyer
        from plyer import utils
        utils.open_url(url)
        return
    except Exception:
        pass
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception as e:
        print("No se pudo abrir el link:", e)


class PagoMPScreen(Screen):

    _init_point = None

    def on_enter(self):
        tipo    = getattr(session, "tipo_servicio", "chat") or "chat"
        abogado = session.abogado_seleccionado or ""
        user    = session.current_user

        self.ids.lbl_abogado_mp.text   = f"Abogado: {abogado}"
        self.ids.lbl_precio_mp.text    = PRECIOS_STR.get(tipo, "$0")
        self.ids.lbl_tipo_mp.text      = f"Consulta {tipo}"
        self.ids.lbl_estado_mp.text    = "Preparando pago..."
        self.ids.btn_ir_mp.disabled    = True
        self.ids.btn_confirmar.disabled = True

        # Generar preferencia en background para no bloquear la UI
        Clock.schedule_once(
            lambda dt: self._generar_preferencia(tipo, abogado,
                                                  user[2] if user else ""),
            0.2,
        )

    def _generar_preferencia(self, tipo, abogado, user_email):
        init_point, pref_id = _crear_preferencia(tipo, abogado, user_email)
        if init_point:
            self._init_point = init_point
            self.ids.lbl_estado_mp.text     = "Link de pago listo"
            self.ids.lbl_estado_mp.color    = (0.18, 0.80, 0.44, 1)
            self.ids.btn_ir_mp.disabled     = False
            self.ids.btn_confirmar.disabled = False
        else:
            # Fallback: si falla la API (token de prueba / sin internet)
            # permite igual crear la consulta como demo
            self.ids.lbl_estado_mp.text  = (
                "Sin conexion a MP. Usa 'Confirmar demo' para continuar."
            )
            self.ids.lbl_estado_mp.color = (0.85, 0.55, 0.05, 1)
            self.ids.btn_confirmar.disabled = False

    def ir_a_pagar(self):
        """Abre el link de MercadoPago en el navegador / webview."""
        if self._init_point:
            _abrir_url(self._init_point)

    def confirmar_pago(self):
        """El usuario confirma que ya pago. Crea la consulta y va al chat."""
        tipo    = getattr(session, "tipo_servicio", "chat") or "chat"
        user    = session.current_user
        abogado = session.abogado_seleccionado

        conn = get_connection()
        c    = conn.cursor()
        c.execute("""
            INSERT INTO consultas (user_email, abogado, estado, tipo_servicio)
            VALUES (?, ?, ?, ?)
        """, (user[2], abogado, "pagado", tipo))
        session.current_consulta_id = c.lastrowid
        conn.commit()
        conn.close()

        # Si es videollamada, ir a la pantalla de videollamada
        if tipo == "video":
            self.manager.current = "videollamada"
        else:
            self.manager.current = "chat"

    def volver(self):
        self.manager.current = "pago"
