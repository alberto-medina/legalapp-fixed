import os, shutil
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from database import get_connection
import session
from views.utils_avatar import get_avatar_source

FOTO_DIR = "assets/fotos"


def _copiar_foto(origen):
    os.makedirs(FOTO_DIR, exist_ok=True)
    ext  = os.path.splitext(origen)[1].lower()
    safe = session.current_user[2].replace("@", "_").replace(".", "_")
    dest = os.path.join(FOTO_DIR, f"perfil_{safe}{ext}")
    shutil.copy2(origen, dest)
    return dest


class PerfilScreen(Screen):

    def on_enter(self):
        if not session.current_user:
            return
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT username, email, telefono, foto, matricula,
                   experiencia, descripcion, rol, cuenta_bancaria
            FROM users WHERE email=?
        """, (session.current_user[2],))
        user = c.fetchone()
        conn.close()
        if not user:
            return

        (nombre, email, telefono, foto, matricula,
         experiencia, descripcion, rol, cuenta_bancaria) = user

        self.ids.nombre.text   = nombre   or ""
        self.ids.telefono.text = telefono or ""
        self.ids.foto.text     = foto     or ""

        # Avatar
        self.ids.img_avatar.source = get_avatar_source(foto)

        if rol == "abogado":
            self.ids.lbl_rol_badge.text  = "ABOGADO / A"
            self.ids.lbl_rol_badge.color = (1, 1, 1, 1)
            # Mostrar seccion abogado
            self.ids.seccion_abogado.opacity  = 1
            self.ids.seccion_abogado.disabled = False

            # ✅ FIX (único cambio)
            self.ids.seccion_abogado.height = self.ids.seccion_abogado.minimum_height

            self.ids.matricula.text         = matricula         or ""
            self.ids.experiencia.text       = experiencia       or ""
            self.ids.descripcion.text       = descripcion       or ""
            self.ids.cuenta_bancaria.text   = cuenta_bancaria   or ""
            self._cargar_resenas(email)
        else:
            self.ids.lbl_rol_badge.text  = "CLIENTE"
            self.ids.lbl_rol_badge.color = (0.60, 0.85, 1.00, 1)
            # Ocultar seccion abogado completamente
            self.ids.seccion_abogado.opacity  = 0
            self.ids.seccion_abogado.disabled = True
            self.ids.seccion_abogado.height   = 0

    # -- FOTO --------------------------------------------------------

    def elegir_foto(self):
        try:
            from plyer import filechooser
            filechooser.open_file(
                on_selection=self._foto_seleccionada,
                filters=["*.png", "*.jpg", "*.jpeg", "*.webp"],
            )
        except Exception:
            self._fallback_tkinter()

    def _fallback_tkinter(self):
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk(); root.withdraw()
            path = filedialog.askopenfilename(
                title="Elegir foto",
                filetypes=[("Imagenes", "*.png *.jpg *.jpeg *.webp"),
                           ("Todos", "*.*")],
            )
            root.destroy()
            if path:
                self._foto_seleccionada([path])
        except Exception as e:
            print("foto error:", e)

    def _foto_seleccionada(self, selection):
        if not selection:
            return
        try:
            dest = _copiar_foto(selection[0])
            self.ids.foto.text         = dest
            self.ids.img_avatar.source = dest
            print("FOTO:", dest)
        except Exception as e:
            print("ERROR foto:", e)

    # -- RESENAS -----------------------------------------------------

    def _cargar_resenas(self, email_abogado):
        box = self.ids.resenas_box
        box.clear_widgets()

        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT puntaje, comentario, cliente_email, fecha
            FROM resenas WHERE abogado_email=?
            ORDER BY id DESC LIMIT 20
        """, (email_abogado,))
        resenas = c.fetchall()
        c.execute(
            "SELECT AVG(puntaje), COUNT(*) FROM resenas WHERE abogado_email=?",
            (email_abogado,)
        )
        avg = c.fetchone()
        conn.close()

        promedio = avg[0] or 0
        total    = avg[1] or 0
        stars    = "*" * round(promedio) + "o" * (5 - round(promedio))
        self.ids.lbl_promedio.text  = f"{promedio:.1f}/5  {stars}  ({total} resenas)"

        if not resenas:
            box.add_widget(Label(
                text="Sin resenas aun",
                color=(0.55, 0.58, 0.65, 1),
                size_hint_y=None, height=36,
            ))
            return

        for puntaje, comentario, cliente, fecha in resenas:
            card = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=72 if comentario else 48,
                padding=[14, 8], spacing=2,
            )
            with card.canvas.before:
                Color(rgba=(0.97, 0.98, 1.0, 1))
                card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[10])
            card.bind(
                pos=lambda w, v: setattr(w._bg, "pos", v),
                size=lambda w, v: setattr(w._bg, "size", v),
            )
            st = "*" * puntaje + "o" * (5 - puntaje)
            card.add_widget(Label(
                text=f"{st}  {fecha or ''}",
                font_size=13, bold=True,
                color=(0.80, 0.55, 0.05, 1),
                halign="left", text_size=(None, None),
            ))
            if comentario:
                card.add_widget(Label(
                    text=f'"{comentario}"', font_size=12,
                    color=(0.35, 0.40, 0.52, 1),
                    halign="left", text_size=(None, None),
                ))
            box.add_widget(card)

    # -- GUARDAR -----------------------------------------------------

    def guardar(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            UPDATE users SET
                username=?, telefono=?, foto=?,
                matricula=?, experiencia=?, descripcion=?,
                cuenta_bancaria=?
            WHERE email=?
        """, (
            self.ids.nombre.text,
            self.ids.telefono.text,
            self.ids.foto.text,
            self.ids.matricula.text       if not self.ids.seccion_abogado.disabled else "",
            self.ids.experiencia.text     if not self.ids.seccion_abogado.disabled else "",
            self.ids.descripcion.text     if not self.ids.seccion_abogado.disabled else "",
            self.ids.cuenta_bancaria.text if not self.ids.seccion_abogado.disabled else "",
            session.current_user[2],
        ))
        conn.commit()
        conn.close()
        print("PERFIL GUARDADO")
        self.volver()

    def volver(self):
        user = session.current_user
        if user and user[4] == "abogado":
            self.manager.current = "abogado_panel"
        else:
            self.manager.current = "dashboard"
