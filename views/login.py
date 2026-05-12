from kivy.uix.screenmanager import Screen
from database import get_connection
import session
import hashlib


class LoginScreen(Screen):

    def login(self):
        email = self.ids.email.text.strip().lower()
        password = self.ids.password.text.strip()

        self.ids.error.text = ""

        if not email or not password:
            self.ids.error.text = "Completa email y contrasena"
            print("LOGIN ERROR - campos vacios")
            return

        password_hash = hashlib.sha256(password.encode()).hexdigest()

        print("INTENTO LOGIN:", email, password)
        print("HASH LOGIN:", password_hash)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM users WHERE LOWER(email)=?
        """, (email,))

        user = cursor.fetchone()

        cursor.execute("SELECT email, password FROM users")
        print("USERS DB:", cursor.fetchall())

        conn.close()

        if user:
            print("HASH DB:", user[3])

            if user[3].strip() == password_hash.strip():
                session.current_user = user
                print("LOGIN OK:", user)

                self.ids.email.text = ""
                self.ids.password.text = ""

                if user[4] == "abogado":
                    self.manager.current = "abogado_panel"
                else:
                    self.manager.current = "dashboard"

                return

        self.ids.error.text = "Email o contrasena incorrectos"
        print("LOGIN ERROR - password incorrecta o usuario no existe")

    def go_register(self):
        self.manager.current = "register"