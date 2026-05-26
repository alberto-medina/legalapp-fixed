import os
import json
import requests

from dotenv import load_dotenv

import session
import supabase_config as fb

from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.utils import platform

# ============================================================
# LOAD ENV
# ============================================================

load_dotenv()

# ============================================================
# MERCADOPAGO CONFIG
# ============================================================

MP_PUBLIC_KEY = os.getenv("MP_PUBLIC_KEY", "")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")

MP_API_URL = "https://api.mercadopago.com/checkout/preferences"
MP_PAYMENTS_URL = "https://api.mercadopago.com/v1/payments/search"

# ============================================================
# PRECIOS
# ============================================================

PRECIOS_NUM = {
    "chat": 1000,
    "video": 3000,
    "urgente": 5000
}

PRECIOS_STR = {
    "chat": "$1.000",
    "video": "$3.000",
    "urgente": "$5.000"
}

# ============================================================
# CREAR PREFERENCIA
# ============================================================

def _crear_preferencia(tipo, abogado_email, user_email):

    try:

        monto = PRECIOS_NUM.get(tipo, 1000)

        body = {
            "items": [{
                "title": f"Consulta {tipo} - Legal App Pro",
                "quantity": 1,
                "unit_price": float(monto),
                "currency_id": "ARS"
            }],
            "payer": {
                "email": user_email,
                "name": user_email.split("@")[0]
            },
            "external_reference": (
                f"{user_email}|{abogado_email}|{tipo}"
            ),
            "back_urls": {
                "success": "legalapp://pago/success",
                "failure": "legalapp://pago/failure",
                "pending": "legalapp://pago/pending"
            },
            "auto_return": "approved"
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MP_ACCESS_TOKEN}"
        }

        response = requests.post(
            MP_API_URL,
            json=body,
            headers=headers,
            timeout=20
        )

        if response.status_code in [200, 201]:

            data = response.json()

            return (
                data.get("init_point"),
                data.get("id")
            )

        print("MP ERROR:", response.text)

        return None, None

    except Exception as e:

        print("ERROR CREANDO PREFERENCIA:", e)

        return None, None

# ============================================================
# VERIFICAR PAGO
# ============================================================

def _verificar_pago_mp(external_reference):

    try:

        headers = {
            "Authorization": f"Bearer {MP_ACCESS_TOKEN}"
        }

        params = {
            "external_reference": external_reference,
            "status": "approved"
        }

        response = requests.get(
            MP_PAYMENTS_URL,
            headers=headers,
            params=params,
            timeout=15
        )

        if response.status_code == 200:

            data = response.json()

            pagos = data.get("results", [])

            return len(pagos) > 0

        return False

    except Exception as e:

        print("ERROR verificando pago:", e)

        return False

# ============================================================
# ABRIR URL
# ============================================================

def _abrir_url(url):

    try:

        if platform == "android":

            from jnius import autoclass

            Intent = autoclass(
                "android.content.Intent"
            )

            Uri = autoclass(
                "android.net.Uri"
            )

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            intent = Intent(Intent.ACTION_VIEW)

            intent.setData(Uri.parse(url))

            PythonActivity.mActivity.startActivity(intent)

            return

    except Exception as e:

        print("ANDROID URL ERROR:", e)

    try:

        import webbrowser

        webbrowser.open(url)

    except Exception as e:

        print("WEB URL ERROR:", e)

# ============================================================
# SCREEN
# ============================================================

class PagoMPScreen(Screen):

    _init_point = None
    _preference_id = None
    _external_reference = None
    _consulta_id = None

    _tipo_servicio = None
    _abogado_email = None
    _abogado_uid = None
    _cliente_uid = None

    _pago_verificado = False

    # ========================================================
    # ENTER
    # ========================================================

    def on_enter(self):

        consulta = self._recuperar_consulta()

        if not consulta:

            self.ids.lbl_estado_mp.text = (
                "No hay consulta activa"
            )

            self.ids.lbl_estado_mp.color = (
                0.90,
                0.25,
                0.25,
                1
            )

            self.ids.btn_ir_mp.disabled = True
            self.ids.btn_confirmar.disabled = True
            self.ids.btn_verificar.disabled = True

            return

        self._consulta_id = consulta.get("id")

        self._tipo_servicio = consulta.get(
            "tipo_servicio",
            "chat"
        )

        self._abogado_email = consulta.get(
            "abogado_email",
            ""
        )

        self._abogado_uid = consulta.get(
            "abogado_uid"
        )

        self._cliente_uid = consulta.get(
            "cliente_uid"
        )

        self._pago_verificado = False

        session.current_consulta_id = (
            self._consulta_id
        )

        session.tipo_servicio = (
            self._tipo_servicio
        )

        session.abogado_seleccionado = (
            self._abogado_email
        )

        user = session.current_user or {}

        self.ids.lbl_abogado_mp.text = (
            f"Abogado: {self._abogado_email}"
        )

        self.ids.lbl_precio_mp.text = (
            PRECIOS_STR.get(
                self._tipo_servicio,
                "$0"
            )
        )

        self.ids.lbl_tipo_mp.text = (
            f"Consulta {self._tipo_servicio.upper()}"
        )

        self.ids.lbl_estado_mp.text = (
            "Generando link de pago..."
        )

        self.ids.lbl_estado_mp.color = (
            0.55,
            0.50,
            0.65,
            1
        )

        self.ids.btn_ir_mp.disabled = True
        self.ids.btn_confirmar.disabled = True
        self.ids.btn_verificar.disabled = True

        Clock.schedule_once(
            lambda dt: self._generar_preferencia(
                self._tipo_servicio,
                self._abogado_email,
                user.get("email", "")
            ),
            0.3
        )

    # ========================================================
    # RECUPERAR CONSULTA
    # ========================================================

    def _recuperar_consulta(self):

        if session.current_consulta_id:

            consulta = fb.obtener_consulta(
                session.current_consulta_id
            )

            if consulta:

                return consulta

        user = session.current_user

        if not user:
            return None

        uid = user.get("uid")

        consultas = fb.obtener_consultas_usuario(
            uid,
            "cliente"
        )

        for cid, cdata in consultas:

            if cdata.get("estado") == "pendiente":

                cdata["id"] = cid

                return cdata

        return None

    # ========================================================
    # GENERAR PREFERENCIA
    # ========================================================

    def _generar_preferencia(
        self,
        tipo,
        abogado,
        user_email
    ):

        init_point, pref_id = _crear_preferencia(
            tipo,
            abogado,
            user_email
        )

        if init_point:

            self._init_point = init_point

            self._preference_id = pref_id

            self._external_reference = (
                f"{user_email}|{abogado}|{tipo}"
            )

            self.ids.lbl_estado_mp.text = (
                "Link de pago listo"
            )

            self.ids.lbl_estado_mp.color = (
                0.18,
                0.80,
                0.44,
                1
            )

            self.ids.btn_ir_mp.disabled = False
            self.ids.btn_verificar.disabled = False

        else:

            self.ids.lbl_estado_mp.text = (
                "Error conectando MercadoPago"
            )

            self.ids.lbl_estado_mp.color = (
                0.90,
                0.25,
                0.25,
                1
            )

    # ========================================================
    # IR A PAGAR
    # ========================================================

    def ir_a_pagar(self):

        if self._init_point:
            _abrir_url(self._init_point)

    # ========================================================
    # VERIFICAR PAGO
    # ========================================================

    def verificar_pago(self):

        if not self._external_reference:
            return

        self.ids.lbl_estado_mp.text = (
            "Verificando pago..."
        )

        pagado = _verificar_pago_mp(
            self._external_reference
        )

        if pagado:

            self._pago_verificado = True

            self.ids.lbl_estado_mp.text = (
                "Pago verificado"
            )

            self.ids.lbl_estado_mp.color = (
                0.18,
                0.80,
                0.44,
                1
            )

            self.ids.btn_confirmar.disabled = False
            self.ids.btn_verificar.disabled = True

        else:

            self.ids.lbl_estado_mp.text = (
                "Pago no encontrado"
            )

            self.ids.lbl_estado_mp.color = (
                0.90,
                0.25,
                0.25,
                1
            )

    # ========================================================
    # CONFIRMAR PAGO
    # ========================================================

    def confirmar_pago(self):

        if not self._consulta_id:
            return

        fb.actualizar_estado_consulta(
            self._consulta_id,
            "pagado"
        )

        if self._abogado_uid:

            fb.notificar_consulta_pagada(
                self._abogado_uid,
                self._tipo_servicio,
                PRECIOS_NUM.get(
                    self._tipo_servicio,
                    1000
                )
            )

            monto_neto, comision = (
                fb.acreditar_honorario(
                    self._abogado_uid,
                    self._tipo_servicio
                )
            )

            print(
                f"PAGO: abogado=${monto_neto} "
                f"comision=${comision}"
            )

        self.ids.lbl_estado_mp.text = (
            "Pago confirmado"
        )

        self.ids.lbl_estado_mp.color = (
            0.18,
            0.80,
            0.44,
            1
        )

        self.ids.btn_confirmar.disabled = True
        self.ids.btn_ir_mp.disabled = True
        self.ids.btn_verificar.disabled = True

        self._escuchar_aceptacion(
            self._consulta_id
        )

    # ========================================================
    # ESCUCHAR ACEPTACION
    # ========================================================

    def _escuchar_aceptacion(
        self,
        consulta_id
    ):

        def check_estado(dt):

            consulta = fb.obtener_consulta(
                consulta_id
            )

            if not consulta:
                return False

            estado = consulta.get("estado", "")

            if estado == "en_curso":

                tipo = consulta.get(
                    "tipo_servicio",
                    "chat"
                )

                if tipo == "video":
                    self.manager.current = (
                        "videollamada"
                    )
                else:
                    self.manager.current = "chat"

                return False

            return True

        Clock.schedule_interval(
            check_estado,
            2
        )

    # ========================================================
    # VOLVER
    # ========================================================

    def volver(self):

        self.manager.current = "pago"