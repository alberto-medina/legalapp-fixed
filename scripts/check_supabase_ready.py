import argparse
import json
import os
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from config import SUPABASE_KEY, SUPABASE_URL
except Exception as exc:
    print(f"ERROR: no pude importar SUPABASE_URL/SUPABASE_KEY desde config.py: {exc}")
    sys.exit(1)


REST_URL = f"{SUPABASE_URL}/rest/v1"
STORAGE_URL = f"{SUPABASE_URL}/storage/v1"
FUNCTIONS_URL = f"{SUPABASE_URL}/functions/v1"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}


REQUIRED_TABLES = {
    "usuarios": [
        "uid",
        "email",
        "nombre",
        "username",
        "telefono",
        "rol",
        "email_verified",
        "aprobado",
        "created_at",
        "matricula",
        "provincia",
        "ciudad",
        "descripcion",
        "experiencia",
        "especialidad",
        "especialidades",
        "estado_abogado",
        "suscripcion_activa",
        "suscripcion_fecha",
        "suscripcion_monto",
        "saldo",
        "foto_url",
        "cuenta_bancaria",
        "fcm_token",
    ],
    "consultas": [
        "id",
        "cliente_uid",
        "cliente_email",
        "abogado_uid",
        "abogado_email",
        "tipo_servicio",
        "estado",
        "monto",
        "area",
        "created_at",
    ],
    "mensajes": [
        "id",
        "consulta_id",
        "emisor_uid",
        "emisor_email",
        "texto",
        "created_at",
    ],
    "retiros": [
        "id",
        "abogado_uid",
        "abogado_email",
        "monto_bruto",
        "comision_plataforma",
        "monto_neto",
        "cuenta_destino",
        "estado",
        "fecha",
        "pagado_at",
        "admin_uid",
    ],
    "resenas": [
        "id",
        "consulta_id",
        "abogado_email",
        "cliente_uid",
        "puntaje",
        "comentario",
        "fecha",
    ],
    "configuracion": [
        "clave",
        "valor",
    ],
    "codigos_verificacion": [
        "uid",
        "email",
        "codigo",
    ],
}


REQUIRED_CONFIG_KEYS = {
    "precio_chat": "1000",
    "precio_video": "3000",
    "precio_urgente": "5000",
    "precio_suscripcion_base": "55000",
    "precio_especialidad_extra": "10000",
}


REQUIRED_BUCKETS = [
    "avatars",
    "chat-files",
]


def ok(msg):
    print(f"[OK] {msg}")


def warn(msg):
    print(f"[WARN] {msg}")


def fail(msg):
    print(f"[FALTA] {msg}")


def request(method, url, **kwargs):
    try:
        return requests.request(method, url, timeout=20, **kwargs)
    except Exception as exc:
        return exc


def check_connection():
    print("\n== Conexion ==")
    res = request("GET", f"{REST_URL}/", headers=HEADERS)
    if isinstance(res, Exception):
        fail(f"No se pudo conectar a Supabase: {res}")
        return False
    if res.status_code in (200, 300, 401, 404):
        ok(f"Supabase responde ({res.status_code})")
        return True
    fail(f"Respuesta inesperada de Supabase: {res.status_code} {res.text[:180]}")
    return False


def check_table_exists(table):
    res = request(
        "GET",
        f"{REST_URL}/{table}",
        headers=HEADERS,
        params={"select": "*", "limit": "0"},
    )
    if isinstance(res, Exception):
        return False, str(res)
    if res.status_code in (200, 206):
        return True, ""
    return False, f"{res.status_code} {res.text[:220]}"


def check_column(table, column):
    res = request(
        "GET",
        f"{REST_URL}/{table}",
        headers=HEADERS,
        params={"select": column, "limit": "0"},
    )
    if isinstance(res, Exception):
        return False, str(res)
    if res.status_code in (200, 206):
        return True, ""
    return False, f"{res.status_code} {res.text[:180]}"


def check_tables():
    print("\n== Tablas y columnas ==")
    total_missing = 0

    for table, columns in REQUIRED_TABLES.items():
        exists, error = check_table_exists(table)
        if not exists:
            fail(f"Tabla {table}: {error}")
            total_missing += 1 + len(columns)
            continue

        ok(f"Tabla {table}")
        missing_cols = []
        for column in columns:
            col_ok, col_error = check_column(table, column)
            if not col_ok:
                missing_cols.append((column, col_error))

        if not missing_cols:
            ok(f"{table}: columnas esperadas")
        else:
            for column, col_error in missing_cols:
                fail(f"{table}.{column}: {col_error}")
            total_missing += len(missing_cols)

    return total_missing


def check_config_values():
    print("\n== Configuracion ==")
    res = request(
        "GET",
        f"{REST_URL}/configuracion",
        headers=HEADERS,
        params={"select": "clave,valor"},
    )
    if isinstance(res, Exception):
        fail(f"No se pudo leer configuracion: {res}")
        return len(REQUIRED_CONFIG_KEYS)
    if res.status_code not in (200, 206):
        fail(f"No se pudo leer configuracion: {res.status_code} {res.text[:220]}")
        return len(REQUIRED_CONFIG_KEYS)

    rows = res.json()
    current = {str(row.get("clave")): str(row.get("valor")) for row in rows}
    missing = 0
    for key, default in REQUIRED_CONFIG_KEYS.items():
        if key in current and current[key] not in ("", "None", "null"):
            ok(f"{key} = {current[key]}")
        else:
            fail(f"Falta configuracion {key} (valor sugerido: {default})")
            missing += 1
    return missing


def check_buckets():
    print("\n== Storage buckets ==")
    res = request("GET", f"{STORAGE_URL}/bucket", headers=HEADERS)
    if isinstance(res, Exception):
        warn(f"No se pudieron listar buckets: {res}")
        return len(REQUIRED_BUCKETS)
    if res.status_code not in (200, 206):
        warn(f"No se pudieron listar buckets con anon key: {res.status_code} {res.text[:220]}")
        return len(REQUIRED_BUCKETS)

    rows = res.json()
    names = {bucket.get("name") or bucket.get("id") for bucket in rows}
    missing = 0
    for bucket in REQUIRED_BUCKETS:
        if bucket in names:
            ok(f"Bucket {bucket}")
        else:
            fail(f"Falta bucket {bucket}")
            missing += 1
    return missing


def check_edge_function():
    print("\n== Edge Function notificaciones-push ==")
    payload = {"tipo": "healthcheck", "data": {"source": "check_supabase_ready"}}
    res = request(
        "POST",
        f"{FUNCTIONS_URL}/notificaciones-push",
        headers=HEADERS,
        data=json.dumps(payload),
    )
    if isinstance(res, Exception):
        warn(f"No se pudo probar notificaciones-push: {res}")
        return 1
    if res.status_code in (200, 201, 202, 204, 400):
        ok(f"Function responde ({res.status_code})")
        if res.status_code == 400:
            warn("Respondio 400: existe, pero quizas no acepta healthcheck. Revisar logs si queres.")
        return 0
    fail(f"Function notificaciones-push no respondio bien: {res.status_code} {res.text[:220]}")
    return 1


def print_sql_help():
    print("\n== SQL sugerido para configuracion faltante ==")
    print("Si faltan claves en configuracion, podes correr algo asi en Supabase SQL Editor:")
    print()
    print("insert into configuracion (clave, valor) values")
    rows = []
    for key, value in REQUIRED_CONFIG_KEYS.items():
        rows.append(f"('{key}', '{value}')")
    print(",\n".join(rows) + "\nON CONFLICT (clave) DO NOTHING;")


def main():
    parser = argparse.ArgumentParser(
        description="Chequea tablas, columnas, configuracion, buckets y function de Supabase para Legal App."
    )
    parser.add_argument(
        "--skip-function",
        action="store_true",
        help="No prueba la Edge Function notificaciones-push.",
    )
    args = parser.parse_args()

    print("Legal App - chequeo Supabase")
    print(f"URL: {SUPABASE_URL}")

    missing = 0
    if check_connection():
        missing += check_tables()
        missing += check_config_values()
        missing += check_buckets()
        if not args.skip_function:
            missing += check_edge_function()
    else:
        missing += 1

    print_sql_help()

    print("\n== Resultado ==")
    if missing == 0:
        ok("Supabase parece listo para los flujos principales.")
        return 0

    fail(f"Hay {missing} punto(s) para revisar antes de produccion.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
