# config.py — Legal App
import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
USE_LOCAL_DB = not (SUPABASE_URL and SUPABASE_ANON_KEY)

PRECIOS_CONSULTA = {
    "chat":    1000.0,
    "video":   3000.0,
    "urgente": 5000.0,
}
COMISION_PLATAFORMA = 0.05

PBKDF2_ITERATIONS = 260_000
PBKDF2_HASH = "sha256"
SALT_BYTES  = 32

APP_NAME    = "Legal App"
APP_VERSION = "1.0.0"
