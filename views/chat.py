import os
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle
from kivy.clock import Clock
from database import get_connection
import session
import time, shutil

try:
    from plyer import filechooser
    PLYER_OK = True
except Exception:
    PLYER_OK = False

UPLOAD_DIR = "assets/uploads"
BUBBLE_W   = 230   # ancho maximo de burbuja en pixeles


def _make_bubble(texto, es_mio):
    """
    Crea wrapper + bubble con altura correcta calculada despues
    de que texture_size este disponible via bind.
    """
    # Label con text_size fijo para que Kivy calcule el wrapping
    label = Label(
        text=texto,
        font_size=14,
        color=(1, 1, 1, 1) if es_mio else (0.10, 0.14, 0.28, 1),
        halign="right" if es_mio else "left",
        valign="middle",
        text_size=(BUBBLE_W - 24, None),
        size_hint=(None, None),
        width=BUBBLE_W - 24,
    )

    bubble = BoxLayout(
        size_hint=(None, None),
        width=BUBBLE_W,
        padding=[12, 8],
    )

    bg = (0.13, 0.77, 0.37, 1) if es_mio else (1, 1, 1, 1)
    with bubble.canvas.before:
        Color(rgba=bg)
        bubble._bg = RoundedRectangle(
            pos=bubble.pos, size=bubble.size, radius=[14]
        )
    bubble.bind(
        pos=lambda w, v: setattr(w._bg, "pos", v),
        size=lambda w, v: setattr(w._bg, "size", v),
    )
    bubble.add_widget(label)

    # wrapper alinea la burbuja a la derecha o izquierda
    wrapper = BoxLayout(
        size_hint_y=None,
        height=60,   # altura provisional, se ajusta en el bind de abajo
    )
    if es_mio:
        wrapper.add_widget(BoxLayout())   # spacer izquierdo
    wrapper.add_widget(bubble)
    if not es_mio:
        wrapper.add_widget(BoxLayout())   # spacer derecho

    # FIX: ajustar altura DESPUES de que texture_size este calculado
    def _on_texture(lbl, tex_size):
        h = tex_size[1] + 24          # padding vertical
        lbl.height   = tex_size[1]
        bubble.height  = h
        wrapper.height = h + 8        # margen entre burbujas

    label.bind(texture_size=_on_texture)
    # Forzar recalculo si el texto ya esta renderizado
    label.texture_update()

    return wrapper


class ChatScreen(Screen):

    def on_enter(self):
        self._setup_ui()
        self.cargar_mensajes()

    def _get_estado_consulta(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "SELECT estado, abogado, user_email, tipo_servicio "
            "FROM consultas WHERE id=?",
            (session.current_consulta_id,)
        )
        row = c.fetchone()
        conn.close()
        return row

    def _setup_ui(self):
        row = self._get_estado_consulta()
        if not row:
            return
        estado, abogado, cliente, tipo = row
        es_abogado = session.current_user and session.current_user[4] == "abogado"
        finalizado = (estado == "finalizado")

        if es_abogado:
            interlocutor = cliente
            estado_linea = "Cliente"
            color_linea  = (0.85, 0.62, 0.05, 1)
        else:
            interlocutor = abogado
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT estado_abogado FROM users WHERE email=?", (abogado,))
            ab_row = c.fetchone()
            conn.close()
            ab_est = ab_row[0] if ab_row and ab_row[0] else "disponible"
            if ab_est == "disponible":
                estado_linea = "En linea"
                color_linea  = (0.10, 0.72, 0.38, 1)
            elif ab_est == "guardia":
                estado_linea = "En guardia"
                color_linea  = (0.85, 0.62, 0.05, 1)
            else:
                estado_linea = "Ocupado"
                color_linea  = (0.80, 0.22, 0.22, 1)

        self.ids.lbl_chat_titulo.text   = interlocutor
        self.ids.lbl_chat_tipo.text     = f"Consulta {tipo or ''}"
        self.ids.lbl_estado_linea.text  = estado_linea
        self.ids.lbl_estado_linea.color = color_linea

        if es_abogado and not finalizado:
            self.ids.btn_finalizar.opacity  = 1
            self.ids.btn_finalizar.disabled = False
        else:
            self.ids.btn_finalizar.opacity  = 0
            self.ids.btn_finalizar.disabled = True

        if finalizado:
            self.ids.banner_finalizado.height  = 36
            self.ids.lbl_banner_fin.text       = "Esta consulta fue finalizada"
            self.ids.input_area.opacity        = 0.4
            self.ids.input_area.disabled       = True
        else:
            self.ids.banner_finalizado.height  = 0
            self.ids.lbl_banner_fin.text       = ""
            self.ids.input_area.opacity        = 1
            self.ids.input_area.disabled       = False

    def cargar_mensajes(self):
        self.ids.chat_box.clear_widgets()
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "SELECT emisor, mensaje, archivo FROM mensajes WHERE consulta_id=?",
            (session.current_consulta_id,)
        )
        mensajes = c.fetchall()
        conn.close()

        mi_email = session.current_user[2] if session.current_user else ""

        for emisor, texto, archivo in mensajes:

            # Mensaje de sistema
            if emisor == "SISTEMA":
                self.ids.chat_box.add_widget(Label(
                    text=texto,
                    font_size=11, italic=True,
                    color=(0.50, 0.55, 0.65, 1),
                    size_hint_y=None, height=30,
                    halign="center",
                    text_size=(300, None),
                ))
                continue

            es_mio = (emisor == mi_email)

            if texto:
                wrapper = _make_bubble(texto, es_mio)
                self.ids.chat_box.add_widget(wrapper)

            if archivo:
                btn = Button(
                    text=f"Adjunto: {os.path.basename(archivo)}",
                    size_hint_y=None, height=44,
                    background_normal="",
                    background_color=(0.92, 0.93, 0.95, 1),
                    color=(0.10, 0.14, 0.28, 1),
                    font_size=12,
                )
                btn.bind(on_release=lambda x, p=archivo: self.abrir_archivo(p))
                self.ids.chat_box.add_widget(btn)

        Clock.schedule_once(lambda dt: self.scroll_abajo(), 0.15)

    def scroll_abajo(self):
        self.ids.scroll_chat.scroll_y = 0

    def enviar(self):
        texto = self.ids.input_mensaje.text.strip()
        if not texto:
            return
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO mensajes (consulta_id, emisor, mensaje) VALUES (?,?,?)",
            (session.current_consulta_id, session.current_user[2], texto)
        )
        conn.commit()
        conn.close()
        self.ids.input_mensaje.text = ""
        self.cargar_mensajes()

    def adjuntar(self):
        if PLYER_OK:
            try:
                filechooser.open_file(on_selection=self.seleccionar_archivo)
                return
            except Exception:
                pass
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk(); root.withdraw()
            path = filedialog.askopenfilename()
            root.destroy()
            if path:
                self.seleccionar_archivo([path])
        except Exception as e:
            print("adjuntar error:", e)

    def seleccionar_archivo(self, selection):
        if not selection:
            return
        origen = selection[0]
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        nombre  = f"{int(time.time())}_{os.path.basename(origen)}"
        destino = os.path.join(UPLOAD_DIR, nombre)
        shutil.copy(origen, destino)
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO mensajes (consulta_id, emisor, archivo) VALUES (?,?,?)",
            (session.current_consulta_id, session.current_user[2], destino)
        )
        conn.commit()
        conn.close()
        self.cargar_mensajes()

    def abrir_archivo(self, path):
        print("Abrir:", path)

    def finalizar_consulta(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "UPDATE consultas SET estado='finalizado' WHERE id=?",
            (session.current_consulta_id,)
        )
        c.execute(
            "INSERT INTO mensajes (consulta_id, emisor, mensaje) VALUES (?,?,?)",
            (session.current_consulta_id, "SISTEMA",
             "El abogado finalizo esta consulta.")
        )
        conn.commit()
        conn.close()
        self._setup_ui()
        self.cargar_mensajes()

    def volver(self):
        if session.current_user and session.current_user[4] == "abogado":
            self.manager.current = "abogado_panel"
        else:
            row = self._get_estado_consulta()
            if row and row[0] == "finalizado":
                conn = get_connection()
                c = conn.cursor()
                c.execute(
                    "SELECT id FROM resenas WHERE consulta_id=?",
                    (session.current_consulta_id,)
                )
                tiene = c.fetchone()
                conn.close()
                if not tiene:
                    self.manager.current = "resena"
                    return
            self.manager.current = "historial"
