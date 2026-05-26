# production_check.py

import os
import ast

# =========================================================
# RESULTADOS
# =========================================================

ERRORES = []
WARNINGS = []
OK = []

# =========================================================
# CARPETAS A IGNORAR
# =========================================================

IGNORAR = [
    ".buildozer",
    "venv",
    "__pycache__",
    ".git",
    ".gradle",
    "build",
    "bin"
]

# =========================================================
# HELPERS
# =========================================================

def ok(msg):

    OK.append(msg)

    print(f"[OK] {msg}")


def warning(msg):

    WARNINGS.append(msg)

    print(f"[WARNING] {msg}")


def error(msg):

    ERRORES.append(msg)

    print(f"[ERROR] {msg}")

# =========================================================
# BUSCAR ARCHIVOS PYTHON SEGURO
# =========================================================

python_files = []

for root, dirs, files in os.walk("."):

    # IGNORAR CARPETAS
    dirs[:] = [
        d for d in dirs
        if d not in IGNORAR
    ]

    for file in files:

        if file.endswith(".py"):

            full_path = os.path.join(
                root,
                file
            )

            python_files.append(full_path)

# =========================================================
# VERIFICAR SINTAXIS
# =========================================================

print("\n==============================")
print("VERIFICANDO PYTHON")
print("==============================")

if not python_files:

    error("No se encontraron archivos Python")

for file in python_files:

    try:

        with open(
            file,
            "r",
            encoding="utf-8"
        ) as f:

            source = f.read()

        ast.parse(source)

        ok(f"Sintaxis OK -> {file}")

    except SyntaxError as e:

        error(
            f"SyntaxError en {file}: {e}"
        )

    except Exception as e:

        error(
            f"Error leyendo {file}: {e}"
        )

# =========================================================
# IMPORTS
# =========================================================

print("\n==============================")
print("VERIFICANDO IMPORTS")
print("==============================")

modulos = [
    "kivy",
    "supabase",
    "firebase_admin",
    "requests",
    "dotenv"
]

for modulo in modulos:

    try:

        __import__(modulo)

        ok(f"Modulo instalado: {modulo}")

    except Exception:

        warning(
            f"Modulo faltante: {modulo}"
        )

# =========================================================
# VARIABLES ENV
# =========================================================

print("\n==============================")
print("VERIFICANDO .ENV")
print("==============================")

variables = [
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "RESEND_API_KEY"
]

for var in variables:

    value = os.getenv(var)

    if value:

        ok(f"Variable encontrada: {var}")

    else:

        warning(
            f"Falta variable: {var}"
        )

# =========================================================
# BUILD OZER
# =========================================================

print("\n==============================")
print("VERIFICANDO BUILDOZER")
print("==============================")

if os.path.exists("buildozer.spec"):

    ok("buildozer.spec encontrado")

    try:

        with open(
            "buildozer.spec",
            "r",
            encoding="utf-8"
        ) as f:

            content = f.read()

        permisos = [
            "INTERNET",
            "CAMERA",
            "RECORD_AUDIO"
        ]

        for permiso in permisos:

            if permiso in content:

                ok(
                    f"Permiso OK: {permiso}"
                )

            else:

                warning(
                    f"Falta permiso: {permiso}"
                )

    except Exception as e:

        error(
            f"Error leyendo buildozer.spec: {e}"
        )

else:

    error("No existe buildozer.spec")

# =========================================================
# FIREBASE
# =========================================================

print("\n==============================")
print("VERIFICANDO FIREBASE")
print("==============================")

firebase_ok = False

for root, dirs, files in os.walk("."):

    dirs[:] = [
        d for d in dirs
        if d not in IGNORAR
    ]

    for file in files:

        if file == "google-services.json":

            firebase_ok = True

            ok(
                "google-services.json encontrado"
            )

        if file == "serviceAccountKey.json":

            ok(
                "serviceAccountKey.json encontrado"
            )

if not firebase_ok:

    warning(
        "No se encontro google-services.json"
    )

# =========================================================
# KV FILES
# =========================================================

print("\n==============================")
print("VERIFICANDO KV")
print("==============================")

kv_count = 0

for root, dirs, files in os.walk("."):

    dirs[:] = [
        d for d in dirs
        if d not in IGNORAR
    ]

    for file in files:

        if file.endswith(".kv"):
            kv_count += 1

if kv_count > 0:

    ok(f"{kv_count} archivos KV encontrados")

else:

    warning("No se encontraron archivos KV")

# =========================================================
# SEGURIDAD
# =========================================================

print("\n==============================")
print("VERIFICANDO SEGURIDAD")
print("==============================")

for file in python_files:

    try:

        with open(
            file,
            "r",
            encoding="utf-8"
        ) as f:

            text = f.read().lower()

        if "service_role" in text:

            warning(
                f"Possible SERVICE ROLE exposure -> {file}"
            )

        if "password=" in text:

            warning(
                f"Possible hardcoded password -> {file}"
            )

        if "sk_" in text:

            warning(
                f"Possible secret key -> {file}"
            )

    except Exception:
        pass

# =========================================================
# ARCHIVOS IMPORTANTES
# =========================================================

print("\n==============================")
print("VERIFICANDO ARCHIVOS")
print("==============================")

archivos_importantes = [
    "main.py",
    "supabase_config.py",
    "firebase_auth.py"
]

for archivo in archivos_importantes:

    encontrado = False

    for root, dirs, files in os.walk("."):

        dirs[:] = [
            d for d in dirs
            if d not in IGNORAR
        ]

        if archivo in files:

            encontrado = True
            break

    if encontrado:

        ok(f"Archivo OK: {archivo}")

    else:

        error(
            f"Archivo faltante: {archivo}"
        )

# =========================================================
# RESULTADO FINAL
# =========================================================

print("\n==============================")
print("RESULTADO FINAL")
print("==============================")

print(f"\nOK: {len(OK)}")
print(f"WARNINGS: {len(WARNINGS)}")
print(f"ERRORES: {len(ERRORES)}")

if len(ERRORES) == 0:

    print("\n✅ APP LISTA PARA TESTING")

    if len(WARNINGS) == 0:

        print(
            "✅ POSIBLEMENTE LISTA PARA PRODUCCION"
        )

    else:

        print(
            "⚠️ Revisar warnings"
        )

else:

    print(
        "\n❌ APP CON ERRORES"
    )

# =========================================================
# ERRORES
# =========================================================

if ERRORES:

    print("\n===== ERRORES =====")

    for e in ERRORES:
        print(f"- {e}")

# =========================================================
# WARNINGS
# =========================================================

if WARNINGS:

    print("\n===== WARNINGS =====")

    for w in WARNINGS:
        print(f"- {w}")

print("\n==============================")
print("FIN ANALISIS")
print("==============================")