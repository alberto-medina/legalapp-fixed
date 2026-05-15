import sqlite3
import os
from kivy.utils import platform
from kivy.app import App

COMISION_PLATAFORMA = 0.05  # 5% al momento del pago

PRECIOS_CONSULTA = {
    "chat":    1000.0,
    "video":   3000.0,
    "urgente": 5000.0,
}


# =========================================================
# RUTA DB
# =========================================================

def get_db_path():

    if platform == "android":

        app = App.get_running_app()

        return os.path.join(
            app.user_data_dir,
            "legal_app.db"
        )

    else:

        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "legal_app.db"
        )


def get_connection():

    return sqlite3.connect(get_db_path())


# =========================================================
# CREATE TABLES
# =========================================================

def create_tables():

    conn = get_connection()
    c = conn.cursor()

    # =====================================================
    # USERS
    # =====================================================

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT,
        email TEXT UNIQUE,
        password TEXT,
        rol TEXT,

        telefono TEXT,
        foto TEXT,

        matricula TEXT,
        experiencia TEXT,
        descripcion TEXT,

        estado_abogado TEXT DEFAULT 'disponible',

        cuenta_bancaria TEXT,

        saldo REAL DEFAULT 0.0,

        especialidad TEXT
    )
    """)

    # =====================================================
    # CONSULTAS
    # =====================================================

    c.execute("""
    CREATE TABLE IF NOT EXISTS consultas (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_email TEXT,
        abogado TEXT,

        estado TEXT,

        tipo_servicio TEXT,

        fecha TEXT,

        monto REAL DEFAULT 0.0,

        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # =====================================================
    # MENSAJES
    # =====================================================

    c.execute("""
    CREATE TABLE IF NOT EXISTS mensajes (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        consulta_id INTEGER,

        emisor TEXT,

        mensaje TEXT,

        archivo TEXT
    )
    """)

    # =====================================================
    # RESEÑAS
    # =====================================================

    c.execute("""
    CREATE TABLE IF NOT EXISTS resenas (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        consulta_id INTEGER UNIQUE,

        abogado_email TEXT,

        cliente_email TEXT,

        puntaje INTEGER,

        comentario TEXT,

        fecha TEXT
    )
    """)

    # =====================================================
    # RETIROS
    # =====================================================

    c.execute("""
    CREATE TABLE IF NOT EXISTS retiros (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        abogado_email TEXT,

        monto_bruto REAL,

        comision_plataforma REAL,

        monto_neto REAL,

        cuenta_destino TEXT,

        estado TEXT DEFAULT 'pendiente',

        fecha TEXT
    )
    """)

    conn.commit()
    conn.close()


# =========================================================
# ACTUALIZAR DB
# =========================================================

def actualizar_db():

    conn = get_connection()
    c = conn.cursor()

    # =====================================================
    # MENSAJES
    # =====================================================

    c.execute("PRAGMA table_info(mensajes)")

    cols_msg = [r[1] for r in c.fetchall()]

    if "archivo" not in cols_msg:

        c.execute("""
            ALTER TABLE mensajes
            ADD COLUMN archivo TEXT
        """)

    # =====================================================
    # USERS
    # =====================================================

    c.execute("PRAGMA table_info(users)")

    cols = [r[1] for r in c.fetchall()]

    if "estado_abogado" not in cols:

        c.execute("""
            ALTER TABLE users
            ADD COLUMN estado_abogado TEXT DEFAULT 'disponible'
        """)

        c.execute("""
            UPDATE users
            SET estado_abogado='disponible'
            WHERE estado_abogado IS NULL
        """)

    if "cuenta_bancaria" not in cols:

        c.execute("""
            ALTER TABLE users
            ADD COLUMN cuenta_bancaria TEXT
        """)

    if "saldo" not in cols:

        c.execute("""
            ALTER TABLE users
            ADD COLUMN saldo REAL DEFAULT 0.0
        """)

    # NUEVO
    if "especialidad" not in cols:

        c.execute("""
            ALTER TABLE users
            ADD COLUMN especialidad TEXT
        """)

    # =====================================================
    # CONSULTAS
    # =====================================================

    c.execute("PRAGMA table_info(consultas)")

    cols_consulta = [r[1] for r in c.fetchall()]

    if "monto" not in cols_consulta:

        c.execute("""
            ALTER TABLE consultas
            ADD COLUMN monto REAL DEFAULT 0.0
        """)

    # NUEVO: created_at para timestamp real
    if "created_at" not in cols_consulta:

        # SQLite no permite DEFAULT con ALTER TABLE, hacer en dos pasos
        c.execute("""
            ALTER TABLE consultas
            ADD COLUMN created_at TEXT
        """)

        # Actualizar registros existentes con timestamp actual
        from datetime import datetime
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute("""
            UPDATE consultas
            SET created_at = ?
            WHERE created_at IS NULL
        """, (ahora,))

    # =====================================================
    # ABOGADO DEMO
    # =====================================================

    c.execute("""
        UPDATE users
        SET especialidad='Civil'
        WHERE email='abogado@test.com'
    """)

    conn.commit()
    conn.close()

    print("DB OK")


# =========================================================
# USUARIOS DEMO
# =========================================================

def crear_usuarios_demo():

    import hashlib

    def hash_password(p):

        return hashlib.sha256(
            p.encode()
        ).hexdigest()

    conn = get_connection()
    c = conn.cursor()

    # =====================================================
    # ABOGADO
    # =====================================================

    c.execute("""
        SELECT email
        FROM users
        WHERE email=?
    """, ("abogado@test.com",))

    abogado = c.fetchone()

    if not abogado:

        c.execute("""
            INSERT INTO users (

                username,
                email,
                password,
                rol,
                telefono,
                saldo,
                especialidad,
                experiencia,
                descripcion,
                estado_abogado

            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            "Dr Test",
            "abogado@test.com",
            hash_password("1234"),
            "abogado",
            "",
            0.0,

            "Civil",

            "8 años",

            "Especialista en daños, contratos y asesoramiento legal.",

            "disponible"
        ))

    # =====================================================
    # CLIENTE
    # =====================================================

    c.execute("""
        SELECT email
        FROM users
        WHERE email=?
    """, ("cliente@test.com",))

    cliente = c.fetchone()

    if not cliente:

        c.execute("""
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

    print("USUARIOS DEMO OK")


# =========================================================
# ACREDITAR HONORARIO
# =========================================================

def acreditar_honorario(
    abogado_email,
    tipo_servicio
):

    monto_total = PRECIOS_CONSULTA.get(
        tipo_servicio,
        1000.0
    )

    comision = round(
        monto_total * COMISION_PLATAFORMA,
        2
    )

    monto_neto = round(
        monto_total - comision,
        2
    )

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        UPDATE users
        SET saldo = saldo + ?
        WHERE email=?
    """, (

        monto_neto,
        abogado_email
    ))

    conn.commit()
    conn.close()

    print(
        f"COBRO 5%: total=${monto_total} "
        f"comision=${comision} "
        f"neto_abogado=${monto_neto}"
    )

    return monto_neto, comision


# =========================================================
# RETIRO
# =========================================================

def solicitar_retiro(
    abogado_email,
    monto_bruto,
    cuenta=None
):

    from datetime import datetime

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT saldo, cuenta_bancaria
        FROM users
        WHERE email=?
    """, (abogado_email,))

    row = c.fetchone()

    if not row:

        conn.close()

        return (
            False,
            "Usuario no encontrado",
            0
        )

    saldo_actual = row[0] or 0.0

    cuenta_dest = (
        cuenta
        or row[1]
        or ""
    )

    if not cuenta_dest:

        conn.close()

        return (
            False,
            "Carga tu CBU/alias en Perfil antes de retirar",
            0
        )

    if monto_bruto <= 0:

        conn.close()

        return (
            False,
            "El monto debe ser mayor a 0",
            0
        )

    if monto_bruto > saldo_actual:

        conn.close()

        return (
            False,
            f"Saldo insuficiente. Disponible: ${saldo_actual:,.0f}",
            0
        )

    fecha = datetime.now().strftime(
        "%Y-%m-%d %H:%M"
    )

    c.execute("""
        UPDATE users
        SET saldo = saldo - ?
        WHERE email=?
    """, (

        monto_bruto,
        abogado_email
    ))

    c.execute("""
        INSERT INTO retiros (

            abogado_email,
            monto_bruto,
            comision_plataforma,
            monto_neto,
            cuenta_destino,
            estado,
            fecha

        )
        VALUES (?, ?, 0, ?, ?, 'pendiente', ?)
    """, (

        abogado_email,
        monto_bruto,
        monto_bruto,
        cuenta_dest,
        fecha
    ))

    conn.commit()
    conn.close()

    msg = (
        f"Retiro de ${monto_bruto:,.0f} solicitado\n"
        f"Se depositara en: {cuenta_dest}"
    )

    return True, msg, monto_bruto


# =========================================================
# VERIFICAR RESEÑA
# =========================================================

def tiene_resena(consulta_id):

    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT 1
        FROM resenas
        WHERE consulta_id=?
    """, (consulta_id,))

    row = c.fetchone()

    conn.close()

    return row is not None