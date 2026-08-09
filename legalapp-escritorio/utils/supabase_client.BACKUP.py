# utils/supabase_client.BACKUP.py — Juris Lex
# Cliente para Supabase (PostgreSQL en la nube).
# Reemplaza SQLite local cuando SUPABASE_URL y SUPABASE_ANON_KEY estan configuradas.
#
# SETUP:
#   1. Crear cuenta gratuita en https://supabase.com
#   2. Crear proyecto "jurislex"
#   3. Ir a Project Settings → API → copiar URL y anon key
#   4. Crear archivo .env en raiz del proyecto:
#        SUPABASE_URL=https://xxxx.supabase.co
#        SUPABASE_ANON_KEY=eyJhbGc...
#   5. pip install supabase --break-system-packages
#
# ESQUEMA EN SUPABASE:
#   Ejecutar el SQL de supabase_schema.sql en el SQL Editor de Supabase.

import logging
from functools import lru_cache
from config import SUPABASE_URL, SUPABASE_ANON_KEY, USE_LOCAL_DB

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_supabase():
    """
    Retorna cliente Supabase singleton.
    Lanza RuntimeError si las credenciales no están configuradas.
    """
    if USE_LOCAL_DB:
        raise RuntimeError(
            "Supabase no configurado. Configura SUPABASE_URL y SUPABASE_ANON_KEY "
            "en el archivo .env o variables de entorno."
        )
    try:
        from supabase import create_client, Client
        client: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("Supabase conectado OK")
        return client
    except ImportError:
        raise ImportError(
            "Librería supabase no instalada. "
            "Ejecuta: pip install supabase --break-system-packages"
        )
    except Exception as e:
        logger.error(f"Error conectando a Supabase: {e}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# OPERACIONES DE USUARIO (usando Supabase REST API)
# ─────────────────────────────────────────────────────────────────────────────

class SupabaseUserRepository:
    """
    Repositorio de usuarios usando Supabase.
    Misma interfaz que las funciones SQLite, pero en la nube.
    """

    def __init__(self):
        self.db = get_supabase()

    def get_by_email(self, email: str) -> dict | None:
        try:
            res = (
                self.db.table("users")
                .select("*")
                .eq("email", email.lower())
                .single()
                .execute()
            )
            return res.data
        except Exception as e:
            logger.error(f"get_by_email({email}): {e}")
            return None

    def create(self, username: str, email: str, password_hash: str,
               salt: str, rol: str, telefono: str) -> tuple[bool, str]:
        try:
            self.db.table("users").insert({
                "username":      username,
                "email":         email.lower(),
                "password_hash": password_hash,
                "salt":          salt,
                "rol":           rol,
                "telefono":      telefono,
            }).execute()
            return True, ""
        except Exception as e:
            err = str(e)
            if "duplicate" in err.lower() or "unique" in err.lower():
                return False, "Este email ya esta registrado"
            logger.error(f"create_user({email}): {e}")
            return False, "Error al registrar"

    def update_saldo(self, email: str, delta: float) -> bool:
        """Incrementa/decrementa saldo (usa RPC para atomicidad)."""
        try:
            self.db.rpc("increment_saldo", {
                "user_email": email.lower(),
                "delta": delta,
            }).execute()
            return True
        except Exception as e:
            logger.error(f"update_saldo({email}, {delta}): {e}")
            return False

    def update_perfil(self, email: str, data: dict) -> tuple[bool, str]:
        try:
            self.db.table("users").update(data).eq("email", email.lower()).execute()
            return True, ""
        except Exception as e:
            logger.error(f"update_perfil({email}): {e}")
            return False, "Error al actualizar perfil"


class SupabaseConsultaRepository:
    """Repositorio de consultas usando Supabase."""

    def __init__(self):
        self.db = get_supabase()

    def get_by_cliente(self, email: str) -> list[dict]:
        try:
            res = (
                self.db.table("consultas")
                .select("*")
                .eq("user_email", email.lower())
                .order("fecha", desc=True)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"get_consultas_cliente({email}): {e}")
            return []

    def get_by_abogado(self, email: str) -> list[dict]:
        try:
            res = (
                self.db.table("consultas")
                .select("*")
                .eq("abogado", email.lower())
                .order("fecha", desc=True)
                .execute()
            )
            return res.data or []
        except Exception as e:
            logger.error(f"get_consultas_abogado({email}): {e}")
            return []

    def create(self, user_email: str, abogado: str, tipo: str, monto: float) -> tuple[int | None, str]:
        try:
            res = self.db.table("consultas").insert({
                "user_email":   user_email.lower(),
                "abogado":      abogado.lower(),
                "tipo_servicio": tipo,
                "monto":        monto,
                "estado":       "pendiente",
            }).execute()
            return res.data[0]["id"], ""
        except Exception as e:
            logger.error(f"create_consulta: {e}")
            return None, "Error al crear consulta"
