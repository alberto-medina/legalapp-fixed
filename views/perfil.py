import os
import shutil

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle

import firebase_config as fb
import session
from views.utils_avatar import get_avatar_source

FOTO_DIR = "assets/fotos"


def _copiar_foto(origen):
    os.makedirs(FOTO_DIR, exist_ok=True)
    ext = os.path.splitext(origen)[1].lower()
    safe = session.get_email().replace("@", "_").replace(".", "_") if session.get_email() else "user"
    dest = os.path.join(FOTO_DIR, f"perfil_{safe}{ext}")
    shutil.copy2(origen, dest)
    return dest


class PerfilScreen(Screen):

    def on_enter(self):
        if not session.current_user:
            return

        uid = session.get_uid()
        user_data = fb.obtener_usuario(uid)

        if not user_data:
            return

        nombre = user_data.get('username', '') or user_data.get('nombre', '')
        email = user_data.get('email', '')
        telefono = user_data.get('telefono', '')
        foto = user_data.get('foto_url', '')
        matricula = user_data.get('matricula', '')
        experiencia = user_data.get('experiencia', '')
        descripcion = user_data.get('descripcion', '')
        rol = user_data.get('rol', 'cliente')
        cuenta_bancaria = user_data.get('cuenta_bancaria', '')

        self.ids.nombre.text = nombre or ""
        self.ids.telefono.text = telefono or ""
        self.ids.foto.text = foto or ""
        self.ids.img_avatar.source = get_avatar_source(foto)

        if rol == "abogado":
            self.ids.lbl_rol_badge.text = "ABOGADO / A"
            self.ids.lbl_rol_badge.color = (1, 1, 1, 1)
            self.ids.seccion_abogado.opacity = 1
            self.ids.seccion_abogado.disabled = False
            Clock.schedule_once(lambda dt: self._recalc_seccion(), 0.05)

            self.ids.matricula.text = matricula or ""
            self.ids.experiencia.text = experiencia or ""
            self.ids.descripcion.text = descripcion or ""
            self.ids.cuenta_bancaria.text = cuenta_bancaria or ""

            self._cargar_resenas(email)
        else:
            self.ids.lbl_rol_badge.text = "CLIENTE"
            self.ids.lbl_rol_badge.color = (0.60, 0.85, 1.00, 1)
            self.ids.seccion_abogado.opacity = 0
            self.ids.seccion_abogado.disabled = True
            self.ids.seccion_abogado.height = 0

    def _recalc_seccion(self):
        sec = self.ids.seccion_abogado
        sec.height = sec.minimum_height

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
            root = tk.Tk()
            root.withdraw()
            path = filedialog.askopenfilename(
                title="Elegir foto",
                filetypes=[("Imagenes", "*.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")],
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
            self.ids.foto.text = dest
            self.ids.img_avatar.source = dest

            uid = session.get_uid()
            if uid:
                ok, url = fb.subir_foto_perfil(uid, dest)
                if ok:
                    self.ids.foto.text = url
        except Exception as e:
            print("ERROR foto:", e)

    def _cargar_resenas(self, email_abogado):
        box = self.ids.resenas_box
        box.clear_widgets()

        resenas = fb.obtener_resenas_abogado(email_abogado)
        total = len(resenas)
        promedio = sum(r.get('puntaje', 0) for r in resenas) / total if total > 0 else 0

        stars = "*" * round(promedio) + "o" * (5 - round(promedio))
        self.ids.lbl_promedio.text = f"{promedio:.1f}/5  {stars}  ({total} resenas)"

        if not resenas:
            box.add_widget(Label(
                text="Sin resenas aun",
                color=(0.55, 0.58, 0.65, 1),
                size_hint_y=None,
                height=dp(36),
                font_size="14sp",
            ))
            return

        for rdata in resenas:
            puntaje = rdata.get('puntaje', 0)
            comentario = rdata.get('comentario', '')
            fecha = rdata.get('fecha', '')

            card = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(82) if comentario else dp(56),
                padding=[dp(14), dp(8)],
                spacing=dp(2),
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
                font_size="13sp",
                bold=True,
                color=(0.80, 0.55, 0.05, 1),
                halign="left",
                valign="middle",
                text_size=(None, None),
            ))

            if comentario:
                card.add_widget(Label(
                    text=f'"{comentario}"',
                    font_size="12sp",
                    color=(0.35, 0.40, 0.52, 1),
                    halign="left",
                    valign="middle",
                    text_size=(None, None),
                ))

            box.add_widget(card)

    def guardar(self):
        uid = session.get_uid()
        if not uid:
            return

        datos = {
            'username': self.ids.nombre.text,
            'telefono': self.ids.telefono.text,
            'foto_url': self.ids.foto.text,
        }

        if not self.ids.seccion_abogado.disabled:
            datos.update({
                'matricula': self.ids.matricula.text,
                'experiencia': self.ids.experiencia.text,
                'descripcion': self.ids.descripcion.text,
                'cuenta_bancaria': self.ids.cuenta_bancaria.text,
            })

        fb.actualizar_usuario(uid, datos)
        self.volver()

    def volver(self):
        if session.es_abogado():
            self.manager.current = "abogado_panel"
        else:
            self.manager.current = "dashboard"