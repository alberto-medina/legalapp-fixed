# supabase_config.py — VERSIÓN ANDROID COMPATIBLE (sin paquete supabase)
import os
import uuid
import json
import logging
import mimetypes
from datetime import datetime, timezone

import requests as http_requests
from kivy.utils import platform

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
LAST_ERROR = ""
MENSAJE_ELIMINADO_TEXTO = "__LEGALAPP_MSG_ELIMINADO__"

EXTENSIONES_CHAT = {
    '.pdf',
    '.png', '.jpg', '.jpeg', '.webp', '.heic', '.heif',
    '.doc', '.docx',
    '.mp4', '.mov', '.m4v', '.3gp', '.webm',
    '.mp3', '.m4a', '.aac', '.wav', '.ogg', '.opus',
}

# =========================================================
# CONFIG SUPABASE (Android compatible)
# =========================================================

import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import SUPABASE_URL, SUPABASE_KEY
import firebase_auth as firebase_auth_api

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Faltan variables SUPABASE_URL o SUPABASE_KEY")

# Headers para todas las llamadas REST a Supabase
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

REST_URL = f"{SUPABASE_URL}/rest/v1"

NOTIFICACIONES_URL = f"{SUPABASE_URL}/functions/v1/notificaciones-push"
MERCADOPAGO_PROXY_URL = f"{SUPABASE_URL}/functions/v1/mercadopago-proxy"


def _invocar_edge_function(url, payload):
    global LAST_ERROR
    LAST_ERROR = ""
    try:
        r = http_requests.post(
            url,
            json=payload,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            },
            timeout=25,
        )
        if r.status_code >= 400:
            LAST_ERROR = r.text
            logger.error(f"EDGE error {r.status_code}: {r.text}")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        if not LAST_ERROR:
            LAST_ERROR = str(e)
        logger.error(f"EDGE call error: {e}")
        return None


def mp_crear_preferencia(titulo, monto, payer_email, external_reference):
    data = _invocar_edge_function(MERCADOPAGO_PROXY_URL, {
        "action": "create_preference",
        "title": titulo,
        "amount": float(monto or 0),
        "payer_email": payer_email or "",
        "external_reference": external_reference or "",
    }) or {}
    if not data.get("ok"):
        return None, None
    return data.get("init_point"), data.get("id")


def mp_verificar_pago(external_reference, preference_id=None):
    data = _invocar_edge_function(MERCADOPAGO_PROXY_URL, {
        "action": "verify_payment",
        "external_reference": external_reference or "",
        "preference_id": preference_id or "",
    }) or {}
    return bool(data.get("approved")), data.get("payment_id")


# =========================================================
# HELPERS HTTP
# =========================================================

def check_conexion():
    """Chequeo liviano usado por main.py para saber si Supabase responde."""
    try:
        r = http_requests.get(
            f"{REST_URL}/usuarios",
            headers=HEADERS,
            params={"select": "id", "limit": 1},
            timeout=8,
        )
        return r.status_code < 500
    except Exception as e:
        logger.error(f"check_conexion error: {e}")
        return False

def _rest_get(table, select="*", filters=None, order=None, limit=None):
    """GET a Supabase REST API."""
    global LAST_ERROR
    LAST_ERROR = ""
    url = f"{REST_URL}/{table}"
    params = {"select": select}
    if filters:
        params.update(filters)
    if order:
        params["order"] = order
    if limit:
        params["limit"] = limit
    try:
        r = http_requests.get(url, headers=HEADERS, params=params, timeout=15)
        if r.status_code >= 400:
            LAST_ERROR = r.text
            logger.error(f"GET {table} error {r.status_code}: {r.text}")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        if not LAST_ERROR:
            LAST_ERROR = str(e)
        logger.error(f"GET {table} error: {e}")
        return []


def _rest_post(table, data):
    """POST a Supabase REST API."""
    global LAST_ERROR
    LAST_ERROR = ""
    url = f"{REST_URL}/{table}"
    try:
        r = http_requests.post(url, headers=HEADERS, json=data, timeout=15)
        if r.status_code >= 400:
            LAST_ERROR = r.text
            logger.error(f"POST {table} error {r.status_code}: {r.text}")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        if not LAST_ERROR:
            LAST_ERROR = str(e)
        logger.error(f"POST {table} error: {e}")
        return None


def _rest_patch(table, data, filters):
    """PATCH a Supabase REST API."""
    global LAST_ERROR
    LAST_ERROR = ""
    url = f"{REST_URL}/{table}"
    # Construir query string manualmente para PATCH
    query_params = []
    for k, v in filters.items():
        query_params.append(f"{k}={v}")
    if query_params:
        url += "?" + "&".join(query_params)

    try:
        r = http_requests.patch(url, headers=HEADERS, json=data, timeout=15)
        if r.status_code >= 400:
            LAST_ERROR = r.text
            logger.error(f"PATCH {table} error {r.status_code}: {r.text}")
        r.raise_for_status()
        return r.json()
    except Exception as e:
        if not LAST_ERROR:
            LAST_ERROR = str(e)
        logger.error(f"PATCH {table} error: {e}")
        return None


def _rest_delete(table, filters):
    """DELETE a Supabase REST API."""
    global LAST_ERROR
    LAST_ERROR = ""
    url = f"{REST_URL}/{table}"
    try:
        r = http_requests.delete(url, headers=HEADERS, params=filters, timeout=15)
        if r.status_code >= 400:
            LAST_ERROR = r.text
            logger.error(f"DELETE {table} error {r.status_code}: {r.text}")
        r.raise_for_status()
        return True
    except Exception as e:
        if not LAST_ERROR:
            LAST_ERROR = str(e)
        logger.error(f"DELETE {table} error: {e}")
        return False


# =========================================================
# HELPERS
# =========================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


# =========================================================
# PUSH NOTIFICATIONS
# =========================================================

def _enviar_notificacion_push(tipo, data):
    try:
        res = http_requests.post(
            NOTIFICACIONES_URL,
            json={"tipo": tipo, "data": data},
            headers={
                "apikey": SUPABASE_KEY,
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SUPABASE_KEY}"
            },
            timeout=20
        )
        logger.info(f"Push {tipo}: {res.status_code} - {res.text[:180]}")
        return res.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Error push {tipo}: {e}")
        return False


def notificar_consulta_pagada(abogado_uid, tipo_servicio, monto, consulta_id=None, cliente_email=""):
    _enviar_notificacion_push("consulta_pagada", {
        "abogado_uid": abogado_uid,
        "tipo_servicio": tipo_servicio,
        "monto": monto,
        "consulta_id": str(consulta_id or ""),
        "cliente_email": cliente_email,
    })


def notificar_consulta_aceptada(cliente_uid, tipo_servicio, consulta_id=None):
    _enviar_notificacion_push("consulta_aceptada", {
        "cliente_uid": cliente_uid,
        "tipo_servicio": tipo_servicio,
        "consulta_id": str(consulta_id or ""),
    })


def notificar_nuevo_mensaje(consulta_id, emisor_uid, receptor_uid, texto):
    preview = texto[:50] + "..." if len(texto) > 50 else texto
    usuario = obtener_usuario(emisor_uid) or {}
    emisor_nombre = (
        usuario.get("nombre")
        or usuario.get("email")
        or "Nuevo mensaje"
    )
    _enviar_notificacion_push("nuevo_mensaje", {
        "consulta_id": str(consulta_id),
        "emisor_uid": emisor_uid,
        "receptor_uid": receptor_uid,
        "emisor_nombre": str(emisor_nombre),
        "preview": preview,
    })


def notificar_videollamada(cliente_uid, consulta_id):
    _enviar_notificacion_push("videollamada", {
        "cliente_uid": cliente_uid,
        "consulta_id": str(consulta_id),
    })


def notificar_consulta_finalizada(cliente_uid, consulta_id=None):
    _enviar_notificacion_push("consulta_finalizada", {
        "cliente_uid": cliente_uid,
        "consulta_id": str(consulta_id or ""),
    })


def notificar_retiro_pagado(abogado_uid, monto_neto):
    _enviar_notificacion_push("retiro_pagado", {
        "abogado_uid": abogado_uid,
        "monto_neto": str(monto_neto or 0),
    })


# =========================================================
# HONORARIOS
# =========================================================

def acreditar_honorario(abogado_uid, tipo_servicio):
    config = obtener_configuracion()

    try:
        precio_chat = int(config.get("precio_chat", 1000))
    except:
        precio_chat = 1000

    try:
        precio_video = int(config.get("precio_video", 3000))
    except:
        precio_video = 3000

    try:
        precio_urgente = int(config.get("precio_urgente", 5000))
    except:
        precio_urgente = 5000

    precios = {
        "chat": precio_chat,
        "video": precio_video,
        "urgente": precio_urgente
    }

    monto = precios.get(tipo_servicio, precio_chat)
    comision = round(monto * 0.20)
    neto = monto - comision

    try:
        user = obtener_usuario(abogado_uid)
        if user:
            saldo_actual = user.get("saldo", 0) or 0
            actualizar_usuario(abogado_uid, {"saldo": saldo_actual + neto})

        logger.info(f"Honorario acreditado neto={neto} comision={comision}")
        return neto, comision

    except Exception as e:
        logger.error(f"ERROR acreditar_honorario: {e}")
        return 0, 0


def sincronizar_saldo_abogado(abogado_uid):
    try:
        if not abogado_uid:
            return 0

        config = obtener_configuracion()

        def precio_tipo(tipo, fallback=1000):
            try:
                return int(config.get(f"precio_{tipo}", fallback))
            except Exception:
                return fallback

        precios = {
            "chat": precio_tipo("chat", 1000),
            "video": precio_tipo("video", 3000),
            "urgente": precio_tipo("urgente", 5000),
        }

        consultas = obtener_consultas_usuario(abogado_uid, "abogado")
        refs_contadas = set()
        total_neto = 0

        for consulta_id, consulta in consultas:
            estado = str(consulta.get("estado") or "").lower()
            if estado not in ["pagado", "en_curso", "videollamada", "finalizado"]:
                continue

            ref = consulta.get("external_reference") or f"id:{consulta_id}"
            if ref in refs_contadas:
                continue
            refs_contadas.add(ref)

            tipo = consulta.get("tipo_servicio", "chat") or "chat"
            try:
                monto = int(consulta.get("monto") or consulta.get("precio") or precios.get(tipo, 1000))
            except Exception:
                monto = precios.get(tipo, 1000)

            comision = round(monto * 0.20)
            total_neto += monto - comision

        retiros = []
        try:
            retiros = _rest_get("retiros", filters={"abogado_uid": f"eq.{abogado_uid}"})
        except Exception:
            user = obtener_usuario(abogado_uid) or {}
            abogado_email = user.get("email", "")
            if abogado_email:
                try:
                    retiros = _rest_get("retiros", filters={"abogado_email": f"eq.{abogado_email}"})
                except Exception:
                    retiros = []

        total_retirado = 0
        for retiro in retiros:
            estado = str(retiro.get("estado") or "").lower()
            if estado in ["rechazado", "cancelado"]:
                continue
            try:
                total_retirado += int(retiro.get("monto_neto") or retiro.get("monto_bruto") or 0)
            except Exception:
                pass

        saldo = max(total_neto - total_retirado, 0)
        actualizar_usuario(abogado_uid, {"saldo": saldo})
        return saldo

    except Exception as e:
        logger.error(f"ERROR sincronizar_saldo_abogado: {e}")
        return 0


# =========================================================
# USUARIOS
# =========================================================

def crear_usuario_db(uid, email, nombre, rol="cliente", telefono="", datos_extra=None):
    try:
        existente = obtener_usuario_por_email(email)
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

        res = _rest_post("usuarios", data)
        return True, None if res else "Error al crear usuario"
    except Exception as e:
        logger.error(e)
        return False, str(e)


def obtener_usuario(uid):
    try:
        res = _rest_get("usuarios", filters={"uid": f"eq.{uid}"}, limit=1)
        return res[0] if res else None
    except Exception as e:
        logger.error(e)
        return None


def obtener_usuario_por_email(email):
    try:
        res = _rest_get("usuarios", filters={"email": f"eq.{email}"}, limit=1)
        return res[0] if res else None
    except Exception as e:
        logger.error(e)
        return None


def actualizar_usuario(uid, datos):
    try:
        res = _rest_patch("usuarios", datos, {"uid": f"eq.{uid}"})
        if res is None:
            logger.error(f"actualizar_usuario fallo uid={uid}: {LAST_ERROR}")
            return False
        return True
    except Exception as e:
        logger.error(e)
        return False


def listar_abogados(disponibles=True, provincia=None, ciudad=None):
    try:
        # Construir query string manualmente para filtros complejos
        filters = {
            "rol": "eq.abogado",
            "suscripcion_activa": "eq.true",
            "aprobado": "eq.true"
        }
        if disponibles:
            filters["estado_abogado"] = "neq.ocupado"
        if provincia:
            filters["provincia"] = f"eq.{provincia}"
        if ciudad and ciudad != "Otras":
            filters["ciudad"] = f"eq.{ciudad}"
        abogados = _rest_get("usuarios", filters=filters)
        return [a for a in abogados if suscripcion_habilitada(a)]
    except Exception as e:
        logger.error(f"ERROR listar_abogados: {e}")
        return []


def obtener_resenas_abogado(email):
    try:
        return _rest_get(
            "resenas",
            filters={"abogado_email": f"eq.{email}"},
            order="id.desc"
        )
    except Exception as e:
        logger.error(f"ERROR obtener_resenas_abogado: {e}")
        return []


def guardar_resena(consulta_id, abogado_email, cliente_email, puntaje, comentario=""):
    try:
        if not consulta_id or not abogado_email or not cliente_email:
            return False

        existente = _rest_get("resenas", filters={"consulta_id": f"eq.{consulta_id}"}, limit=1)
        if existente:
            _rest_patch(
                "resenas",
                {
                    "abogado_email": abogado_email,
                    "cliente_email": cliente_email,
                    "puntaje": int(puntaje or 0),
                    "comentario": str(comentario or "").strip(),
                    "fecha": now_iso(),
                },
                {"consulta_id": f"eq.{consulta_id}"}
            )
            return True

        data = {
            "consulta_id": consulta_id,
            "abogado_email": abogado_email,
            "cliente_email": cliente_email,
            "puntaje": int(puntaje or 0),
            "comentario": str(comentario or "").strip(),
            "fecha": now_iso(),
        }
        res = _rest_post("resenas", data)
        return bool(res)
    except Exception as e:
        logger.error(f"ERROR guardar_resena: {e}")
        return False


def activar_suscripcion_abogado(uid, monto, especialidades):
    try:
        datos = {
            "suscripcion_activa": True,
            "suscripcion_fecha": now_iso(),
            "suscripcion_monto": monto,
            "estado_abogado": "disponible",
            "especialidades": especialidades,
            "aprobado": False,
        }
        if especialidades:
            datos["especialidad"] = especialidades[0]
        _rest_patch("usuarios", datos, {"uid": f"eq.{uid}"})
        return True
    except Exception as e:
        logger.error(f"ERROR activar_suscripcion: {e}")
        return False


def _monto_suscripcion_valido(monto):
    try:
        return float(monto or 0) > 0
    except Exception:
        return False


def tiene_pago_suscripcion_valido(user):
    if not user:
        return False
    return bool(user.get("suscripcion_fecha")) and _monto_suscripcion_valido(
        user.get("suscripcion_monto")
    )


def suscripcion_habilitada(user):
    if not user:
        return False
    return bool(user.get("suscripcion_activa", False)) and tiene_pago_suscripcion_valido(user)


def desactivar_suscripcion_abogado(uid):
    try:
        _rest_patch("usuarios", {
            "suscripcion_activa": False,
            "estado_abogado": "ocupado"
        }, {"uid": f"eq.{uid}"})
        return True
    except Exception as e:
        logger.error(f"ERROR desactivar_suscripcion: {e}")
        return False

def reactivar_abogado(uid):
    try:
        user = obtener_usuario(uid)
        if not user:
            return False, "No se encontró el abogado"
        if not tiene_pago_suscripcion_valido(user):
            return False, "No se puede reactivar: no hay una suscripción paga válida"
        _rest_patch("usuarios", {
            "suscripcion_activa": True,
            "estado_abogado": "disponible"
        }, {"uid": f"eq.{uid}"})
        return True, "Abogado reactivado"
    except Exception as e:
        logger.error(f"ERROR reactivar_abogado: {e}")
        return False, str(e)


def aprobar_abogado(uid):
    try:
        user = obtener_usuario(uid)
        if not user:
            return False, "No se encontró el abogado"
        if not user.get("email_verified", False):
            return False, "No se puede aprobar: el email no está verificado"
        if not suscripcion_habilitada(user):
            return False, "No se puede aprobar: falta una suscripción paga válida"
        _rest_patch("usuarios", {"aprobado": True}, {"uid": f"eq.{uid}"})
        return True, "Abogado aprobado"
    except Exception as e:
        logger.error(f"ERROR aprobar_abogado: {e}")
        return False, str(e)


# =========================================================
# STORAGE - FOTO PERFIL
# =========================================================

def subir_foto_perfil(uid, path_local):
    """Sube foto de perfil a Supabase Storage y retorna la URL publica."""
    try:
        ext = os.path.splitext(path_local)[1].lower() or ".jpg"
        version = int(datetime.now(timezone.utc).timestamp())
        content_type = f"image/{ext.replace('.', '')}" if ext != ".jpg" else "image/jpeg"
        bucket_candidatos = ["chat-files"]

        with open(path_local, "rb") as f:
            contenido = f.read()

        ultimo_error = None
        for bucket in bucket_candidatos:
            path_storage = f"avatars/{uid}_{version}{ext}"
            upload_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path_storage}"
            upload_headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": content_type,
                "x-upsert": "true"
            }
            try:
                logger.info(f"subir_foto_perfil: subiendo uid={uid} bucket={bucket} path={path_storage}")
                r = http_requests.post(upload_url, headers=upload_headers, data=contenido, timeout=30)
                if r.status_code >= 400:
                    ultimo_error = r.text
                    logger.error(f"ERROR subir_foto_perfil bucket={bucket} status={r.status_code}: {r.text}")
                    continue

                r.raise_for_status()
                url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path_storage}"
                ok_db = actualizar_usuario(uid, {"foto_url": url})
                if not ok_db:
                    logger.error(f"ERROR actualizar foto_url en usuarios tras subir foto uid={uid}: {LAST_ERROR}")
                    verificado = _rest_get("usuarios", filters={"uid": f"eq.{uid}"}, limit=1)
                    foto_actual = (verificado[0].get("foto_url") if verificado else "") or ""
                    if str(foto_actual).strip() != url:
                        ultimo_error = LAST_ERROR or "No se pudo persistir foto_url en usuarios"
                        continue

                verificado = _rest_get("usuarios", filters={"uid": f"eq.{uid}"}, limit=1)
                foto_actual = (verificado[0].get("foto_url") if verificado else "") or ""
                if str(foto_actual).strip() != url:
                    ultimo_error = "La foto se subio, pero foto_url no quedo guardada en Supabase"
                    logger.error(f"ERROR verificacion foto_url uid={uid}: esperado={url} actual={foto_actual}")
                    continue

                logger.info(f"Foto perfil subida correctamente bucket={bucket} url={url}")
                return True, url
            except Exception as e_bucket:
                ultimo_error = str(e_bucket)
                logger.error(f"ERROR subir_foto_perfil bucket={bucket}: {e_bucket}")
                continue

        logger.error(f"ERROR subir_foto_perfil final: {ultimo_error}")
        return False, None

    except Exception as e:
        logger.error(f"ERROR subir_foto_perfil: {e}")
        return False, None


def subir_archivo_chat(consulta_id, path_local, nombre):
    """Sube archivo al chat con validacion de tipo y tamanio."""
    try:
        ext = os.path.splitext(nombre)[1].lower()
        if ext not in EXTENSIONES_CHAT:
            return False, f"Tipo de archivo no permitido: {ext}"

        tamano_mb = os.path.getsize(path_local) / (1024 * 1024)
        if tamano_mb > 50:
            return False, "Archivo muy grande. Maximo 50MB"

        bucket = "chat-files"
        path_storage = f"{consulta_id}/{nombre}"

        upload_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}/{path_storage}"
        content_type = mimetypes.guess_type(nombre)[0] or "application/octet-stream"
        if ext == ".pdf":
            content_type = "application/pdf"
        elif ext in [".jpg", ".jpeg"]:
            content_type = "image/jpeg"
        elif ext == ".png":
            content_type = "image/png"
        elif ext == ".webp":
            content_type = "image/webp"
        elif ext == ".doc":
            content_type = "application/msword"
        elif ext == ".docx":
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext in [".mp4", ".m4v"]:
            content_type = "video/mp4"
        elif ext == ".mov":
            content_type = "video/quicktime"
        elif ext == ".3gp":
            content_type = "video/3gpp"
        elif ext == ".webm":
            content_type = "video/webm"
        elif ext == ".mp3":
            content_type = "audio/mpeg"
        elif ext in [".m4a", ".aac"]:
            content_type = "audio/mp4"
        elif ext == ".wav":
            content_type = "audio/wav"
        elif ext in [".ogg", ".opus"]:
            content_type = "audio/ogg"
        upload_headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": content_type,
            "x-upsert": "true"
        }
        with open(path_local, "rb") as f:
            r = http_requests.post(upload_url, headers=upload_headers, data=f, timeout=60)
        if r.status_code >= 400:
            logger.error(f"ERROR subir_archivo_chat {r.status_code}: {r.text}")
            return False, r.text[:180]
        r.raise_for_status()

        url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path_storage}"
        return True, url

    except Exception as e:
        logger.error(e)
        return False, str(e)


def eliminar_archivo_chat(url_archivo):
    try:
        url_archivo = str(url_archivo or "").strip()
        if not url_archivo:
            return True

        marcador = "/storage/v1/object/public/chat-files/"
        if marcador not in url_archivo:
            return True

        path_storage = url_archivo.split(marcador, 1)[1].split("?", 1)[0].strip("/")
        if not path_storage:
            return True

        delete_url = f"{SUPABASE_URL}/storage/v1/object/chat-files/{path_storage}"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        r = http_requests.delete(delete_url, headers=headers, timeout=20)
        if r.status_code not in [200, 204, 404]:
            logger.error(f"ERROR eliminar_archivo_chat {r.status_code}: {r.text}")
            return False
        return True
    except Exception as e:
        logger.error(f"ERROR eliminar_archivo_chat: {e}")
        return False


def eliminar_foto_perfil(url_archivo):
    try:
        return eliminar_archivo_chat(url_archivo)
    except Exception as e:
        logger.error(f"ERROR eliminar_foto_perfil: {e}")
        return False


def eliminar_mensaje_chat(mensaje_id, emisor_uid=None, archivo=None):
    try:
        patch_filters = {"id": f"eq.{mensaje_id}"}

        _rest_patch("mensajes", {
            "texto": MENSAJE_ELIMINADO_TEXTO,
            "archivo": None,
        }, patch_filters)

        restante = []
        try:
            restante = _rest_get("mensajes", filters={"id": f"eq.{mensaje_id}"}, limit=1)
        except Exception:
            restante = []

        if restante:
            msg = restante[0] or {}
            texto_actual = str(msg.get("texto") or msg.get("mensaje") or "").strip()
            archivo_actual = msg.get("archivo")
            if texto_actual != MENSAJE_ELIMINADO_TEXTO or archivo_actual:
                logger.error(
                    f"eliminar_mensaje_chat fallo id={mensaje_id} uid={emisor_uid}: {LAST_ERROR or texto_actual}"
                )
                return False

        if archivo:
            eliminar_archivo_chat(archivo)

        return True
    except Exception as e:
        logger.error(f"ERROR eliminar_mensaje_chat: {e}")
        return False


def eliminar_cuenta_completa(uid, email="", foto_url="", id_token=None, refresh_token=None):
    try:
        uid = str(uid or "").strip()
        email = str(email or "").strip().lower()
        foto_url = str(foto_url or "").strip()

        if not uid:
            return False, "No se encontro la cuenta a eliminar"

        consultas_cliente = obtener_consultas_usuario(uid, "cliente") or []
        consultas_abogado = obtener_consultas_usuario(uid, "abogado") or []
        consultas = {}
        for consulta_id, data in consultas_cliente + consultas_abogado:
            consultas[str(consulta_id)] = data or {}

        for consulta_id in consultas.keys():
            try:
                _rest_delete("mensajes", {"consulta_id": f"eq.{consulta_id}"})
            except Exception:
                pass
            try:
                _rest_delete("resenas", {"consulta_id": f"eq.{consulta_id}"})
            except Exception:
                pass

        try:
            _rest_delete("mensajes", {"emisor_uid": f"eq.{uid}"})
        except Exception:
            pass

        try:
            _rest_delete("codigos_verificacion", {"uid": f"eq.{uid}"})
        except Exception:
            pass

        try:
            _rest_delete("retiros", {"abogado_uid": f"eq.{uid}"})
        except Exception:
            pass

        if email:
            try:
                _rest_delete("retiros", {"abogado_email": f"eq.{email}"})
            except Exception:
                pass
            try:
                _rest_delete("consultas", {"cliente_email": f"eq.{email}"})
            except Exception:
                pass
            try:
                _rest_delete("consultas", {"abogado_email": f"eq.{email}"})
            except Exception:
                pass
            try:
                _rest_delete("resenas", {"cliente_email": f"eq.{email}"})
            except Exception:
                pass
            try:
                _rest_delete("resenas", {"abogado_email": f"eq.{email}"})
            except Exception:
                pass

        try:
            _rest_delete("consultas", {"cliente_uid": f"eq.{uid}"})
        except Exception:
            pass
        try:
            _rest_delete("consultas", {"abogado_uid": f"eq.{uid}"})
        except Exception:
            pass

        if foto_url:
            try:
                eliminar_foto_perfil(foto_url)
            except Exception:
                pass

        ok_usuario = _rest_delete("usuarios", {"uid": f"eq.{uid}"})
        if not ok_usuario:
            return False, "No se pudo borrar la cuenta en Supabase"

        token_a_borrar = id_token
        if refresh_token:
            try:
                ok_refresh, token_data, _ = firebase_auth_api.refrescar_id_token(refresh_token)
                if ok_refresh and token_data and token_data.get("id_token"):
                    token_a_borrar = token_data.get("id_token")
            except Exception:
                pass

        if token_a_borrar:
            ok_auth, err_auth = firebase_auth_api.borrar_usuario_auth(token_a_borrar)
            if not ok_auth:
                return False, f"Se borró en Supabase, pero falló Firebase Auth: {err_auth}"

        return True, "Cuenta eliminada correctamente"
    except Exception as e:
        logger.error(f"ERROR eliminar_cuenta_completa: {e}")
        return False, str(e)


# =========================================================
# REALTIME — NO DISPONIBLE EN ANDROID SIN supabase-py
# =========================================================

class _FakeListener:
    """Listener de fallback cuando realtime no esta disponible."""

    def unsubscribe(self):
        pass


def escuchar_mensajes(consulta_id, callback):
    """Escucha mensajes nuevos en tiempo real para una consulta.

    NOTA: Realtime requiere WebSocket y el paquete supabase-py.
    En Android sin el paquete, se usa polling como fallback.
    """
    logger.warning("Realtime no disponible en Android. Usar polling manual.")
    return _FakeListener()


def escuchar_consulta(consulta_id, callback):
    """Escucha cambios de estado en una consulta.

    NOTA: Realtime requiere WebSocket y el paquete supabase-py.
    En Android sin el paquete, se usa polling como fallback.
    """
    logger.warning("Realtime no disponible en Android. Usar polling manual.")
    return _FakeListener()


# =========================================================
# RETIROS
# =========================================================

def solicitar_retiro(uid, monto, cuenta_destino):
    try:
        sincronizar_saldo_abogado(uid)

        user = obtener_usuario(uid)
        if not user:
            return False, "Usuario no encontrado", 0

        cuenta_destino = str(cuenta_destino or "").strip()
        saldo = user.get("saldo", 0) or 0
        abogado_email = user.get("email", "")

        if monto <= 0:
            return False, "Monto invalido", 0

        if not cuenta_destino or len(cuenta_destino) < 6:
            return False, "Ingresa un alias o CBU valido", 0

        if monto > saldo:
            return False, f"Saldo insuficiente: ${saldo:,.0f}", 0

        pendientes = _rest_get(
            "retiros",
            filters={
                "abogado_uid": f"eq.{uid}",
                "estado": "eq.pendiente",
            },
            limit=1,
        )
        if not pendientes and abogado_email:
            pendientes = _rest_get(
                "retiros",
                filters={
                    "abogado_email": f"eq.{abogado_email}",
                    "estado": "eq.pendiente",
                },
                limit=1,
            )
        if pendientes:
            return False, "Ya tienes un retiro pendiente de aprobacion", 0

        neto = monto

        retiro = _rest_post("retiros", {
            "abogado_uid": uid,
            "abogado_email": abogado_email,
            "monto_bruto": monto,
            "comision_plataforma": 0,
            "monto_neto": neto,
            "cuenta_destino": cuenta_destino,
            "estado": "pendiente",
            "fecha": now_iso(),
        })

        if not retiro:
            return False, "No se pudo crear la solicitud de retiro", 0

        if cuenta_destino != str(user.get("cuenta_bancaria") or "").strip():
            actualizar_usuario(uid, {"cuenta_bancaria": cuenta_destino})
        actualizar_usuario(uid, {"saldo": saldo - monto})

        return True, "Retiro solicitado correctamente", neto

    except Exception as e:
        logger.error(f"ERROR solicitar_retiro: {e}")
        return False, str(e), 0


def listar_retiros_pendientes():
    try:
        return _rest_get("retiros", filters={"estado": "eq.pendiente"}, order="fecha.asc")
    except Exception as e:
        logger.error(f"ERROR listar_retiros_pendientes: {e}")
        return []


def procesar_retiro(retiro_id, admin_uid):
    try:
        res = _rest_get("retiros", filters={"id": f"eq.{retiro_id}"}, limit=1)
        if not res:
            return False, "Retiro no encontrado"

        retiro = res[0]
        if retiro.get("estado") != "pendiente":
            return False, "Ya procesado"

        actualizado = _rest_patch("retiros", {
            "estado": "pagado",
            "pagado_at": now_iso(),
            "admin_uid": admin_uid,
        }, {"id": f"eq.{retiro_id}"})
        if actualizado is None and LAST_ERROR:
            return False, "No se pudo marcar el retiro como pagado"

        abogado_uid = retiro.get("abogado_uid")
        if abogado_uid:
            notificar_retiro_pagado(abogado_uid, retiro.get("monto_neto", 0))

        return True, f"Retiro ${retiro.get('monto_neto', 0):,.0f} pagado"

    except Exception as e:
        logger.error(f"ERROR procesar_retiro: {e}")
        return False, str(e)


def crear_retiro(abogado_uid, abogado_email, monto_bruto, cuenta_destino):
    try:
        _rest_post("retiros", {
            "abogado_uid": abogado_uid,
            "abogado_email": abogado_email,
            "monto_bruto": monto_bruto,
            "comision_plataforma": 0,
            "monto_neto": monto_bruto,
            "cuenta_destino": cuenta_destino,
            "estado": "pendiente",
            "fecha": now_iso(),
        })
        return True, monto_bruto
    except Exception as e:
        logger.error(f"ERROR crear_retiro: {e}")
        return False, str(e)


# =========================================================
# VERIFICACION EMAIL (usando Firebase nativo — sin Resend)
# =========================================================

def enviar_codigo_verificacion(email, uid, id_token=None):
    """
    Envía email de verificación vía Firebase Auth.
    Requiere id_token del usuario recién creado/logueado.
    """
    try:
        if not id_token:
            logger.warning(f"No hay id_token para {email}, usando fallback de código")
            # Fallback: código de 6 dígitos (para testing sin email)
            codigo = str(uuid.uuid4().int)[:6]
            _rest_delete("codigos_verificacion", {"uid": f"eq.{uid}"})
            _rest_post("codigos_verificacion", {
                "uid": uid,
                "email": email,
                "codigo": codigo
            })
            logger.info(f"Código fallback generado para {email}")
            return True, "fallback"

        # Firebase nativo
        ok, error = enviar_verificacion_email(id_token)
        if ok:
            logger.info(f"Email de verificación enviado por Firebase a {email}")
            return True, "firebase"

        logger.error(f"Firebase verify email falló: {error}")
        return False, error

    except Exception as e:
        logger.error(f"ERROR enviar_codigo_verificacion: {e}")
        return False, str(e)


def reenviar_codigo_verificacion(email, uid, id_token=None):
    return enviar_codigo_verificacion(email, uid, id_token)


def verificar_email_con_codigo(uid, codigo=None, id_token=None):
    """
    Verifica email:
    - Si hay id_token: consulta Firebase directamente si email está verificado
    - Si hay código: verifica contra tabla codigos_verificacion (fallback)
    """
    try:
        # Modo Firebase nativo
        if id_token:
            ok, user_info, error = obtener_info_usuario(id_token)
            if ok and user_info.get("email_verified"):
                # ✅ SINCRONIZAR CON SUPABASE
                _rest_patch("usuarios", {"email_verified": True}, {"uid": f"eq.{uid}"})
                logger.info(f"Email verificado por Firebase para {uid}")
                return True, "Cuenta verificada correctamente"
            return False, "Email no verificado aún. Revisá tu bandeja de entrada y tocá el link del email."

        # Modo código de 6 dígitos (fallback)
        if codigo:
            res = _rest_get("codigos_verificacion", filters={
                "uid": f"eq.{uid}",
                "codigo": f"eq.{codigo}"
            }, limit=1)
            if not res:
                return False, "Código incorrecto"
            _rest_patch("usuarios", {"email_verified": True}, {"uid": f"eq.{uid}"})
            return True, "Cuenta verificada correctamente"

        return False, "Método de verificación no especificado"

    except Exception as e:
        logger.error(f"ERROR verificar_email_con_codigo: {e}")
        return False, str(e)


# =========================================================
# CONSULTAS
# =========================================================

def crear_consulta(data):
    try:
        data["created_at"] = now_iso()
        if "monto" not in data and "precio" in data:
            data["monto"] = data["precio"]
        if "precio" not in data and "monto" in data:
            data["precio"] = data["monto"]
        res = _rest_post("consultas", data)
        if res and isinstance(res, list) and res[0].get("id"):
            return True, res[0]["id"]
        if res and isinstance(res, dict) and res.get("id"):
            return True, res["id"]
        if res:
            filtros = {}
            if data.get("external_reference"):
                filtros["external_reference"] = f"eq.{data.get('external_reference')}"
            if data.get("cliente_uid"):
                filtros["cliente_uid"] = f"eq.{data.get('cliente_uid')}"
            if data.get("abogado_uid"):
                filtros["abogado_uid"] = f"eq.{data.get('abogado_uid')}"
            if data.get("tipo_servicio"):
                filtros["tipo_servicio"] = f"eq.{data.get('tipo_servicio')}"
            if data.get("estado"):
                filtros["estado"] = f"eq.{data.get('estado')}"
            recientes = _rest_get("consultas", filters=filtros, order="created_at.desc", limit=1)
            if recientes and recientes[0].get("id"):
                return True, recientes[0]["id"]
        return False, LAST_ERROR or "Supabase no devolvio id de consulta"
    except Exception as e:
        logger.error(e)
        return False, str(e)


def obtener_consulta(consulta_id):
    try:
        res = _rest_get("consultas", filters={"id": f"eq.{consulta_id}"}, limit=1)
        return res[0] if res else None
    except Exception as e:
        logger.error(e)
        return None


def obtener_consulta_por_external_reference(external_reference):
    try:
        if not external_reference:
            return None

        res = _rest_get(
            "consultas",
            filters={"external_reference": f"eq.{external_reference}"},
            limit=1
        )

        if res:
            return res[0]

        if LAST_ERROR and "external_reference" in LAST_ERROR:
            logger.error("Falta la columna consultas.external_reference")
            return {"_schema_error": True}

        return None
    except Exception as e:
        logger.error(f"ERROR obtener_consulta_por_external_reference: {e}")
        return None


def obtener_consultas_usuario(uid, rol="cliente"):
    try:
        campo = "cliente_uid" if rol == "cliente" else "abogado_uid"
        res = _rest_get("consultas", filters={campo: f"eq.{uid}"})
        return [(c["id"], c) for c in res]
    except Exception as e:
        logger.error(f"ERROR obtener_consultas_usuario: {e}")
        return []


def actualizar_estado_consulta(consulta_id, estado):
    try:
        _rest_patch("consultas", {"estado": estado}, {"id": f"eq.{consulta_id}"})
        return True
    except Exception as e:
        logger.error(e)
        return False


def actualizar_consulta(consulta_id, datos):
    try:
        _rest_patch("consultas", datos, {"id": f"eq.{consulta_id}"})
        return True
    except Exception as e:
        logger.error(e)
        return False


def buscar_pago_procesado_disponible(external_reference=None, cliente_uid=None, abogado_uid=None, tipo_servicio=None):
    try:
        candidatos = []
        vistos = set()

        if external_reference:
            res = _rest_get(
                "pagos_procesados",
                filters={"external_reference": f"eq.{external_reference}"},
                order="processed_at.desc",
                limit=5
            )
            if res:
                for pago in res:
                    ref = pago.get("external_reference")
                    if ref and ref not in vistos:
                        vistos.add(ref)
                        candidatos.append(pago)

        if cliente_uid and abogado_uid and tipo_servicio:
            prefix = f"consulta|{cliente_uid}|{abogado_uid}|{tipo_servicio}|"
            res = _rest_get(
                "pagos_procesados",
                filters={"external_reference": f"like.{prefix}%"},
                order="processed_at.desc",
                limit=20
            )
            if res:
                for pago in res:
                    ref = pago.get("external_reference")
                    if ref and ref not in vistos:
                        vistos.add(ref)
                        candidatos.append(pago)

        for pago in candidatos:
            ref = pago.get("external_reference")
            if not ref:
                continue

            consulta = obtener_consulta_por_external_reference(ref)
            if consulta and consulta.get("_schema_error"):
                return None

            if consulta:
                estado = str(consulta.get("estado") or "").lower()
                if estado == "finalizado":
                    continue

                return {
                    "pago": pago,
                    "consulta": consulta,
                    "external_reference": ref
                }

            return {
                "pago": pago,
                "consulta": None,
                "external_reference": ref
            }

        return None

    except Exception as e:
        logger.error(f"ERROR buscar_pago_procesado_disponible: {e}")
        return None


def pago_procesado_existe(external_reference=None, cliente_uid=None, abogado_uid=None, tipo_servicio=None):
    try:
        return bool(buscar_pago_procesado_disponible(
            external_reference=external_reference,
            cliente_uid=cliente_uid,
            abogado_uid=abogado_uid,
            tipo_servicio=tipo_servicio,
        ))
    except Exception as e:
        logger.error(f"ERROR pago_procesado_existe: {e}")
        return False


def recuperar_consultas_pagadas_cliente(cliente_uid):
    try:
        if not cliente_uid:
            return 0

        prefix = f"consulta|{cliente_uid}|"
        pagos = _rest_get(
            "pagos_procesados",
            filters={"external_reference": f"like.{prefix}%"},
            order="processed_at.desc",
            limit=50
        )

        if not pagos:
            return 0

        cliente = obtener_usuario(cliente_uid) or {}
        config = obtener_configuracion() or {}

        def _precio(tipo):
            clave = f"precio_{tipo}"
            defecto = {
                "chat": 1000,
                "video": 3000,
                "urgente": 5000,
            }.get(tipo, 1000)
            try:
                return int(config.get(clave, defecto))
            except Exception:
                return defecto

        recuperadas = 0

        for pago in pagos:
            ref = pago.get("external_reference", "")
            partes = ref.split("|")

            if len(partes) < 5 or partes[0] != "consulta":
                continue

            pago_cliente_uid = partes[1]
            abogado_uid = partes[2]
            tipo_servicio = partes[3] or "chat"

            if pago_cliente_uid != cliente_uid:
                continue

            existente = obtener_consulta_por_external_reference(ref)
            if existente and existente.get("_schema_error"):
                return recuperadas
            if existente:
                continue

            abogado = obtener_usuario(abogado_uid) or {}
            data = {
                "cliente_uid": cliente_uid,
                "cliente_email": cliente.get("email", ""),
                "abogado_uid": abogado_uid,
                "abogado_email": abogado.get("email", ""),
                "tipo_servicio": tipo_servicio,
                "estado": "pagado",
                "monto": _precio(tipo_servicio),
                "area": "",
                "external_reference": ref,
                "created_at": pago.get("processed_at") or now_iso(),
            }

            ok, _ = crear_consulta(data)
            if ok:
                recuperadas += 1

        return recuperadas

    except Exception as e:
        logger.error(f"ERROR recuperar_consultas_pagadas_cliente: {e}")
        return 0


# =========================================================
# MENSAJES
# =========================================================

def enviar_mensaje(consulta_id, emisor_uid, texto, archivo=None):
    try:
        usuario = obtener_usuario(emisor_uid)
        email = usuario.get("email", "") if usuario else ""

        # Evita dobles inserciones inmediatas por doble toque, polling o eventos repetidos.
        try:
            recientes = _rest_get(
                "mensajes",
                filters={
                    "consulta_id": f"eq.{consulta_id}",
                    "emisor_uid": f"eq.{emisor_uid}",
                },
                order="created_at.desc",
                limit=3
            ) or []

            ahora = datetime.now(timezone.utc)
            texto_cmp = str(texto or "").strip()
            archivo_cmp = str(archivo or "").strip()

            for msg in recientes:
                texto_prev = str(msg.get("texto") or "").strip()
                archivo_prev = str(msg.get("archivo") or "").strip()
                created_prev = str(msg.get("created_at") or "").strip()
                if texto_prev != texto_cmp or archivo_prev != archivo_cmp:
                    continue
                if not created_prev:
                    continue
                try:
                    created_prev_dt = datetime.fromisoformat(created_prev.replace("Z", "+00:00"))
                    if abs((ahora - created_prev_dt).total_seconds()) <= 2.0:
                        logger.info(
                            f"Mensaje duplicado evitado consulta={consulta_id} uid={emisor_uid} texto={texto_cmp[:40]}"
                        )
                        return True
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"ERROR control duplicado mensaje: {e}")

        data = {
            "consulta_id": consulta_id,
            "emisor_uid": emisor_uid,
            "emisor_email": email,
            "texto": texto,
            "created_at": now_iso()
        }

        if archivo:
            data["archivo"] = archivo

        res = _rest_post("mensajes", data)
        if not res and archivo and "archivo" in LAST_ERROR:
            data.pop("archivo", None)
            data["texto"] = f"{texto}\n{archivo}"
            _rest_post("mensajes", data)

        consulta = obtener_consulta(consulta_id)
        if consulta:
            if emisor_uid == consulta.get("cliente_uid"):
                receptor_uid = consulta.get("abogado_uid")
            else:
                receptor_uid = consulta.get("cliente_uid")
            if receptor_uid:
                notificar_nuevo_mensaje(consulta_id, emisor_uid, receptor_uid, texto)

        return True
    except Exception as e:
        logger.error(e)
        return False


def obtener_mensajes(consulta_id):
    try:
        return _rest_get("mensajes", filters={"consulta_id": f"eq.{consulta_id}"}, order="created_at.asc")
    except Exception as e:
        logger.error(e)
        return []


def consulta_tiene_videollamada_iniciada(consulta_id):
    try:
        if not consulta_id:
            return False

        mensajes = obtener_mensajes(consulta_id)
        for msg in reversed(mensajes or []):
            texto = str(msg.get("texto") or msg.get("mensaje") or "").lower()
            if "inicio una videollamada" in texto:
                return True
        return False
    except Exception as e:
        logger.error(f"ERROR consulta_tiene_videollamada_iniciada: {e}")
        return False


# =========================================================
# RESENAS
# =========================================================

def tiene_resena(consulta_id):
    try:
        res = _rest_get("resenas", filters={"consulta_id": f"eq.{consulta_id}"}, limit=1)
        return len(res) > 0
    except Exception as e:
        logger.error(e)
        return False


# =========================================================
# CONFIGURACION
# =========================================================

def obtener_configuracion():
    try:
        res = _rest_get("configuracion")
        return {item["clave"]: item["valor"] for item in res}
    except Exception as e:
        logger.error(f"ERROR obtener_configuracion: {e}")
        return {}


def actualizar_configuracion(clave, valor):
    try:
        res = _rest_patch("configuracion", {"valor": str(valor)}, {"clave": f"eq.{clave}"})
        logger.info(f"actualizar_configuracion: {clave}={valor}, res={res}")
        return True if res is not None else False
    except Exception as e:
        logger.error(f"ERROR actualizar_configuracion: {e}")
        return False


# =========================================================
# FIREBASE AUTH (import desde firebase_auth.py)
# =========================================================

from firebase_auth import (
    crear_usuario_auth,
    crear_usuario_auth_completo,
    login_usuario_auth,
    enviar_reset_password,
    enviar_verificacion_email,
    obtener_info_usuario
)


# =========================================================
# COMPATIBILIDAD
# =========================================================

def crear_usuario(email, password, nombre, rol="cliente", telefono="", datos_extra=None):
    try:
        ok, uid, error = crear_usuario_auth(email, password, nombre)
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

        res = _rest_post("usuarios", data)
        if not res:
            return False, None, "Error al guardar usuario"

        return True, uid, None
    except Exception as e:
        logger.error(e)
        return False, None, str(e)


def crear_usuario_con_auth(email, password, nombre, rol="cliente", telefono="", datos_extra=None):
    try:
        ok, auth_data, error = crear_usuario_auth_completo(email, password, nombre)
        if not ok:
            return False, None, None, error

        uid = (auth_data or {}).get("uid")
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

        res = _rest_post("usuarios", data)
        if not res:
            return False, None, None, "Error al guardar usuario"

        return True, uid, auth_data, None
    except Exception as e:
        logger.error(e)
        return False, None, None, str(e)


def login_usuario(email, password):
    try:
        ok, auth_data, error = login_usuario_auth(email, password)
        if not ok:
            return False, None, error

        uid = auth_data["uid"]
        res = _rest_get("usuarios", filters={"uid": f"eq.{uid}"}, limit=1)

        if not res:
            return False, None, "Usuario no encontrado"

        user = res[0]

        if user.get("rol") == "abogado" and not suscripcion_habilitada(user):
            return False, None, "Suscripcion inactiva"

        user["idToken"] = auth_data["idToken"]
        user["refreshToken"] = auth_data.get("refreshToken")
        return True, user, None
    except Exception as e:
        logger.error(e)
        return False, None, str(e)



