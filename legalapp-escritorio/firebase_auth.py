# firebase_auth.py — VERSIÓN ANDROID COMPATIBLE (sin firebase_admin)
import os
import requests
from kivy.utils import platform

# =========================================================
# CONFIG
# =========================================================

from config import FIREBASE_API_KEY

API_KEY = FIREBASE_API_KEY

FIREBASE_AUTH_URL = "https://identitytoolkit.googleapis.com/v1"


# =========================================================
# HELPERS
# =========================================================

def _auth_post(endpoint, payload, params=None):
    """POST al Firebase Auth REST API."""
    url = f"{FIREBASE_AUTH_URL}/{endpoint}"
    if params:
        url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])
    try:
        r = requests.post(url, json=payload, timeout=15)
        data = r.json()
        if r.status_code == 200:
            return True, data, None
        error_msg = data.get("error", {}).get("message", "Error de autenticación")
        return False, None, error_msg
    except Exception as e:
        return False, None, str(e)


# =========================================================
# REFRESH TOKEN (NUEVO)
# =========================================================

def refrescar_id_token(refresh_token):
    """Obtiene un id_token fresco usando el refresh_token."""
    try:
        url = f"https://securetoken.googleapis.com/v1/token?key={API_KEY}"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        r = requests.post(url, data=payload, timeout=15)
        data = r.json()

        if r.status_code == 200:
            return True, {
                "id_token": data.get("id_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in")
            }, None
        else:
            error_msg = data.get("error", {}).get("message", "Error refrescando token")
            return False, None, error_msg

    except Exception as e:
        return False, None, str(e)


# =========================================================
# REGISTRO
# =========================================================

def crear_usuario_auth_completo(email, password, nombre):
    """Crea usuario en Firebase Auth vía REST API y devuelve tokens del alta."""
    try:
        ok, data, error = _auth_post(
            "accounts:signUp",
            {
                "email": email,
                "password": password,
                "displayName": nombre,
                "returnSecureToken": True
            },
            params={"key": API_KEY}
        )
        if not ok:
            return False, None, error

        return True, {
            "uid": data.get("localId"),
            "idToken": data.get("idToken"),
            "refreshToken": data.get("refreshToken"),
        }, None

    except Exception as e:
        return False, None, str(e)


def crear_usuario_auth(email, password, nombre):
    """Compatibilidad: devuelve solo uid."""
    ok, data, error = crear_usuario_auth_completo(email, password, nombre)
    if not ok:
        return False, None, error
    return True, (data or {}).get("uid"), None


# =========================================================
# LOGIN
# =========================================================

def login_usuario_auth(email, password):
    """Login vía Firebase Auth REST API."""
    try:
        ok, data, error = _auth_post(
            "accounts:signInWithPassword",
            {
                "email": email,
                "password": password,
                "returnSecureToken": True
            },
            params={"key": API_KEY}
        )
        if not ok:
            return False, None, error

        return True, {
            "uid": data.get("localId"),
            "idToken": data.get("idToken"),
            "refreshToken": data.get("refreshToken")
        }, None

    except Exception as e:
        return False, None, str(e)


# =========================================================
# RESET PASSWORD
# =========================================================

def enviar_reset_password(email):
    """Envía email de reset de password."""
    try:
        ok, _, error = _auth_post(
            "accounts:sendOobCode",
            {
                "requestType": "PASSWORD_RESET",
                "email": email
            },
            params={"key": API_KEY}
        )
        if not ok:
            return False, error
        return True, None

    except Exception as e:
        return False, str(e)


# =========================================================
# VERIFY EMAIL
# =========================================================

def enviar_verificacion_email(id_token):
    """Envía email de verificación."""
    try:
        ok, _, error = _auth_post(
            "accounts:sendOobCode",
            {
                "requestType": "VERIFY_EMAIL",
                "idToken": id_token
            },
            params={"key": API_KEY}
        )
        if not ok:
            return False, error
        return True, None

    except Exception as e:
        return False, str(e)


# =========================================================
# OBTENER INFO USUARIO
# =========================================================

def obtener_info_usuario(id_token):
    """Obtiene info del usuario incluyendo emailVerified."""
    try:
        ok, data, error = _auth_post(
            "accounts:lookup",
            {"idToken": id_token},
            params={"key": API_KEY}
        )
        if not ok:
            return False, None, error

        users = data.get("users", [])
        if not users:
            return False, None, "Usuario no encontrado"

        user = users[0]
        return True, {
            "uid": user.get("localId"),
            "email": user.get("email"),
            "email_verified": user.get("emailVerified", False),
            "display_name": user.get("displayName", ""),
        }, None
    except Exception as e:
        return False, None, str(e)


def borrar_usuario_auth(id_token):
    """Borra el usuario autenticado actualmente en Firebase Auth."""
    try:
        ok, _, error = _auth_post(
            "accounts:delete",
            {"idToken": id_token},
            params={"key": API_KEY}
        )
        if not ok:
            return False, error
        return True, None
    except Exception as e:
        return False, str(e)


