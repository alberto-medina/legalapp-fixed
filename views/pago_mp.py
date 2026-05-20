import json
import session
import firebase_config as fb
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.utils import platform

# ============================================================
# CREDENCIALES DE MERCADOPAGO - APP "LegalApp Pro"
# Creada en cuenta real de Alberto Esteban Medina
# ============================================================
MP_PUBLIC_KEY = "APP_USR-49bdd339-b519-4773-ae55-6412e0c5c494"
MP_ACCESS_TOKEN = "APP_USR-5938797624128997-051723-c3ad40c853475d8fadcb362e38902388-547885776"
MP_API_URL = "https://api.mercadopago.com/checkout/preferences"
MP_PAYMENTS_URL = "https://api.mercadopago.com/v1/payments/search"

PRECIOS_NUM = {"chat": 1000, "video": 3000, "urgente": 5000}
PRECIOS_STR = {"chat": "$1.000", "video": "$3.000", "urgente": "$5.000"}


def _crear_preferencia(tipo, abogado_email, user_email):
    """
    Crea una preferencia de pago en MercadoPago.
    Retorna: (init_point, preference_id) o (None, None) si falla.
    """
    try:
        import requests
        monto = PRECIOS_NUM.get(tipo, 1000)

        body = {
            "items": [{
                "title": f"Consulta {tipo} - Legal App Pro",
                "quantity": 1,
                "unit_price": float(monto),
                "currency_id": "ARS",
            }],
            "payer": {
                "email": user_email,
                "name": user_email.split('@')[0] if user_email else "Cliente",
            },
            "external_reference": f"{user_email}|{abogado_email}|{tipo}",
            "back_urls": {
                "success": "legalapp://pago/success",
                "failure": "legalapp://pago/failure",
                "pending": "legalapp://pago/pending",
            },
            "auto_return": "approved",
            "notification_url": "https://us-central1-legalapp-pro.cloudfunctions.net/mp_webhook",
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
        }

        resp = requests.post(MP_API_URL, json=body, headers=headers, timeout=15)

        if resp.status_code == 201:
            data = resp.json()
            return data.get("init_point"), data.get("id")
        else:
            print(f"MP ERROR {resp.status_code}: {resp.text}")
            return None, None

    except Exception as e:
        print("MP ERROR:", e)
        return None, None


def _verificar_pago_mp(external_reference):
    """
    Consulta a MP si hay pagos aprobados para esta external_reference.
    Retorna True si hay al menos un pago con estado 'approved'.
    """
    try:
        import requests
        headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
        params = {"external_reference": external_reference, "status": "approved"}

        resp = requests.get(MP_PAYMENTS_URL, headers=headers, params=params, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            pagos = data.get("results", [])
            return len(pagos) > 0
        return False
    except Exception as e:
        print("ERROR verificando pago:", e)
        return False


def _abrir_url(url):
    """Abre una URL en el navegador del dispositivo."""
    try:
        if platform == 'android':
            from jnius import autoclass
            Intent = autoclass('android.content.Intent')
            Uri = autoclass('android.net.Uri')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')

            intent = Intent(Intent.ACTION_VIEW)
            intent.setData(Uri.parse(url))
            PythonActivity.mActivity.startActivity(intent)
            return
    except Exception as e:
        print("Android intent error:", e)

    try:
        import webbrowser
        webbrowser.open(url)
    except Exception as e:
        print("No se pudo abrir el link:", e)


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

    def on_enter(self):
        # Recuperar consulta: primero session, si no, buscar en Firestore
        consulta = self._recuperar_consulta()

        if not consulta:
            self.ids.lbl_estado_mp.text = "Error: No hay consulta activa. Volvé a crear una."
            self.ids.lbl_estado_mp.color = (0.85, 0.30, 0.30, 1)
            self.ids.btn_ir_mp.disabled = True
            self.ids.btn_confirmar.disabled = True
            self.ids.btn_verificar.disabled = True
            return

        self._consulta_id = consulta.get('id')
        self._tipo_servicio = consulta.get('tipo_servicio', 'chat')
        self._abogado_email = consulta.get('abogado_email', '')
        self._abogado_uid = consulta.get('abogado_uid')
        self._cliente_uid = consulta.get('cliente_uid')
        self._pago_verificado = False

        # Guardar en session para compatibilidad
        session.current_consulta_id = self._consulta_id
        session.tipo_servicio = self._tipo_servicio
        session.abogado_seleccionado = self._abogado_email

        user = session.current_user

        self.ids.lbl_abogado_mp.text = f"Abogado: {self._abogado_email}"
        self.ids.lbl_precio_mp.text = PRECIOS_STR.get(self._tipo_servicio, "$0")
        self.ids.lbl_tipo_mp.text = f"Consulta {self._tipo_servicio.upper()}"
        self.ids.lbl_estado_mp.text = "Generando link de pago..."
        self.ids.lbl_estado_mp.color = (0.55, 0.50, 0.65, 1)
        self.ids.btn_ir_mp.disabled = True
        self.ids.btn_confirmar.disabled = True
        self.ids.btn_confirmar.text = "YA PAGUE"
        self.ids.btn_verificar.disabled = True
        self.ids.btn_verificar.text = "VERIFICAR PAGO"

        # Generar preferencia con delay para que la UI se actualice
        Clock.schedule_once(
            lambda dt: self._generar_preferencia(self._tipo_servicio, self._abogado_email, user.get('email', '') if user else ""),
            0.3,
        )

    def _recuperar_consulta(self):
        """Recupera la consulta activa del usuario desde session o Firestore."""
        # Primero intentar session
        if session.current_consulta_id:
            consulta = fb.obtener_consulta(session.current_consulta_id)
            if consulta and consulta.get('estado') == 'pendiente':
                print(f"CONSULTA RECUPERADA DE SESSION: {session.current_consulta_id}")
                return consulta

        # Si no hay session, buscar en Firestore la ultima consulta pendiente del usuario
        user = session.current_user
        if not user:
            return None

        uid = user.get('uid')
        consultas = fb.obtener_consultas_usuario(uid, 'cliente')

        # Buscar la primera consulta pendiente (la mas reciente)
        for cid, cdata in consultas:
            if cdata.get('estado') == 'pendiente':
                cdata['id'] = cid
                print(f"CONSULTA RECUPERADA DE FIRESTORE: {cid}")
                return cdata

        return None

    def _generar_preferencia(self, tipo, abogado, user_email):
        init_point, pref_id = _crear_preferencia(tipo, abogado, user_email)

        if init_point:
            self._init_point = init_point
            self._preference_id = pref_id
            self._external_reference = f"{user_email}|{abogado}|{tipo}"
            self.ids.lbl_estado_mp.text = "✓ Link de pago listo. Abrí MP y pagá."
            self.ids.lbl_estado_mp.color = (0.18, 0.80, 0.44, 1)
            self.ids.btn_ir_mp.disabled = False
            self.ids.btn_confirmar.disabled = True  # DESHABILITADO hasta verificar
            self.ids.btn_confirmar.text = "YA PAGUE"
            self.ids.btn_verificar.disabled = False  # Habilitar verificar
            self.ids.btn_verificar.text = "VERIFICAR PAGO"
        else:
            self.ids.lbl_estado_mp.text = "⚠ Sin conexión a MP. Usá 'Confirmar pago' para continuar en modo demo."
            self.ids.lbl_estado_mp.color = (0.85, 0.55, 0.05, 1)
            self.ids.btn_ir_mp.disabled = True
            self.ids.btn_confirmar.disabled = False  # En modo demo, habilitado
            self.ids.btn_confirmar.text = "CONFIRMAR PAGO (DEMO)"
            self.ids.btn_verificar.disabled = True

    def ir_a_pagar(self):
        """Abre el link de MercadoPago en el navegador."""
        if self._init_point:
            _abrir_url(self._init_point)

    def verificar_pago(self):
        """Verifica en MP si el pago fue aprobado."""
        if not self._external_reference:
            self.ids.lbl_estado_mp.text = "Error: No hay referencia de pago"
            self.ids.lbl_estado_mp.color = (0.85, 0.30, 0.30, 1)
            return

        self.ids.lbl_estado_mp.text = "⏳ Verificando pago en MP..."
        self.ids.lbl_estado_mp.color = (0.55, 0.50, 0.65, 1)
        self.ids.btn_verificar.disabled = True
        self.ids.btn_verificar.text = "VERIFICANDO..."

        # Verificar en MP por external_reference
        pagado = _verificar_pago_mp(self._external_reference)

        if pagado:
            # Pago verificado por MP
            self._pago_verificado = True
            self.ids.lbl_estado_mp.text = "✓ Pago verificado por MP. Apretá 'Ya Pagué' para continuar."
            self.ids.lbl_estado_mp.color = (0.18, 0.80, 0.44, 1)
            self.ids.btn_confirmar.disabled = False
            self.ids.btn_confirmar.text = "YA PAGUE ✓"
            self.ids.btn_verificar.disabled = True
            self.ids.btn_verificar.text = "PAGO VERIFICADO"
        else:
            # No se encontró pago aprobado
            self.ids.lbl_estado_mp.text = "⚠ MP no confirma el pago aún. Pagá en MP y volvé a verificar."
            self.ids.lbl_estado_mp.color = (0.85, 0.55, 0.05, 1)
            self.ids.btn_verificar.disabled = False
            self.ids.btn_verificar.text = "VERIFICAR PAGO"

    def confirmar_pago(self):
        """
        Confirma el pago y actualiza la consulta a 'pagado'.
        Notifica al abogado que tiene una consulta pagada en espera.
        """
        if not self._consulta_id:
            self.ids.lbl_estado_mp.text = "Error: No hay consulta activa"
            self.ids.lbl_estado_mp.color = (0.85, 0.30, 0.30, 1)
            return

        # Actualizar estado a 'pagado'
        fb.actualizar_estado_consulta(self._consulta_id, 'pagado')

        # Notificar al abogado que tiene consulta pagada en espera
        if self._abogado_uid:
            fb.notificar_consulta_pagada(self._abogado_uid, self._tipo_servicio, PRECIOS_NUM.get(self._tipo_servicio, 1000))

        # Acreditar honorarios al abogado
        if self._abogado_uid:
            monto_neto, comision = fb.acreditar_honorario(self._abogado_uid, self._tipo_servicio)
            print(f"PAGO PROCESADO: neto abogado=${monto_neto}, comision plataforma=${comision}")

        # Deshabilitar boton de MP para evitar pagar dos veces
        self.ids.btn_ir_mp.disabled = True
        self.ids.btn_ir_mp.opacity = 0.5

        # Mostrar mensaje de espera al cliente
        self.ids.lbl_estado_mp.text = "✓ Pago confirmado. Esperando que el abogado acepte la consulta..."
        self.ids.lbl_estado_mp.color = (0.18, 0.80, 0.44, 1)
        self.ids.btn_confirmar.disabled = True
        self.ids.btn_confirmar.text = "PAGO CONFIRMADO"
        self.ids.btn_verificar.disabled = True

        # Escuchar cambios en la consulta para saber cuando el abogado acepta
        self._escuchar_aceptacion(self._consulta_id)

    def _escuchar_aceptacion(self, consulta_id):
        """Escucha cuando el abogado cambia el estado a 'en_curso'."""
        def check_estado(dt):
            consulta = fb.obtener_consulta(consulta_id)
            if not consulta:
                return False

            estado = consulta.get('estado', '')
            if estado == 'en_curso':
                # Abogado aceptó, redirigir al cliente
                tipo = consulta.get('tipo_servicio', 'chat')
                if tipo == "video":
                    self.manager.current = "videollamada"
                else:
                    self.manager.current = "chat"
                return False
            elif estado == 'finalizado':
                self.ids.lbl_estado_mp.text = "La consulta fue cancelada"
                self.ids.lbl_estado_mp.color = (0.85, 0.30, 0.30, 1)
                return False
            return True

        Clock.schedule_interval(check_estado, 2)

    def volver(self):
        self.manager.current = "pago"