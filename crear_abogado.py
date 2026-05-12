from database import get_connection, create_tables
import hashlib


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# =========================================================
# CREAR TABLAS
# =========================================================

create_tables()

conn = get_connection()
cursor = conn.cursor()

# =========================================================
# BORRAR DEMOS ANTERIORES
# =========================================================

cursor.execute(
    "DELETE FROM users WHERE email=?",
    ("abogado@test.com",)
)

cursor.execute(
    "DELETE FROM users WHERE email=?",
    ("cliente@test.com",)
)

# =========================================================
# CREAR ABOGADO DEMO
# =========================================================

cursor.execute("""
    INSERT INTO users (
        username,
        email,
        password,
        rol,
        telefono,
        especialidad,
        matricula,
        experiencia,
        descripcion,
        estado_abogado,
        cuenta_bancaria,
        saldo
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    "Dr Test",
    "abogado@test.com",
    hash_password("1234"),
    "abogado",
    "387000000",
    "Derecho Penal",
    "MP-2025-TEST",
    "12 años",
    "Especialista en derecho penal, denuncias, defensa y causas urgentes.",
    "disponible",
    "",
    0.0
))

# =========================================================
# CREAR CLIENTE DEMO
# =========================================================

cursor.execute("""
    INSERT INTO users (
        username,
        email,
        password,
        rol,
        telefono
    )
    VALUES (?, ?, ?, ?, ?)
""", (
    "Cliente Test",
    "cliente@test.com",
    hash_password("1234"),
    "cliente",
    "123456"
))

conn.commit()
conn.close()

print("OK Abogado y Cliente creados correctamente")