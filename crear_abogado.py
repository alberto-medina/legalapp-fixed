from database import get_connection, create_tables
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 👇 MUY IMPORTANTE
create_tables()

conn = get_connection()
cursor = conn.cursor()

# BORRAR SI EXISTEN
cursor.execute("DELETE FROM users WHERE email=?", ("abogado@test.com",))
cursor.execute("DELETE FROM users WHERE email=?", ("cliente@test.com",))

# CREAR ABOGADO
cursor.execute(
    """
    INSERT INTO users (username, email, password, rol, telefono)
    VALUES (?, ?, ?, ?, ?)
    """,
    ("Dr Test", "abogado@test.com", hash_password("1234"), "abogado", "")
)

# CREAR CLIENTE
cursor.execute(
    """
    INSERT INTO users (username, email, password, rol, telefono)
    VALUES (?, ?, ?, ?, ?)
    """,
    ("Cliente Test", "cliente@test.com", hash_password("1234"), "cliente", "123456")
)

conn.commit()
conn.close()

print("OK Abogado y Cliente creados correctamente")