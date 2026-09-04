import os
import json
import time
import threading

import session
import supabase_config as fb

from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.utils import platform

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DEBUG
except Exception:
    DEBUG = False

def obtener_precios():
    config = fb.obtener_configuracion() or {}
    try:
        chat = int(config.get("precio_chat", 1000))
    except:
        chat = 1000
    try:
        video = int(config.get("precio_video", 3000))
    except:
        video = 3000
    try:
        urgente = int(config.get("precio_urgente", 5000))
    except:
        urgente = 5000
    return {
        "chat": chat,
        "video": video,
        "urgente": urgente
    }

def obtener_precios_str():
    p = obtener_precios()
    return {
        "chat": f"${p['chat']:,}",
        "video": f"${p['video']:,}",
        "urgente": f"${p['urgente']:,}"
    }

def _especialidades_extra_seleccionadas():
    valor = getattr(session, "especialidad_a_agregar", None)
    if isinstance(valor, list):
        return [str(v).strip() for v in valor if str(v).strip()]
    if valor:
        return [str(valor).strip()]
    return []

def _crear_preferencia(tipo, abogado_email, user_email, consulta_id=None, external_reference=None, monto_override=None):
    try:
        PRECIOS_NUM = obtener_precios()
        if tipo == "especialidad_extra":
            config = fb.obtener_configuracion() or {}
            try:
                monto_unit = int(config.get("precio_especialidad_extra", 10000))
            except:
                monto_unit = 10000
            seleccionadas = _especialidades_extra_seleccionadas()
            monto = monto_override or getattr(session, "pago_monto", None) or (max(1, len(seleccionadas)) * monto_unit)
            especialidad = ", ".join(seleccionadas) if seleccionadas else "Especialidad adicional"
            title = f"Especialidad adicional - {especialidad}"
            especialidad_ref = "__".join(seleccionadas) if seleccionadas else "especialidad"
            external_reference = f"especialidad_extra|{user_email}|{especialidad_ref}|{monto}"
        else:
            monto = monto_override or PRECIOS_NUM.get(tipo, 1000)
            title = f"Consulta {tipo} - Legal App Pro"
            external_reference = external_reference or f"consulta|{consulta_id}|{user_email}|{abogado_email}|{tipo}"

        return fb.mp_crear_preferencia(title, monto, user_email, external_reference)

    except Exception as e:
        print("ERROR CREANDO PREFERENCIA:", e)
        return None, None


def _verificar_pago_mp(external_reference, preference_id=None, payer_email=None, monto=None):
    try:
        aprobado, payment_id = fb.mp_verificar_pago(external_reference, preference_id)
        if payment_id:
            return True
        return bool(aprobado)
    except Exception as e:
        print("ERROR verificando pago:", e)
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
    _btn_reintentar = None
    _consulta_preparada = None
    _consulta_data = None
    _external_reference_seed = None
    _payment_id = None
    _consulta_estado_previo = None

    def preparar_pago_consulta(self, data):
        self._consulta_preparada = dict(data or {})

    def _usar_consulta_para_pago(self, consulta):
        if not consulta:
            return

        self._consulta_id = consulta.get("id")
        self._consulta_estado_previo = consulta.get("estado")
        self._consulta_data = dict(consulta)
        self._tipo_servicio = consulta.get("tipo_servicio", self._tipo_servicio)
        self._abogado_uid = consulta.get("abogado_uid", self._abogado_uid)
        self._abogado_email = consulta.get("abogado_email", self._abogado_email)
        self._cliente_uid = consulta.get("cliente_uid", self._cliente_uid)

        external_reference = consulta.get("external_reference")
        if external_reference:
            self._external_reference = external_reference
            self._external_reference_seed = external_reference
            session.pago_external_reference = external_reference

        session.current_consulta_id = self._consulta_id
        session.tipo_servicio = self._tipo_servicio
        session.abogado_seleccionado = self._abogado_email

    def _crear_consulta_pendiente_si_falta(self, data):
        if self._external_reference:
            consulta = fb.obtener_consulta_por_external_reference(
                self._external_reference
            )

            if consulta and consulta.get("_schema_error"):
                self.ids.lbl_estado_mp.text = "Falta configurar la referencia de pago en Supabase"
                self.ids.lbl_estado_mp.color = (0.90, 0.25, 0.25, 1)
                return False

            if consulta:
                if str(consulta.get("estado") or "").lower() != "finalizado":
                    self._usar_consulta_para_pago(consulta)
                    session.guardar()
                    return True

        if session.current_consulta_id:
            consulta = fb.obtener_consulta(session.current_consulta_id)
            if consulta and str(consulta.get("estado") or "").lower() != "finalizado":
                if self._external_reference and not consulta.get("external_reference"):
                    fb.actualizar_consulta(
                        session.current_consulta_id,
                        {"external_reference": self._external_reference}
                    )
                    consulta["external_reference"] = self._external_reference
                self._usar_consulta_para_pago(consulta)
                session.guardar()
                return True

        cliente_uid = data.get("cliente_uid") or self._cliente_uid
        abogado_uid = data.get("abogado_uid") or self._abogado_uid
        tipo = data.get("tipo_servicio") or self._tipo_servicio

        if cliente_uid and abogado_uid and tipo:
            consultas = fb.obtener_consultas_usuario(cliente_uid, "cliente")
            for cid, consulta in consultas:
                if (
                    consulta.get("estado") == "pendiente"
                    and consulta.get("abogado_uid") == abogado_uid
                    and consulta.get("tipo_servicio") == tipo
                ):
                    consulta["id"] = cid
                    if consulta.get("external_reference"):
                        self._external_reference = consulta.get("external_reference")
                        self._external_reference_seed = self._external_reference
                        session.pago_external_reference = self._external_reference
                    elif self._external_reference:
                        fb.actualizar_consulta(
                            cid,
                            {"external_reference": self._external_reference}
                        )
                        consulta["external_reference"] = self._external_reference

                    self._usar_consulta_para_pago(consulta)
                    session.guardar()
                    return True

        consulta_data = dict(data or {})
        consulta_data.pop("id", None)
        consulta_data.pop("created_at", None)
        consulta_data["estado"] = "pendiente"
        consulta_data["external_reference"] = self._external_reference

        ok, consulta_id = fb.crear_consulta(consulta_data)
        if not ok or not consulta_id:
            detalle = str(consulta_id or "")
            if len(detalle) > 80:
                detalle = detalle[:80] + "..."
            self.ids.lbl_estado_mp.text = f"Error creando consulta\n{detalle}"
            self.ids.lbl_estado_mp.color = (0.90, 0.25, 0.25, 1)
            return False

        consulta = fb.obtener_consulta(consulta_id) or dict(consulta_data)
        consulta["id"] = consulta_id
        self._usar_consulta_para_pago(consulta)
        session.guardar()
        return True

    def _armar_consulta_data_desde_session(self):
        user = session.current_user or {}
        abogado_uid = getattr(session, "pago_pending_abogado_uid", None)
        abogado_email = getattr(session, "pago_pending_abogado_email", None)
        cliente_uid = getattr(session, "pago_pending_cliente_uid", None) or user.get("uid")
        cliente_email = getattr(session, "pago_pending_cliente_email", None) or user.get("email", "")
        tipo = getattr(session, "tipo_servicio", "chat") or "chat"
        monto = getattr(session, "pago_pending_precio", None) or obtener_precios().get(tipo, 1000)

        if not abogado_uid or not cliente_uid:
            return None

        return {
            "abogado_uid": abogado_uid,
            "abogado_email": abogado_email or "",
            "cliente_uid": cliente_uid,
            "cliente_email": cliente_email or "",
            "tipo_servicio": tipo,
            "monto": monto,
            "area": getattr(session, "area_legal", "") or "",
        }

    def on_enter(self):
        if not self._consulta_preparada:
            session.cargar()

        if (
            getattr(session, 'pago_tipo', None) == 'especialidad_extra'
            or (
                getattr(session, 'especialidad_a_agregar', None)
                and getattr(session, 'pago_monto', None)
            )
        ):
            session.pago_tipo = 'especialidad_extra'
            session.guardar()
            self._iniciar_pago_especialidad_extra()
            return

        if self._consulta_preparada:
            self._iniciar_pago_consulta_preparada()
            return

        if getattr(session, "pago_tipo", None) == "consulta":
            data = self._armar_consulta_data_desde_session()
            if data:
                self._consulta_preparada = data
                self._iniciar_pago_consulta_preparada()
                return

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
        self._consulta_estado_previo = consulta.get("estado")

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
        session.guardar()

        user = session.current_user or {}

        PRECIOS_STR = obtener_precios_str()

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

    def _iniciar_pago_consulta_preparada(self):
        data = dict(self._consulta_preparada or {})
        self._consulta_preparada = None
        self._consulta_data = data

        self._consulta_id = None
        self._tipo_servicio = data.get("tipo_servicio", "chat") or "chat"
        self._abogado_email = data.get("abogado_email", "")
        self._abogado_uid = data.get("abogado_uid")
        self._cliente_uid = data.get("cliente_uid")
        self._pago_verificado = False
        self._payment_id = None
        self._consulta_estado_previo = None

        cliente_email = data.get("cliente_email", "")
        monto = data.get("monto", 0) or obtener_precios().get(self._tipo_servicio, 1000)
        self._external_reference_seed = getattr(session, "pago_external_reference", None)
        if not self._external_reference_seed:
            self._external_reference_seed = (
                f"consulta|{self._cliente_uid}|{self._abogado_uid}|"
                f"{self._tipo_servicio}|{int(time.time())}"
            )
        self._external_reference = self._external_reference_seed
        self._preference_id = getattr(session, "pago_preference_id", None)
        self._init_point = getattr(session, "pago_init_point", None)

        session.pago_tipo = "consulta"
        session.tipo_servicio = self._tipo_servicio
        session.abogado_seleccionado = self._abogado_email
        session.pago_pending_abogado_uid = self._abogado_uid
        session.pago_pending_abogado_email = self._abogado_email
        session.pago_pending_cliente_uid = self._cliente_uid
        session.pago_pending_cliente_email = cliente_email
        session.pago_pending_precio = monto
        session.pago_external_reference = self._external_reference_seed
        session.guardar()

        if not self._crear_consulta_pendiente_si_falta(data):
            self.ids.btn_ir_mp.disabled = True
            self.ids.btn_confirmar.disabled = True
            self.ids.btn_verificar.disabled = True
            return

        self.ids.lbl_abogado_mp.text = f"Abogado: {self._abogado_email}"
        self.ids.lbl_precio_mp.text = f"${int(monto):,}"
        self.ids.lbl_tipo_mp.text = f"Consulta {self._tipo_servicio.upper()}"
        self.ids.lbl_estado_mp.text = "Generando link de pago..."
        self.ids.lbl_estado_mp.color = (0.55, 0.50, 0.65, 1)
        self.ids.btn_ir_mp.disabled = True
        self.ids.btn_confirmar.disabled = True
        self.ids.btn_verificar.disabled = True

        if self._init_point:
            self.ids.lbl_estado_mp.text = "Link de pago listo"
            self.ids.lbl_estado_mp.color = (0.18, 0.80, 0.44, 1)
            self.ids.btn_ir_mp.disabled = False
            self.ids.btn_confirmar.disabled = False
            return

        Clock.schedule_once(
            lambda dt: self._generar_preferencia(
                self._tipo_servicio,
                self._abogado_email,
                cliente_email
            ),
            0.3
        )

    def _reconstruir_pago_consulta_desde_session(self):
        user = session.current_user or {}
        abogado_email = getattr(session, "abogado_seleccionado", "") or ""
        cliente_uid = user.get("uid")

        if not cliente_uid or not abogado_email:
            return False

        abogado_data = fb.obtener_usuario_por_email(abogado_email)
        if not abogado_data:
            return False

        tipo = getattr(session, "tipo_servicio", "chat") or "chat"
        precios = obtener_precios()

        session.pago_tipo = "consulta"
        session.pago_pending_abogado_uid = abogado_data.get("uid")
        session.pago_pending_abogado_email = abogado_data.get("email", abogado_email)
        session.pago_pending_cliente_uid = cliente_uid
        session.pago_pending_cliente_email = user.get("email", "")
        session.pago_pending_precio = precios.get(tipo, precios.get("chat", 1000))
        session.current_consulta_id = None
        session.guardar()
        return True

    def _iniciar_pago_especialidad_extra(self):
        user = session.current_user or {}
        email = user.get("email", "")
        seleccionadas = _especialidades_extra_seleccionadas()
        especialidad = ", ".join(seleccionadas) if seleccionadas else "Especialidad adicional"
        monto = getattr(session, "pago_monto", None)
        if not monto:
            config = fb.obtener_configuracion() or {}
            try:
                monto_unit = int(config.get("precio_especialidad_extra", 10000))
            except:
                monto_unit = 10000
            monto = max(1, len(seleccionadas)) * monto_unit
            session.pago_monto = monto
            session.guardar()

        self._consulta_id = None
        self._tipo_servicio = "especialidad_extra"
        self._abogado_email = email
        self._abogado_uid = user.get("uid")
        self._cliente_uid = None
        self._pago_verificado = False
        self._payment_id = None
        self._consulta_estado_previo = None
        self._external_reference = None

        self.ids.lbl_abogado_mp.text = f"Abogado: {email}"
        self.ids.lbl_precio_mp.text = f"${int(monto):,}"
        self.ids.lbl_tipo_mp.text = f"Agregar {especialidad}"
        self.ids.lbl_estado_mp.text = "Generando link de pago..."
        self.ids.lbl_estado_mp.color = (0.55, 0.50, 0.65, 1)
        self.ids.btn_ir_mp.disabled = True
        self.ids.btn_confirmar.disabled = True
        self.ids.btn_verificar.disabled = True

        Clock.schedule_once(
            lambda dt: self._generar_preferencia(
                "especialidad_extra",
                email,
                email
            ),
            0.3
        )

    def _recuperar_consulta(self):
        if self._consulta_preparada:
            data = dict(self._consulta_preparada)
            self._consulta_preparada = None
            data["estado"] = "pendiente"
            if not data.get("external_reference"):
                data["external_reference"] = (
                    getattr(session, "pago_external_reference", None)
                    or f"consulta|{data.get('cliente_uid')}|{data.get('abogado_uid')}|"
                    f"{data.get('tipo_servicio', 'chat')}|{int(time.time())}"
                )

            ok, consulta_id = fb.crear_consulta(data)
            if ok and consulta_id:
                session.current_consulta_id = consulta_id
                session.pago_pending_abogado_uid = None
                session.pago_pending_abogado_email = None
                session.pago_pending_cliente_uid = None
                session.pago_pending_cliente_email = None
                session.pago_pending_precio = None
                session.guardar()

                consulta = fb.obtener_consulta(consulta_id)
                if consulta:
                    return consulta

                data["id"] = consulta_id
                return data

            print(f"ERROR creando consulta preparada: {consulta_id}")

        if (
            not getattr(session, 'pago_pending_abogado_uid', None)
            and not getattr(session, 'current_consulta_id', None)
        ):
            self._reconstruir_pago_consulta_desde_session()

        # Primero: si hay datos pending de consulta_tipo, crear la consulta nueva.
        abogado_uid   = getattr(session, 'pago_pending_abogado_uid', None)
        abogado_email = getattr(session, 'pago_pending_abogado_email', None)
        cliente_uid   = getattr(session, 'pago_pending_cliente_uid', None)
        cliente_email = getattr(session, 'pago_pending_cliente_email', None)
        tipo          = getattr(session, 'tipo_servicio', 'chat') or 'chat'
        precio        = getattr(session, 'pago_pending_precio', 0) or 0

        if abogado_uid and cliente_uid:
            data = {
                "abogado_uid":   abogado_uid,
                "abogado_email": abogado_email or "",
                "cliente_uid":   cliente_uid,
                "cliente_email": cliente_email or "",
                "tipo_servicio": tipo,
                "estado":        "pendiente",
                "monto":         precio,
                "area":          getattr(session, 'area_legal', '') or '',
                "external_reference": (
                    getattr(session, "pago_external_reference", None)
                    or f"consulta|{cliente_uid}|{abogado_uid}|{tipo}|{int(time.time())}"
                ),
            }
            ok, consulta_id = fb.crear_consulta(data)
            if ok and consulta_id:
                session.current_consulta_id = consulta_id
                # Limpiar pending para no crear duplicados si vuelve atras
                session.pago_pending_abogado_uid   = None
                session.pago_pending_abogado_email = None
                session.pago_pending_cliente_uid   = None
                session.pago_pending_cliente_email = None
                session.pago_pending_precio        = None
                session.guardar()

                consulta = fb.obtener_consulta(consulta_id)
                if consulta:
                    return consulta

                # Si no la encuentra aun, armar con los datos locales
                data["id"] = consulta_id
                return data
            else:
                print(f"ERROR creando consulta: {consulta_id}")
                return None

        # Segundo: si ya hay consulta activa en session, usarla.
        if session.current_consulta_id:
            consulta = fb.obtener_consulta(session.current_consulta_id)
            if consulta:
                if cliente_uid and abogado_uid and tipo:
                    if (
                        consulta.get("cliente_uid") != cliente_uid
                        or consulta.get("abogado_uid") != abogado_uid
                        or (consulta.get("tipo_servicio", "chat") or "chat") != tipo
                    ):
                        consulta = None
                if consulta and str(consulta.get("estado") or "").lower() == "finalizado":
                    consulta = None
            if consulta:
                return consulta

        # Tercero: buscar consulta pendiente existente del usuario.
        # Si ya sabemos abogado/tipo, reutilizar solo esa combinacion.
        user = session.current_user
        if not user:
            return None

        uid = user.get("uid")
        consultas = fb.obtener_consultas_usuario(uid, "cliente")
        for cid, cdata in consultas:
            if str(cdata.get("estado") or "").lower() != "pendiente":
                continue

            if cliente_uid and abogado_uid and tipo:
                if cdata.get("abogado_uid") != abogado_uid:
                    continue
                if (cdata.get("tipo_servicio", "chat") or "chat") != tipo:
                    continue

            if not abogado_uid and not tipo:
                cdata["id"] = cid
                return cdata

            cdata["id"] = cid
            return cdata

        return None

    def _generar_preferencia(
        self,
        tipo,
        abogado,
        user_email
    ):
        import threading as _t

        def _fetch():
            monto_override = None
            if self._consulta_data:
                monto_override = self._consulta_data.get("monto")
            init_point, pref_id = _crear_preferencia(
                tipo,
                abogado,
                user_email,
                self._consulta_id,
                external_reference=self._external_reference_seed,
                monto_override=monto_override
            )
            Clock.schedule_once(
                lambda dt: self._on_preferencia_lista(
                    init_point, pref_id, user_email, abogado, tipo
                ), 0
            )

        _t.Thread(target=_fetch, daemon=True).start()

    def _on_preferencia_lista(self, init_point, pref_id, user_email, abogado, tipo):
        """Callback en hilo principal cuando la preferencia MP esta lista o fallo."""
        if init_point:
            self._init_point = init_point
            self._preference_id = pref_id
            if tipo == "especialidad_extra":
                seleccionadas = _especialidades_extra_seleccionadas()
                especialidad = "__".join(seleccionadas) if seleccionadas else "especialidad"
                monto = getattr(session, "pago_monto", 10000) or 10000
                self._external_reference = f"especialidad_extra|{user_email}|{especialidad}|{monto}"
            else:
                self._external_reference = self._external_reference_seed or f"consulta|{self._consulta_id}|{user_email}|{abogado}|{tipo}"
            self._tipo_servicio = tipo
            self._abogado_email = abogado

            if tipo != "especialidad_extra":
                session.pago_external_reference = self._external_reference
                session.pago_preference_id = self._preference_id
                session.pago_init_point = self._init_point
                session.guardar()

            self.ids.lbl_estado_mp.text = "Link de pago listo"
            self.ids.lbl_estado_mp.color = (0.18, 0.80, 0.44, 1)
            self.ids.btn_ir_mp.disabled = False
            self.ids.btn_verificar.disabled = True
            self.ids.btn_confirmar.disabled = False

            # Ocultar boton reintentar si estaba visible
            if hasattr(self, '_btn_reintentar') and self._btn_reintentar:
                try:
                    self._btn_reintentar.parent.remove_widget(self._btn_reintentar)
                except Exception:
                    pass
                self._btn_reintentar = None

        else:
            self.ids.lbl_estado_mp.text = "Error conectando MercadoPago"
            self.ids.lbl_estado_mp.color = (0.90, 0.25, 0.25, 1)
            self._mostrar_btn_reintentar(user_email, abogado, tipo)

    def _mostrar_btn_reintentar(self, user_email, abogado, tipo):
        """Agrega boton Reintentar debajo del estado cuando MP falla."""
        from kivy.uix.button import Button as _Btn

        # Evitar duplicados
        if hasattr(self, '_btn_reintentar') and self._btn_reintentar:
            return

        btn = _Btn(
            text="Reintentar conexion con MercadoPago",
            size_hint_y=None,
            height=46,
            bold=True,
            font_size="13sp",
            background_normal="",
            background_color=(0.90, 0.55, 0.05, 1),
            color=(1, 1, 1, 1),
        )

        def _reintentar(instance):
            btn.disabled = True
            self.ids.lbl_estado_mp.text = "Reintentando..."
            self.ids.lbl_estado_mp.color = (0.55, 0.50, 0.65, 1)
            Clock.schedule_once(
                lambda dt: self._generar_preferencia(tipo, abogado, user_email),
                0.2
            )

        btn.bind(on_release=_reintentar)

        # Insertar despues de lbl_estado_mp en su contenedor
        try:
            parent = self.ids.lbl_estado_mp.parent
            idx = parent.children.index(self.ids.lbl_estado_mp)
            parent.add_widget(btn, index=idx)
            self._btn_reintentar = btn
        except Exception as e:
            print(f"ERROR btn reintentar: {e}")

    def ir_a_pagar(self):
        if self._init_point:
            self.ids.lbl_estado_mp.text = "Cuando termines el pago, volve y toca Continuar"
            self.ids.lbl_estado_mp.color = (0.55, 0.50, 0.65, 1)
            _abrir_url(self._init_point)

    def _cliente_email_pago(self):
        if self._consulta_data:
            return self._consulta_data.get("cliente_email", "")
        return getattr(session, "pago_pending_cliente_email", "") or (session.current_user or {}).get("email", "")

    def _monto_pago(self):
        if self._consulta_data:
            return self._consulta_data.get("monto", 0)
        return getattr(session, "pago_pending_precio", 0) or obtener_precios().get(self._tipo_servicio or "chat", 1000)

    def _pago_procesado_en_supabase(self):
        cliente_uid = self._cliente_uid or getattr(session, "pago_pending_cliente_uid", None)
        abogado_uid = self._abogado_uid or getattr(session, "pago_pending_abogado_uid", None)
        tipo = self._tipo_servicio or getattr(session, "tipo_servicio", None)

        resultado = fb.buscar_pago_procesado_disponible(
            external_reference=self._external_reference,
            cliente_uid=cliente_uid,
            abogado_uid=abogado_uid,
            tipo_servicio=tipo,
        )

        if not resultado:
            return False

        pago = resultado.get("pago") or {}
        consulta = resultado.get("consulta")
        external_reference = resultado.get("external_reference") or self._external_reference

        if external_reference:
            self._external_reference = external_reference
            self._external_reference_seed = external_reference
            session.pago_external_reference = external_reference

        self._payment_id = pago.get("payment_id")

        if consulta:
            self._consulta_id = consulta.get("id")
            self._consulta_estado_previo = consulta.get("estado")
            self._consulta_data = dict(consulta)
            self._tipo_servicio = consulta.get("tipo_servicio", self._tipo_servicio)
            self._abogado_uid = consulta.get("abogado_uid", self._abogado_uid)
            self._abogado_email = consulta.get("abogado_email", self._abogado_email)
            self._cliente_uid = consulta.get("cliente_uid", self._cliente_uid)

            session.current_consulta_id = self._consulta_id
            session.tipo_servicio = self._tipo_servicio
            session.abogado_seleccionado = self._abogado_email

        session.guardar()
        return True

    def verificar_pago(self):
        if not self._external_reference:
            return

        # FIX: este chequeo llama a la API de Mercado Pago (red) -- si
        # corria en el hilo principal, volver del navegador de MP sin pagar
        # (o con la red lenta reconectando) podia colgar la UI el tiempo
        # suficiente como para que Android la matara (ANR) -- se ve como un
        # crash aunque el error real sea "app no responde". Se saca el
        # llamado de red a un hilo aparte, igual que el resto de los
        # llamados a Supabase/MP en la app.
        self.ids.btn_verificar.disabled = True
        self.ids.lbl_estado_mp.text = (
            "Verificando pago..."
        )

        def _worker():
            try:
                pagado = _verificar_pago_mp(
                    self._external_reference,
                    self._preference_id,
                    payer_email=self._cliente_email_pago(),
                    monto=self._monto_pago(),
                ) or self._pago_procesado_en_supabase()
            except Exception as e:
                print("ERROR verificar_pago (background):", e)
                pagado = False
            Clock.schedule_once(lambda dt, p=pagado: self._aplicar_resultado_verificar_pago(p), 0)

        threading.Thread(target=_worker, daemon=True).start()

    def _aplicar_resultado_verificar_pago(self, pagado):
        self.ids.btn_verificar.disabled = False

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

    def confirmar_pago(self):
        self.ids.btn_confirmar.disabled = True

        if not self._pago_verificado:
            if not self._external_reference:
                self.ids.lbl_estado_mp.text = "Pago no preparado"
                self.ids.lbl_estado_mp.color = (0.90, 0.25, 0.25, 1)
                self.ids.btn_confirmar.disabled = False
                return

            self.ids.lbl_estado_mp.text = "Verificando pago..."
            self.ids.lbl_estado_mp.color = (0.55, 0.50, 0.65, 1)

            # FIX: mismo problema que verificar_pago() -- este chequeo llama
            # a la API de Mercado Pago (red) y corria en el hilo principal.
            # Es exactamente el camino que se dispara al volver del
            # navegador de MP SIN pagar y tocar "Confirmar": la app se
            # quedaba colgada esperando la respuesta de red justo despues
            # de volver de background (momento en que el celular suele
            # tardar mas en reconectar), lo suficiente como para que
            # Android la matara (se veia como un crash). Se saca el
            # llamado de red a un hilo aparte; el resto de la logica
            # (crear consulta, etc.) sigue igual, corriendo recien cuando
            # se confirma que el pago existe.
            def _worker():
                try:
                    verificado = _verificar_pago_mp(
                        self._external_reference,
                        self._preference_id,
                        payer_email=self._cliente_email_pago(),
                        monto=self._monto_pago(),
                    ) or self._pago_procesado_en_supabase()
                except Exception as e:
                    print("ERROR confirmar_pago verificacion (background):", e)
                    verificado = False
                Clock.schedule_once(lambda dt, v=verificado: self._confirmar_pago_background(v), 0)

            threading.Thread(target=_worker, daemon=True).start()
            return

        self._confirmar_pago_logica()

    def _confirmar_pago_background(self, verificado):
        if verificado:
            self._pago_verificado = True
            self._confirmar_pago_logica()
        else:
            self.ids.lbl_estado_mp.text = "Pago no encontrado. Espera unos segundos y toca Continuar."
            self.ids.lbl_estado_mp.color = (0.90, 0.25, 0.25, 1)
            self.ids.btn_confirmar.disabled = False

    def _confirmar_pago_logica(self):
        # FIX: Si es pago de especialidad extra, actualizar abogado
        if (
            getattr(session, 'pago_tipo', None) == 'especialidad_extra'
            or self._tipo_servicio == "especialidad_extra"
        ):
            self._confirmar_especialidad_extra()
            return

        consulta_creada_ahora = False

        if self._external_reference:
            consulta_ref = fb.obtener_consulta_por_external_reference(
                self._external_reference
            )

            if consulta_ref and consulta_ref.get("_schema_error"):
                self.ids.lbl_estado_mp.text = "Falta configurar la referencia de pago en Supabase"
                self.ids.lbl_estado_mp.color = (0.90, 0.25, 0.25, 1)
                self.ids.btn_confirmar.disabled = False
                return

            if consulta_ref:
                estado_ref = str(consulta_ref.get("estado") or "").lower()
                if estado_ref == "finalizado":
                    self.ids.lbl_estado_mp.text = "Este pago ya fue usado en una consulta finalizada"
                    self.ids.lbl_estado_mp.color = (0.90, 0.25, 0.25, 1)
                    self.ids.btn_confirmar.disabled = False
                    return

                self._consulta_id = consulta_ref.get("id")
                self._consulta_estado_previo = consulta_ref.get("estado")
                self._consulta_data = dict(consulta_ref)
                self._tipo_servicio = consulta_ref.get("tipo_servicio", self._tipo_servicio)
                self._abogado_uid = consulta_ref.get("abogado_uid", self._abogado_uid)
                self._abogado_email = consulta_ref.get("abogado_email", self._abogado_email)
                self._cliente_uid = consulta_ref.get("cliente_uid", self._cliente_uid)

                session.current_consulta_id = self._consulta_id
                session.tipo_servicio = self._tipo_servicio
                session.abogado_seleccionado = self._abogado_email
                session.guardar()

        if not self._consulta_id:
            if not self._consulta_data:
                self._consulta_data = self._armar_consulta_data_desde_session()

            if self._consulta_data:
                data = dict(self._consulta_data)
                data.pop("id", None)
                data.pop("created_at", None)
                data["estado"] = "pagado"
                if self._external_reference:
                    data["external_reference"] = self._external_reference

                ok, consulta_id = fb.crear_consulta(data)
                if ok and consulta_id:
                    consulta_creada_ahora = True
                    self._consulta_id = consulta_id
                    self._consulta_estado_previo = None
                    self._abogado_uid = self._abogado_uid or data.get("abogado_uid")
                    self._abogado_email = self._abogado_email or data.get("abogado_email", "")
                    self._cliente_uid = self._cliente_uid or data.get("cliente_uid")
                    session.current_consulta_id = consulta_id
                    session.guardar()
                else:
                    detalle = str(consulta_id or "")
                    if len(detalle) > 80:
                        detalle = detalle[:80] + "..."
                    self.ids.lbl_estado_mp.text = f"Error creando consulta\n{detalle}"
                    self.ids.lbl_estado_mp.color = (0.90, 0.25, 0.25, 1)
                    self.ids.btn_confirmar.disabled = False
                    return
            else:
                self.ids.btn_confirmar.disabled = False
                return

        PRECIOS_NUM = obtener_precios()

        if consulta_creada_ahora:
            estado_previo = ""
        else:
            estado_previo = str(self._consulta_estado_previo or "").lower()
            if not estado_previo and self._consulta_id:
                consulta_actual = fb.obtener_consulta(self._consulta_id)
                if consulta_actual:
                    estado_previo = str(consulta_actual.get("estado") or "").lower()
                    self._consulta_estado_previo = consulta_actual.get("estado")

        if estado_previo == "finalizado":
            self.ids.lbl_estado_mp.text = "Esta consulta ya fue finalizada"
            self.ids.lbl_estado_mp.color = (0.90, 0.25, 0.25, 1)
            self.ids.btn_confirmar.disabled = False
            return

        debe_acreditar = estado_previo not in ["pagado", "en_curso", "videollamada"]

        if estado_previo not in ["pagado", "en_curso", "videollamada"]:
            fb.actualizar_estado_consulta(self._consulta_id, "pagado")

        if self._abogado_uid and debe_acreditar:
            fb.notificar_consulta_pagada(
                self._abogado_uid,
                self._tipo_servicio,
                PRECIOS_NUM.get(
                    self._tipo_servicio,
                    1000
                ),
                consulta_id=self._consulta_id,
                cliente_email=(session.current_user or {}).get("email", "")
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

        self.ids.btn_ir_mp.disabled = True
        self.ids.btn_verificar.disabled = True

        session.pago_tipo = None
        session.pago_pending_abogado_uid = None
        session.pago_pending_abogado_email = None
        session.pago_pending_cliente_uid = None
        session.pago_pending_cliente_email = None
        session.pago_pending_precio = None
        session.pago_external_reference = None
        session.pago_preference_id = None
        session.pago_init_point = None
        session.guardar()

        self._consulta_data = None

        Clock.schedule_once(
            lambda dt: setattr(self.manager, "current", "chat"),
            1.0
        )

    def _confirmar_especialidad_extra(self):
        """Confirma pago de especialidad extra y actualiza abogado"""
        import json

        uid = session.get_uid()
        if not uid:
            self.ids.lbl_estado_mp.text = "Error: no hay usuario"
            return

        user_data = fb.obtener_usuario(uid)
        if not user_data:
            self.ids.lbl_estado_mp.text = "Error cargando perfil"
            return

        especialidades_raw = user_data.get('especialidades', '[]') or '[]'
        try:
            actuales = json.loads(especialidades_raw) if isinstance(especialidades_raw, str) else especialidades_raw
        except:
            actuales = []

        nuevas = _especialidades_extra_seleccionadas()
        for nueva in nuevas:
            if nueva and nueva not in actuales:
                actuales.append(nueva)

        datos = {
            'especialidades': json.dumps(actuales),
            'especialidad': actuales[0] if actuales else ''
        }

        fb.actualizar_usuario(uid, datos)
        user_data.update(datos)

        session.current_user = user_data

        session.pago_tipo = None
        session.pago_monto = None
        session.especialidad_a_agregar = None
        session.especialidades_actuales = None
        session.current_consulta_id = None
        session.guardar()

        try:
            if self.manager.has_screen("abogados"):
                self.manager.get_screen("abogados")._todos = []
        except Exception:
            pass

        self.ids.lbl_estado_mp.text = "¡Especialidad agregada!"
        self.ids.lbl_estado_mp.color = (0.18, 0.80, 0.44, 1)

        Clock.schedule_once(
            lambda dt: setattr(self.manager, 'current', 'perfil_abogado'),
            1.5
        )

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

    def volver(self):
        if getattr(session, 'pago_tipo', None) == 'especialidad_extra':
            self.manager.current = "perfil_abogado"
        else:
            self.manager.current = "pago"
