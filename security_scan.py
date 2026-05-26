# security_scan.py

import os

# =========================================================
# CONFIG
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
# BUSQUEDAS PELIGROSAS
# =========================================================

PATRONES = {
    "SERVICE ROLE": [
        "service_role",
        "SUPABASE_SERVICE_ROLE_KEY",
        "service-role"
    ],

    "SUPABASE KEYS": [
        "SUPABASE_KEY",
        "SUPABASE_ANON_KEY",
        "SUPABASE_URL"
    ],

    "TOKENS": [
        "token",
        "access_token",
        "refresh_token",
        "idToken"
    ],

    "PASSWORDS": [
        "password=",
        "password =",
        "senha",
        "clave"
    ],

    "SECRET KEYS": [
        "sk_",
        "secret",
        "private_key"
    ],

    "MERCADO PAGO": [
        "MP_ACCESS_TOKEN",
        "APP_USR",
        "mercadopago"
    ],

    "FIREBASE": [
        "firebase",
        "serviceAccountKey"
    ]
}

# =========================================================
# RESULTADOS
# =========================================================

encontrados = []

# =========================================================
# HELPERS
# =========================================================

def imprimir_divisor():

    print("\n" + "=" * 60)

# =========================================================
# ESCANEO
# =========================================================

print("\n🔍 ESCANEANDO SEGURIDAD...\n")

for root, dirs, files in os.walk("."):

    # IGNORAR CARPETAS
    dirs[:] = [
        d for d in dirs
        if d not in IGNORAR
    ]

    for file in files:

        if not (
            file.endswith(".py")
            or file.endswith(".env")
            or file.endswith(".kv")
            or file.endswith(".txt")
            or file.endswith(".json")
        ):
            continue

        full_path = os.path.join(root, file)

        try:

            with open(
                full_path,
                "r",
                encoding="utf-8",
                errors="ignore"
            ) as f:

                lines = f.readlines()

            for i, line in enumerate(lines):

                line_lower = line.lower()

                for categoria, patrones in PATRONES.items():

                    for patron in patrones:

                        if patron.lower() in line_lower:

                            encontrados.append({
                                "categoria": categoria,
                                "archivo": full_path,
                                "linea": i + 1,
                                "contenido": line.strip()
                            })

        except Exception as e:

            print(
                f"ERROR leyendo {full_path}: {e}"
            )

# =========================================================
# RESULTADOS
# =========================================================

imprimir_divisor()

print("RESULTADOS SECURITY SCAN")

imprimir_divisor()

if not encontrados:

    print("✅ No se encontraron riesgos")

else:

    print(
        f"⚠️ Se encontraron {len(encontrados)} posibles riesgos\n"
    )

    for item in encontrados:

        print(f"""
TIPO: {item['categoria']}
ARCHIVO: {item['archivo']}
LINEA: {item['linea']}
CODIGO: {item['contenido']}
""")

# =========================================================
# RESUMEN
# =========================================================

imprimir_divisor()

print("RESUMEN")

imprimir_divisor()

categorias = {}

for item in encontrados:

    cat = item["categoria"]

    categorias[cat] = categorias.get(cat, 0) + 1

for cat, total in categorias.items():

    print(f"{cat}: {total}")

print("\n✅ ESCANEO FINALIZADO")