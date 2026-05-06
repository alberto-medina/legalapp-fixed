"""
pago_mp.py - MercadoPago + cobro 5% plataforma al momento del pago
"""
import json
import session
from database import get_connection, acreditar_honorario
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock

MP_ACCESS_TOKEN = "TEST-TU-ACCESS-TOKEN-AQUI"
MP_API_URL = "https://api.mercadopago.com/checkout/preferences"

PRECIOS_NUM = {"chat": 1000, "video": 3000, "urgente": 5000}
PRECIOS_STR = {"chat": "$1.000", "video": "$3.000", "urgente": "$5.000"}


def _crear_preferencia(tipo, abogado, user_email):
    try:
        import urllib.request
        monto = PRECIOS_NUM.get(tipo, 1000)
        body  = json.dumps({
            "items": [{
                "title":       f"Consulta {tipo} - Legal App",
                "quantity":    1,
                "unit_price":  monto,
                "currency_id": "ARS",
            }],
            "payer": {"email": user_email},
            "external_reference": f"{user_email}|{abogado}|{tipo}",
        }).encode("utf-8")
        req = urllib.request.Request(
            MP_API_URL, data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {MP_ACCESS_TOKEN}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("init_point"), data.get("id")
    except Exception as e:
        print("MP ERROR:", e)
        return None, None


def _abrir_url(url):
    try:
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

        self.ids.lbl_abogado_mp.text    = f"Abogado: {abogado}"
        self.ids.lbl_precio_mp.text     = PRECIOS_STR.get(tipo, "$0")
        self.ids.lbl_tipo_mp.text       = f"Consulta {tipo}"
        self.ids.lbl_estado_mp.text     = "Preparando pago..."
        self.ids.btn_ir_mp.disabled     = True
        self.ids.btn_confirmar.disabled = True

        Clock.schedule_once(
            lambda dt: self._generar_preferencia(
                tipo, abogado, user[2] if user else ""
            ),
            0.2,
        )

    def _generar_preferencia(self, tipo, abogado, user_email):
        init_point, _ = _crear_preferencia(tipo, abogado, user_email)
        if init_point:
            self._init_point = init_point
            self.ids.lbl_estado_mp.text  = "Link de pago listo"
            self.ids.lbl_estado_mp.color = (0.18, 0.80, 0.44, 1)
            self.ids.btn_ir_mp.disabled  = False
            self.ids.btn_confirmar.disabled = False
        else:
            self.ids.lbl_estado_mp.text  = (
                "Sin conexion a MP. Usa 'Confirmar demo' para continuar."
            )
            self.ids.lbl_estado_mp.color = (0.85, 0.55, 0.05, 1)
            self.ids.btn_confirmar.disabled = False

    def ir_a_pagar(self):
        if self._init_point:
            _abrir_url(self._init_point)

    def confirmar_pago(self):
        """
        Crea la consulta, cobra el 5% de plataforma AHORA
        y acredita el 95% al saldo del abogado.
        """
        tipo    = getattr(session, "tipo_servicio", "chat") or "chat"
        user    = session.current_user
        abogado = session.abogado_seleccionado

        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO consultas (user_email, abogado, estado, tipo_servicio)
            VALUES (?, ?, ?, ?)
        """, (user[2], abogado, "pagado", tipo))
        session.current_consulta_id = c.lastrowid
        conn.commit()
        conn.close()

        # COBRO 5% plataforma al momento del pago
        # acreditar_honorario descuenta el 5% y acredita el 95% al abogado
        monto_neto, comision = acreditar_honorario(abogado, tipo)
        print(f"PAGO PROCESADO: neto abogado=${monto_neto}, "
              f"comision plataforma=${comision}")

        if tipo == "video":
            self.manager.current = "videollamada"
        else:
            self.manager.current = "chat"

    def volver(self):
        self.manager.current = "pago"
