"""Crea una cuenta nueva (Firebase Auth + fila en Supabase) para despues
promoverla a admin a mano desde el SQL Editor de Supabase.

No hace falta abrir la app. Corre 100% en tu computadora: el email y
password que pongas solo se mandan a Firebase (para crear la cuenta) y a
Supabase (para crear la fila en usuarios), nunca a mi.

Uso:
    python scripts/crear_cuenta_admin.py
"""
import getpass
import os
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config import SUPABASE_URL, SUPABASE_KEY, FIREBASE_API_KEY

nombre = input("Nombre (para mostrar en la app, ej. 'Admin'): ").strip() or "Admin"
email = input("Email para la cuenta admin: ").strip()
password = getpass.getpass("Password para esa cuenta (minimo 6 caracteres): ")

print("\nCreando cuenta en Firebase...")
res = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}",
    json={"email": email, "password": password, "displayName": nombre, "returnSecureToken": True},
    timeout=15,
)
data = res.json()

if res.status_code != 200:
    print("ERROR creando la cuenta en Firebase:", data.get("error", {}).get("message", data))
    sys.exit(1)

uid = data["localId"]
print(f"Cuenta creada en Firebase. uid = {uid}")

print("Creando la fila en Supabase (tabla usuarios)...")
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}
payload = {
    "uid": uid,
    "nombre": nombre,
    "username": nombre,
    "email": email,
    "telefono": "",
    "rol": "cliente",
    "email_verified": False,
    "aprobado": False,
}
res2 = requests.post(f"{SUPABASE_URL}/rest/v1/usuarios", headers=headers, json=payload, timeout=15)

if res2.status_code >= 400:
    print("ERROR creando la fila en Supabase:", res2.status_code, res2.text)
    sys.exit(1)

print("Fila creada en Supabase.")
print("\nAhora andá al SQL Editor de Supabase y corré exactamente esto:\n")
print(
    f"update public.usuarios\n"
    f"set rol = 'admin', aprobado = true, email_verified = true\n"
    f"where email = '{email}';"
)
print("\nDespues deslogueate y volve a entrar en la app con ese email/password.")
