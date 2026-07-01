import os
import requests
import threading

from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.utils import platform

import supabase_config as fb
import session

# --- CARGA DE CONFIGURACION (Android compatible) ---
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MP_ACCESS_TOKEN

MP_API_URL = "https://api.mercadopago.com/checkout/preferences"
MP_PAYMENTS_URL = "https://api.mercadopago.com/v1/payments/search"


def _crear_preferencia_suscripcion(uid, email, monto, especialidades):
    try:
        email = email or ""
        esp_str = ", ".join(especialidades) if especialidades else "General"
        body = {
            "items": [{
                "title": f"Suscripcion Legal App - {esp_str}",
                "quantity": 1,
                "unit_price": float(monto),
                "currency_id": "ARS"
            }],
            "payer": {
                "email": email,
                "name": email.split("@")[0] if "@" in email else "Abogado"
            },
            "external_reference": f"suscripcion|{uid}|{monto}",
            "back_urls": {
                "success": "https://www.mercadopago.com.ar/",
                "failure": "https://www.mercadopago.com.ar/",
                "pending": "https://www.mercadopago.com.ar/"
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MP_ACCESS_TOKEN}"
        }

        response = requests.post(MP_API_URL, json=body, headers=headers, timeout=20)

        if response.status_code in [200, 201]:
            data = response.json()
            return data.get("init_point"), data.get("id")

        print("MP ERROR:", response.text)
        return None, None

    except Exception as e:
        print("ERROR PREFERENCIA SUSCRIPCION:", e)
        return None, None


def _verificar_pago_suscripcion(external_reference):
    try:
        headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
        params = {"external_reference": external_reference, "status": "approved"}
        response = requests.get(MP_PAYMENTS_URL, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return len(data.get("results", [])) > 0
        return False
    except Exception as e:
        print("ERROR verificando suscripcion:", e)
        return False


def _abrir_url(url):
    try:
        if platform == "android":
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            Uri = autoclass("android.net.Uri")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            browser_packages = [
                "com.android.chrome",
                "com.google.android.apps.chrome",
                "com.brave.browser",
                "org.mozilla.firefox",
                "com.microsoft.emmx",
                "com.opera.browser",
                "com.android.browser",
            ]

            for package_name in browser_packages:
                try:
                    intent = Intent(Intent.ACTION_VIEW)
                    intent.addCategory(Intent.CATEGORY_BROWSABLE)
                    intent.setData(Uri.parse(url))
                    intent.setPackage(package_name)
                    PythonActivity.mActivity.startActivity(intent)
                    return
                except Exception:
                    pass

            intent = Intent(Intent.ACTION_VIEW)
            intent.addCategory(Intent.CATEGORY_BROWSABLE)
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


class PagoSuscripcionScreen(Screen):
    _init_point = None
    _external_reference = None
    _uid = None
    _email = None
    _monto = 0
    _especialidades = []
    _cargando_suscripcion = False

    def obtener_monto(self):
        monto_session = getattr(session, 'monto_suscripcion', None)
        if monto_session not in [None, "", 0]:
            try:
                return int(monto_session)
            except Exception:
                pass

        config = fb.obtener_configuracion() or {}

        try:
            return int(config.get("precio_suscripcion_base", 55000))
        except:
            return 55000

    def on_enter(self):
        if self._cargando_suscripcion:
            return

        self._cargando_suscripcion = True
        self._uid = (
            getattr(session, 'abogado_registrando_uid', None)
            or getattr(session, 'pending_uid', None)
            or (session.current_user or {}).get('uid')
        )
        self._email = (
            getattr(session, 'pending_email', None)
            or (session.current_user or {}).get('email', '')
        )

        self._monto = self.obtener_monto()
        self._especialidades = getattr(session, 'especialidades_abogado', [])

        if not self._uid:
            self._cargando_suscripcion = False
            self.ids.lbl_estado.text = "Error: no hay sesion activa"
            self.ids.lbl_estado.color = (0.90, 0.25, 0.25, 1)
            self.ids.btn_pagar.disabled = True
            self.ids.btn_verificar.disabled = True
            return

        esp_str = ", ".join(self._especialidades) if self._especialidades else "-"
        self.ids.lbl_especialidades.text = f"Especialidades: {esp_str}"
        self.ids.lbl_monto.text = f"Total: ${self._monto:,}"
        self.ids.lbl_estado.text = "Generando link de pago..."
        self.ids.lbl_estado.color = (0.55, 0.50, 0.65, 1)
        self.ids.btn_pagar.disabled = True
        self.ids.btn_verificar.disabled = True
        self.ids.btn_activar_manual.disabled = True

        def _fetch():
            try:
                if not self._email:
                    usuario = fb.obtener_usuario(self._uid)
                    self._email = (usuario or {}).get('email', '')
            except Exception as e:
                print(f"ERROR cargando email suscripcion: {e}")
            finally:
                Clock.schedule_once(lambda dt: self._post_carga_suscripcion(), 0)

        threading.Thread(target=_fetch, daemon=True).start()

    def _post_carga_suscripcion(self):
        if not self._email:
            self._cargando_suscripcion = False
            self.ids.lbl_estado.text = "Error: no hay email para MercadoPago"
            self.ids.lbl_estado.color = (0.90, 0.25, 0.25, 1)
            self.ids.btn_pagar.disabled = True
            self.ids.btn_verificar.disabled = True
            return

        Clock.schedule_once(lambda dt: self._generar_preferencia(), 0.1)

    def _generar_preferencia(self):
        def _worker():
            init_point, pref_id = _crear_preferencia_suscripcion(
                self._uid, self._email, self._monto, self._especialidades
            )
            Clock.schedule_once(lambda dt, init=init_point, pref=pref_id: self._aplicar_preferencia(init, pref), 0)

        threading.Thread(target=_worker, daemon=True).start()

    def _aplicar_preferencia(self, init_point, pref_id):
        self._cargando_suscripcion = False
        if init_point:
            self._init_point = init_point
            self._external_reference = f"suscripcion|{self._uid}|{self._monto}"
            self.ids.lbl_estado.text = "Link de pago listo"
            self.ids.lbl_estado.color = (0.18, 0.80, 0.44, 1)
            self.ids.btn_pagar.disabled = False
            self.ids.btn_verificar.disabled = False
            Clock.schedule_once(lambda dt: self.verificar_pago(silencioso=True), 0.8)
        else:
            self.ids.lbl_estado.text = "Error conectando MercadoPago\nPuede activar manualmente si pago por otro medio"
            self.ids.lbl_estado.color = (0.90, 0.55, 0.10, 1)
            self.ids.btn_activar_manual.disabled = False

    def ir_a_pagar(self):
        if self._init_point:
            _abrir_url(self._init_point)

    def verificar_pago(self, silencioso=False):
        if not self._external_reference:
            return

        if not silencioso:
            self.ids.lbl_estado.text = "Verificando pago..."
        pagado = _verificar_pago_suscripcion(self._external_reference)

        if pagado:
            self._activar_suscripcion()
        elif not silencioso:
            self.ids.lbl_estado.text = "Pago no encontrado. Intenta de nuevo."
            self.ids.lbl_estado.color = (0.90, 0.25, 0.25, 1)

    def activar_manual(self):
        self._activar_suscripcion()

    def _activar_suscripcion(self):
        import json
        from datetime import datetime

        try:
            datos = {
                "suscripcion_activa": True,
                "suscripcion_fecha": str(datetime.now()),
                "suscripcion_monto": self._monto,
                "aprobado": False,
                "estado_abogado": "disponible",
                "especialidades": json.dumps(self._especialidades),
            }

            if self._especialidades:
                datos["especialidad"] = self._especialidades[0]

            fb.actualizar_usuario(self._uid, datos)

            # Pago registrado: queda pendiente de aprobacion admin.
            session.current_user = None
            session.pending_uid = None
            session.pending_email = None
            session.abogado_registrando_uid = None
            session.guardar()

            self.ids.lbl_estado.text = "Pago confirmado. Tu cuenta queda pendiente de aprobacion."
            self.ids.lbl_estado.color = (0.18, 0.80, 0.44, 1)
            self.ids.btn_pagar.disabled = True
            self.ids.btn_verificar.disabled = True
            self.ids.btn_activar_manual.disabled = True

            Clock.schedule_once(
                lambda dt: setattr(self.manager, 'current', 'login'),
                2.0
            )

        except Exception as e:
            print(f"ERROR activando suscripcion: {e}")
            self.ids.lbl_estado.text = f"Error activando: {e}"
            self.ids.lbl_estado.color = (0.90, 0.25, 0.25, 1)

    def volver(self):
        self.manager.current = 'register_abogado'
