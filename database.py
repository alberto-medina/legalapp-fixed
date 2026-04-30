import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "legal_app.db")
print("USANDO DB EN:", DB_PATH)


def get_connection():
    return sqlite3.connect(DB_PATH)


def create_tables():
    conn = get_connection()
    c = conn.cursor()

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
        cuenta_bancaria TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS consultas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT,
        abogado TEXT,
        estado TEXT,
        tipo_servicio TEXT,
        fecha TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS mensajes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        consulta_id INTEGER,
        emisor TEXT,
        mensaje TEXT,
        archivo TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS resenas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        consulta_id INTEGER UNIQUE,
        abogado_email TEXT,
        cliente_email TEXT,
        puntaje INTEGER,
        comentario TEXT,
        fecha TEXT
    )""")

    conn.commit()
    conn.close()


def actualizar_db():
    conn = get_connection()
    c = conn.cursor()

    # mensajes.archivo
    c.execute("PRAGMA table_info(mensajes)")
    if "archivo" not in [r[1] for r in c.fetchall()]:
        c.execute("ALTER TABLE mensajes ADD COLUMN archivo TEXT")

    # users: migraciones
    c.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in c.fetchall()]

    if "estado_abogado" not in cols:
        print("MIGRACION: agregando estado_abogado...")
        c.execute("ALTER TABLE users ADD COLUMN estado_abogado TEXT DEFAULT 'disponible'")
        c.execute("UPDATE users SET estado_abogado='disponible' WHERE estado_abogado IS NULL")

    if "cuenta_bancaria" not in cols:
        print("MIGRACION: agregando cuenta_bancaria...")
        c.execute("ALTER TABLE users ADD COLUMN cuenta_bancaria TEXT")

    conn.commit()
    conn.close()
    print("DB OK")


create_tables()
actualizar_db()
