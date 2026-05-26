# supabase_config.py

import os
import uuid
import json
import logging
from datetime import datetime, timezone

import requests as http_requests
from dotenv import load_dotenv
from supabase import create_client

# =========================================================
# LOAD ENV
# =========================================================

load_dotenv()

# =========================================================
# LOGS
# =========================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================================
# CONFIG SUPABASE
# =========================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")

# IMPORTANTE:
# EN APK / ANDROID USAR SOLO ANON KEY
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception(
        "Faltan variables SUPABASE_URL o SUPABASE_ANON_KEY"
    )

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

NOTIFICACIONES_URL = (
    f"{SUPABASE_URL}/functions/v1/notificaciones-push"
)

# =========================================================
# HELPERS
# =========================================================

def now_iso():
    return datetime.now(
        timezone.utc
    ).isoformat()

# =========================================================
# PUSH NOTIFICATIONS
# =========================================================

def _enviar_notificacion_push(tipo, data):

    try:

        res = http_requests.post(
            NOTIFICACIONES_URL,
            json={
                "tipo": tipo,
                "data": data
            },
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SUPABASE_KEY}"
            },
            timeout=20
        )

        logger.info(
            f"Push {tipo}: {res.status_code}"
        )

        return res.status_code in [200, 201]

    except Exception as e:

        logger.error(
            f"Error push {tipo}: {e}"
        )

        return False


def notificar_consulta_pagada(
        abogado_uid,
        tipo_servicio,
        monto,
        consulta_id=None,
        cliente_email=""
):

    _enviar_notificacion_push(
        "consulta_pagada",
        {
            "abogado_uid": abogado_uid,
            "tipo_servicio": tipo_servicio,
            "monto": monto,
            "consulta_id": str(consulta_id or ""),
            "cliente_email": cliente_email,
        }
    )


def notificar_consulta_aceptada(
        cliente_uid,
        tipo_servicio,
        consulta_id=None
):

    _enviar_notificacion_push(
        "consulta_aceptada",
        {
            "cliente_uid": cliente_uid,
            "tipo_servicio": tipo_servicio,
            "consulta_id": str(consulta_id or ""),
        }
    )


def notificar_nuevo_mensaje(
        consulta_id,
        emisor_uid,
        receptor_uid,
        texto
):

    preview = (
        texto[:50] + "..."
        if len(texto) > 50
        else texto
    )

    _enviar_notificacion_push(
        "nuevo_mensaje",
        {
            "consulta_id": str(consulta_id),
            "emisor_uid": emisor_uid,
            "receptor_uid": receptor_uid,
            "preview": preview,
        }
    )


def notificar_videollamada(
        cliente_uid,
        consulta_id
):

    _enviar_notificacion_push(
        "videollamada",
        {
            "cliente_uid": cliente_uid,
            "consulta_id": str(consulta_id),
        }
    )


def notificar_consulta_finalizada(
        cliente_uid,
        consulta_id=None
):

    _enviar_notificacion_push(
        "consulta_finalizada",
        {
            "cliente_uid": cliente_uid,
            "consulta_id": str(consulta_id or ""),
        }
    )

# =========================================================
# HONORARIOS
# =========================================================

def acreditar_honorario(
        abogado_uid,
        tipo_servicio
):

    precios = {
        "chat": 1000,
        "video": 3000,
        "urgente": 5000
    }

    monto = precios.get(
        tipo_servicio,
        1000
    )

    # COMISION SOLO UNA VEZ
    comision = round(monto * 0.20)

    neto = monto - comision

    try:

        user = obtener_usuario(abogado_uid)

        if user:

            saldo_actual = (
                user.get("saldo", 0) or 0
            )

            actualizar_usuario(
                abogado_uid,
                {
                    "saldo": saldo_actual + neto
                }
            )

        logger.info(
            f"Honorario acreditado "
            f"neto={neto} "
            f"comision={comision}"
        )

        return neto, comision

    except Exception as e:

        logger.error(
            f"ERROR acreditar_honorario: {e}"
        )

        return 0, 0

# =========================================================
# USUARIOS
# =========================================================

def crear_usuario_db(
        uid,
        email,
        nombre,
        rol="cliente",
        telefono="",
        datos_extra=None
):

    try:

        existente = obtener_usuario_por_email(
            email
        )

        if existente:
            return False, "Email ya registrado"

        data = {
            "uid": uid,
            "nombre": nombre,
            "email": email,
            "telefono": telefono,
            "rol": rol,
            "email_verified": False,
            "aprobado": False,
            "created_at": now_iso()
        }

        if datos_extra:
            data.update(datos_extra)

        supabase.table(
            "usuarios"
        ).insert(data).execute()

        return True, None

    except Exception as e:

        logger.error(e)

        return False, str(e)


def obtener_usuario(uid):

    try:

        res = supabase.table(
            "usuarios"
        ).select("*") \
            .eq("uid", uid) \
            .limit(1) \
            .execute()

        if res.data:
            return res.data[0]

        return None

    except Exception as e:

        logger.error(e)

        return None


def obtener_usuario_por_email(email):

    try:

        res = supabase.table(
            "usuarios"
        ).select("*") \
            .eq("email", email) \
            .limit(1) \
            .execute()

        if res.data:
            return res.data[0]

        return None

    except Exception as e:

        logger.error(e)

        return None


def actualizar_usuario(uid, datos):

    try:

        supabase.table("usuarios") \
            .update(datos) \
            .eq("uid", uid) \
            .execute()

        return True

    except Exception as e:

        logger.error(e)

        return False


def listar_abogados(
        disponibles=True,
        provincia=None,
        ciudad=None
):

    try:

        query = supabase.table("usuarios") \
            .select("*") \
            .eq("rol", "abogado") \
            .eq("suscripcion_activa", True) \
            .eq("aprobado", True)

        if disponibles:
            query = query.neq(
                "estado_abogado",
                "ocupado"
            )

        if provincia:
            query = query.eq(
                "provincia",
                provincia
            )

        if ciudad and ciudad != "Otras":
            query = query.eq(
                "ciudad",
                ciudad
            )

        res = query.execute()

        return res.data

    except Exception as e:

        logger.error(
            f"ERROR listar_abogados: {e}"
        )

        return []


def obtener_resenas_abogado(email):

    try:

        res = supabase.table(
            "resenas"
        ).select("*") \
            .eq("abogado_email", email) \
            .execute()

        return res.data

    except Exception as e:

        logger.error(
            f"ERROR obtener_resenas_abogado: {e}"
        )

        return []


def activar_suscripcion_abogado(
        uid,
        monto,
        especialidades
):

    try:

        datos = {
            "suscripcion_activa": True,
            "suscripcion_fecha": now_iso(),
            "suscripcion_monto": monto,
            "estado_abogado": "disponible",
            "especialidades": especialidades,
            "aprobado": True,
        }

        if especialidades:
            datos["especialidad"] = (
                especialidades[0]
            )

        supabase.table("usuarios") \
            .update(datos) \
            .eq("uid", uid) \
            .execute()

        return True

    except Exception as e:

        logger.error(
            f"ERROR activar_suscripcion: {e}"
        )

        return False


def desactivar_suscripcion_abogado(uid):

    try:

        supabase.table("usuarios") \
            .update({
                "suscripcion_activa": False,
                "estado_abogado": "ocupado"
            }) \
            .eq("uid", uid) \
            .execute()

        return True

    except Exception as e:

        logger.error(
            f"ERROR desactivar_suscripcion: {e}"
        )

        return False


def aprobar_abogado(uid):

    try:

        supabase.table("usuarios") \
            .update({
                "aprobado": True
            }) \
            .eq("uid", uid) \
            .execute()

        return True, "Abogado aprobado"

    except Exception as e:

        logger.error(
            f"ERROR aprobar_abogado: {e}"
        )

        return False, str(e)

# =========================================================
# RETIROS
# =========================================================

def solicitar_retiro(
        uid,
        monto,
        cuenta_destino
):

    try:

        user = obtener_usuario(uid)

        if not user:
            return False, "Usuario no encontrado", 0

        saldo = user.get("saldo", 0) or 0

        if monto <= 0:
            return False, "Monto invalido", 0

        if monto > saldo:
            return (
                False,
                f"Saldo insuficiente: ${saldo}",
                0
            )

        # NO SE COBRA DOBLE COMISION
        neto = monto

        supabase.table("retiros").insert({
            "abogado_uid": uid,
            "abogado_email": user.get(
                "email",
                ""
            ),
            "monto_bruto": monto,
            "comision_plataforma": 0,
            "monto_neto": neto,
            "cuenta_destino": cuenta_destino,
            "estado": "pendiente",
            "fecha": now_iso(),
        }).execute()

        actualizar_usuario(
            uid,
            {
                "saldo": saldo - monto
            }
        )

        return (
            True,
            "Retiro solicitado correctamente",
            neto
        )

    except Exception as e:

        logger.error(
            f"ERROR solicitar_retiro: {e}"
        )

        return False, str(e), 0


def listar_retiros_pendientes():

    try:

        res = supabase.table("retiros") \
            .select("*") \
            .eq("estado", "pendiente") \
            .order("fecha", desc=False) \
            .execute()

        return res.data

    except Exception as e:

        logger.error(
            f"ERROR listar_retiros_pendientes: {e}"
        )

        return []


def procesar_retiro(
        retiro_id,
        admin_uid
):

    try:

        res = supabase.table("retiros") \
            .select("*") \
            .eq("id", retiro_id) \
            .limit(1) \
            .execute()

        if not res.data:
            return False, "Retiro no encontrado"

        retiro = res.data[0]

        if retiro.get("estado") != "pendiente":
            return False, "Ya procesado"

        supabase.table("retiros") \
            .update({
                "estado": "pagado",
                "pagado_at": now_iso(),
                "admin_uid": admin_uid,
            }) \
            .eq("id", retiro_id) \
            .execute()

        return (
            True,
            f"Retiro ${retiro.get('monto_neto', 0)} pagado"
        )

    except Exception as e:

        logger.error(
            f"ERROR procesar_retiro: {e}"
        )

        return False, str(e)


def crear_retiro(
        abogado_uid,
        abogado_email,
        monto_bruto,
        cuenta_destino
):

    try:

        supabase.table("retiros").insert({
            "abogado_uid": abogado_uid,
            "abogado_email": abogado_email,
            "monto_bruto": monto_bruto,
            "comision_plataforma": 0,
            "monto_neto": monto_bruto,
            "cuenta_destino": cuenta_destino,
            "estado": "pendiente",
            "fecha": now_iso(),
        }).execute()

        return True, monto_bruto

    except Exception as e:

        logger.error(
            f"ERROR crear_retiro: {e}"
        )

        return False, str(e)

# =========================================================
# VERIFICACION EMAIL
# =========================================================

def enviar_codigo_verificacion_resend(
        email,
        codigo
):

    try:

        import resend

        resend.api_key = os.getenv(
            "RESEND_API_KEY"
        )

        resend.Emails.send({
            "from": "LegalApp <onboarding@resend.dev>",
            "to": email,
            "subject": "Codigo de verificacion",
            "html": f"""
            <div style="font-family:Arial;padding:20px;">
                <h2>Legal App</h2>
                <p>Tu codigo es:</p>
                <h1>{codigo}</h1>
            </div>
            """
        })

        logger.info(
            f"Email enviado a {email}"
        )

        return True

    except Exception as e:

        logger.error(
            f"Resend error: {e}"
        )

        return False


def enviar_codigo_verificacion(
        email,
        uid
):

    try:

        codigo = str(
            uuid.uuid4().int
        )[:6]

        supabase.table(
            "codigos_verificacion"
        ).delete() \
            .eq("uid", uid) \
            .execute()

        supabase.table(
            "codigos_verificacion"
        ).insert({
            "uid": uid,
            "email": email,
            "codigo": codigo
        }).execute()

        enviar_codigo_verificacion_resend(
            email,
            codigo
        )

        return True, codigo

    except Exception as e:

        logger.error(
            f"ERROR enviar_codigo_verificacion: {e}"
        )

        return False, None


def reenviar_codigo_verificacion(
        email,
        uid
):

    return enviar_codigo_verificacion(
        email,
        uid
    )


def verificar_email_con_codigo(
        uid,
        codigo
):

    try:

        res = supabase.table(
            "codigos_verificacion"
        ).select("*") \
            .eq("uid", uid) \
            .eq("codigo", codigo) \
            .execute()

        if not res.data:
            return False, "Codigo incorrecto"

        supabase.table("usuarios") \
            .update({
                "email_verified": True
            }) \
            .eq("uid", uid) \
            .execute()

        return True, "Cuenta verificada"

    except Exception as e:

        logger.error(
            f"ERROR verificar_email_con_codigo: {e}"
        )

        return False, str(e)

# =========================================================
# CONSULTAS
# =========================================================

def crear_consulta(data):

    try:

        data["created_at"] = now_iso()

        res = supabase.table("consultas") \
            .insert(data) \
            .execute()

        return True, res.data[0]["id"]

    except Exception as e:

        logger.error(e)

        return False, str(e)


def obtener_consulta(consulta_id):

    try:

        res = supabase.table("consultas") \
            .select("*") \
            .eq("id", consulta_id) \
            .limit(1) \
            .execute()

        if res.data:
            return res.data[0]

        return None

    except Exception as e:

        logger.error(e)

        return None


def obtener_consultas_usuario(
        uid,
        rol="cliente"
):

    try:

        if rol == "cliente":

            res = supabase.table(
                "consultas"
            ).select("*") \
                .eq("cliente_uid", uid) \
                .execute()

        else:

            res = supabase.table(
                "consultas"
            ).select("*") \
                .eq("abogado_uid", uid) \
                .execute()

        return [
            (c["id"], c)
            for c in res.data
        ]

    except Exception as e:

        logger.error(
            f"ERROR obtener_consultas_usuario: {e}"
        )

        return []


def actualizar_estado_consulta(
        consulta_id,
        estado
):

    try:

        supabase.table("consultas") \
            .update({
                "estado": estado
            }) \
            .eq("id", consulta_id) \
            .execute()

        return True

    except Exception as e:

        logger.error(e)

        return False

# =========================================================
# MENSAJES
# =========================================================

def enviar_mensaje(
        consulta_id,
        emisor_uid,
        texto
):

    try:

        usuario = obtener_usuario(
            emisor_uid
        )

        email = ""

        if usuario:
            email = usuario.get(
                "email",
                ""
            )

        supabase.table("mensajes").insert({
            "consulta_id": consulta_id,
            "emisor_uid": emisor_uid,
            "emisor_email": email,
            "texto": texto,
            "created_at": now_iso()
        }).execute()

        consulta = obtener_consulta(
            consulta_id
        )

        if consulta:

            if emisor_uid == consulta.get(
                "cliente_uid"
            ):
                receptor_uid = consulta.get(
                    "abogado_uid"
                )
            else:
                receptor_uid = consulta.get(
                    "cliente_uid"
                )

            if receptor_uid:

                notificar_nuevo_mensaje(
                    consulta_id,
                    emisor_uid,
                    receptor_uid,
                    texto
                )

        return True

    except Exception as e:

        logger.error(e)

        return False


def obtener_mensajes(consulta_id):

    try:

        res = supabase.table("mensajes") \
            .select("*") \
            .eq("consulta_id", consulta_id) \
            .order("created_at") \
            .execute()

        return res.data

    except Exception as e:

        logger.error(e)

        return []

# =========================================================
# STORAGE
# =========================================================

def subir_archivo_chat(
        consulta_id,
        path_local,
        nombre
):

    try:

        bucket = "chat-files"

        path_storage = (
            f"{consulta_id}/{nombre}"
        )

        with open(path_local, "rb") as f:

            supabase.storage \
                .from_(bucket) \
                .upload(
                    path_storage,
                    f.read()
                )

        url = supabase.storage \
            .from_(bucket) \
            .get_public_url(path_storage)

        return True, url

    except Exception as e:

        logger.error(e)

        return False, None

# =========================================================
# RESEÑAS
# =========================================================

def tiene_resena(consulta_id):

    try:

        res = supabase.table("resenas") \
            .select("*") \
            .eq("consulta_id", consulta_id) \
            .execute()

        return len(res.data) > 0

    except Exception as e:

        logger.error(e)

        return False

# =========================================================
# FIREBASE AUTH
# =========================================================

from firebase_auth import (
    crear_usuario_auth,
    login_usuario_auth,
    enviar_reset_password,
    enviar_verificacion_email
)

# =========================================================
# COMPATIBILIDAD APP VIEJA
# =========================================================

def crear_usuario(
        email,
        password,
        nombre,
        rol="cliente",
        telefono="",
        datos_extra=None
):

    try:

        ok, uid, error = crear_usuario_auth(
            email,
            password,
            nombre
        )

        if not ok:
            return False, None, error

        data = {
            "uid": uid,
            "nombre": nombre,
            "username": nombre,
            "email": email,
            "telefono": telefono,
            "rol": rol,
            "email_verified": False,
            "aprobado": False
        }

        if datos_extra:
            data.update(datos_extra)

        res = supabase.table(
            "usuarios"
        ).insert(data).execute()

        if not res.data:
            return (
                False,
                None,
                "Error al guardar usuario"
            )

        return True, uid, None

    except Exception as e:

        logger.error(e)

        return False, None, str(e)


def login_usuario(email, password):

    try:

        ok, auth_data, error = login_usuario_auth(
            email,
            password
        )

        if not ok:
            return False, None, error

        uid = auth_data["uid"]

        res = supabase.table(
            "usuarios"
        ).select("*") \
            .eq("uid", uid) \
            .limit(1) \
            .execute()

        if not res.data:
            return (
                False,
                None,
                "Usuario no encontrado"
            )

        user = res.data[0]

        if (
            user.get("rol") == "abogado"
            and not user.get(
                "suscripcion_activa",
                False
            )
        ):
            return (
                False,
                None,
                "Suscripcion inactiva"
            )

        user["idToken"] = auth_data["idToken"]

        return True, user, None

    except Exception as e:

        logger.error(e)

        return False, None, str(e)

# =========================================================
# CONFIGURACION
# =========================================================

def obtener_configuracion():

    try:

        res = supabase.table(
            "configuracion"
        ).select("*").execute()

        return {
            item["clave"]: item["valor"]
            for item in res.data
        }

    except Exception as e:

        logger.error(
            f"ERROR obtener_configuracion: {e}"
        )

        return {}


def actualizar_configuracion(
        clave,
        valor
):

    try:

        supabase.table("configuracion") \
            .update({
                "valor": str(valor)
            }) \
            .eq("clave", clave) \
            .execute()

        return True

    except Exception as e:

        logger.error(
            f"ERROR actualizar_configuracion: {e}"
        )

        return False