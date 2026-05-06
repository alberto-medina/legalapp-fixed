from kivy.uix.screenmanager import Screen
from database import get_connection
import session
import hashlib


class LoginScreen(Screen):

    def login(self):
        email = self.ids.email.text.strip().lower()
        password = self.ids.password.text.strip()

        if not email or not password:
            print("LOGIN ERROR - campos vacios")
            return

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        print("INTENTO LOGIN:", email, password)
        print("HASH LOGIN:", password_hash)

        conn = get_connection()
        cursor = conn.cursor()

        # 🔥 Buscar SOLO por email
        cursor.execute("""
            SELECT * FROM users WHERE LOWER(email)=?
        """, (email,))

        user = cursor.fetchone()

        # DEBUG (te va a mostrar qué hay realmente)
        cursor.execute("SELECT email, password FROM users")
        print("USERS DB:", cursor.fetchall())

        conn.close()

        if user:
            print("HASH DB:", user[3])  # columna password

            # 🔥 Comparación directa de hash
            if user[3].strip() == password_hash.strip():
                session.current_user = user
                print("LOGIN OK:", user)

                if user[4] == "abogado":
                    self.manager.current = "abogado_panel"
                else:
                    self.manager.current = "dashboard"
                return

        print("LOGIN ERROR - password incorrecta o usuario no existe")

    def go_register(self):
        self.manager.current = "register"