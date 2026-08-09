"""Script chico para probar admin-actions a mano.

Te pide tu email y contraseña de Firebase (la misma con la que entrás a la
app) SOLO en esta terminal, no las manda a ningún lado salvo a Firebase
para loguearte, y te imprime el id_token para que lo pegues en el panel
"Test" de la funcion admin-actions en el Dashboard de Supabase.

Uso:
    python scripts/obtener_id_token.py
"""
import getpass
import sys

import requests

FIREBASE_API_KEY = "AIzaSyBmBKc5MkGmWBjeEa2YPOqCKa9Ve3fxWbE"

email = input("Email: ").strip()
password = getpass.getpass("Password (no se muestra en pantalla): ")

res = requests.post(
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}",
    json={"email": email, "password": password, "returnSecureToken": True},
    timeout=15,
)
data = res.json()

if res.status_code != 200:
    print("\nERROR al loguearse:", data.get("error", {}).get("message", data))
    sys.exit(1)

print("\nLogin OK. Este es tu id_token (vence en 1 hora):\n")
print(data["idToken"])
print("\nPegalo en el campo id_token del Request Body en el panel Test de admin-actions.")
