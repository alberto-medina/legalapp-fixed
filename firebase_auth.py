import os
import requests
import firebase_admin

from firebase_admin import credentials
from firebase_admin import auth

# =========================================================
# FIREBASE INIT
# =========================================================

SERVICE_ACCOUNT_FILE = "serviceAccountKey.json"

if not firebase_admin._apps:
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)

        firebase_admin.initialize_app(cred)

        print("Firebase Auth conectado")
    else:
        raise FileNotFoundError(
            "Falta serviceAccountKey.json"
        )

# =========================================================
# API KEY
# =========================================================

API_KEY = "AIzaSyBmBKc5MkGmWBjeEa2YPOqCKa9Ve3fxWbE"

# =========================================================
# REGISTRO
# =========================================================

def crear_usuario_auth(email, password, nombre):

    try:

        user = auth.create_user(
            email=email,
            password=password,
            display_name=nombre
        )

        return True, user.uid, None

    except Exception as e:
        return False, None, str(e)

# =========================================================
# LOGIN
# =========================================================

def login_usuario_auth(email, password):

    try:

        url = (
            "https://identitytoolkit.googleapis.com/"
            f"v1/accounts:signInWithPassword?key={API_KEY}"
        )

        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }

        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        data = response.json()

        if response.status_code == 200:

            return True, {
                "uid": data["localId"],
                "idToken": data["idToken"],
                "refreshToken": data["refreshToken"]
            }, None

        # ✅ CORREGIDO: extraer mensaje de error como string
        error_msg = data.get("error", {}).get("message", "Error de autenticación")
        return False, None, error_msg

    except Exception as e:
        return False, None, str(e)

# =========================================================
# RESET PASSWORD
# =========================================================

def enviar_reset_password(email):

    try:

        url = (
            "https://identitytoolkit.googleapis.com/"
            f"v1/accounts:sendOobCode?key={API_KEY}"
        )

        payload = {
            "requestType": "PASSWORD_RESET",
            "email": email
        }

        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            return True, None

        # ✅ CORREGIDO: extraer mensaje de error como string
        data = response.json()
        error_msg = data.get("error", {}).get("message", "Error al enviar reset")
        return False, error_msg

    except Exception as e:
        return False, str(e)

# =========================================================
# VERIFY EMAIL
# =========================================================

def enviar_verificacion_email(id_token):

    try:

        url = (
            "https://identitytoolkit.googleapis.com/"
            f"v1/accounts:sendOobCode?key={API_KEY}"
        )

        payload = {
            "requestType": "VERIFY_EMAIL",
            "idToken": id_token
        }

        response = requests.post(
            url,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            return True, None

        # ✅ CORREGIDO: extraer mensaje de error como string
        data = response.json()
        error_msg = data.get("error", {}).get("message", "Error al enviar verificación")
        return False, error_msg

    except Exception as e:
        return False, str(e)