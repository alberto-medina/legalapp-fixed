import os
import time
import shutil

from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp

from database import get_connection, tiene_resena
import session

try:
    from plyer import filechooser
    PLYER_OK = True
except Exception:
    PLYER_OK = False

UPLOAD_DIR = "assets/uploads"

# responsive
BUBBLE_W_DESKTOP = 420
BUBBLE_W_MOBILE = 260


# =====================================================
# BUBBLE
# =====================================================

def _make_bubble(texto, es_mio, ancho_max):

    cor_fondo = (
        (0.30, 0.23, 0.67, 1)
        if es_mio else
        (1, 1, 1, 1)
    )

    cor_texto = (
        (1, 1, 1, 1)
        if es_mio else
        (0.10, 0.12, 0.18, 1)
    )

    wrapper = BoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        padding=[dp(8), dp(4)],
        spacing=dp(6),
    )

    if es_mio:
        wrapper.add_widget(BoxLayout())

    bubble = BoxLayout(
        orientation="vertical",
        size_hint=(None, None),
        width=ancho_max,
        padding=[dp(14), dp(10)],
    )

    with bubble.canvas.before:

        Color(rgba=cor_fondo)

        bubble.bg = RoundedRectangle(
            pos=bubble.pos,
            size=bubble.size,
            radius=[dp(18)],
        )

    bubble.bind(
        pos=lambda w, v: setattr(w.bg, "pos", v),
        size=lambda w, v: setattr(w.bg, "size", v),
    )

    texto_lbl = Label(
        text=texto,
        font_size="15sp",
        color=cor_texto,
        halign="left",
        valign="top",
        size_hint_y=None,
    )

    texto_lbl.bind(
        width=lambda s, *_: setattr(
            s,
            "text_size",
            (s.width, None)
        )
    )

    def ajustar(*args):

        texto_lbl.texture_update()

        altura = max(dp(34), texto_lbl.texture_size[1])

        texto_lbl.height = altura

        bubble.height = altura + dp(24)

        wrapper.height = bubble.height + dp(8)

    texto_lbl.bind(
        texture_size=ajustar,
        width=ajustar,
    )

    texto_lbl.width = ancho_max - dp(28)

    bubble.add_widget(texto_lbl)

    wrapper.add_widget(bubble)

    if not es_mio:
        wrapper.add_widget(BoxLayout())

    Clock.schedule_once(lambda dt: ajustar(), 0)

    return wrapper


# =====================================================
# CHAT
# =====================================================

class ChatScreen(Screen):

    auto_refresh_event = None
    video_event = None

    ultimo_total_mensajes = -1

    # =====================================================
    # ENTER
    # =====================================================

    def on_enter(self):

        self._setup_ui()

        self.cargar_mensajes(scroll_final=True)

        # evita loops
        if not self.auto_refresh_event:

            self.auto_refresh_event = Clock.schedule_interval(
                self.auto_refresh,
                2
            )

        if not self.video_event:

            self.video_event = Clock.schedule_interval(
                self.check_videollamada,
                2
            )

    # =====================================================
    # LEAVE
    # =====================================================

    def on_leave(self):

        if self.auto_refresh_event:

            self.auto_refresh_event.cancel()

            self.auto_refresh_event = None

        if self.video_event:

            self.video_event.cancel()

            self.video_event = None

    # =====================================================
    # AUTO REFRESH
    # =====================================================

    def auto_refresh(self, dt):

        if not session.current_consulta_id:
            return

        conn = get_connection()

        c = conn.cursor()

        c.execute("""
            SELECT COUNT(*)
            FROM mensajes
            WHERE consulta_id=?
        """, (session.current_consulta_id,))

        total = c.fetchone()[0]

        conn.close()

        # SOLO refresca si cambió algo
        if total != self.ultimo_total_mensajes:

            self.cargar_mensajes()

    # =====================================================
    # CHECK VIDEO
    # =====================================================

    def check_videollamada(self, dt):

        if not session.current_consulta_id:
            return

        conn = get_connection()

        c = conn.cursor()

        c.execute("""
            SELECT estado
            FROM consultas
            WHERE id=?
        """, (session.current_consulta_id,))

        row = c.fetchone()

        conn.close()

        if not row:
            return

        estado = row[0]

        mostrar = estado == "videollamada"

        self.ids.btn_unirse_video.opacity = 1 if mostrar else 0

        self.ids.btn_unirse_video.disabled = not mostrar

    # =====================================================
    # VIDEO
    # =====================================================

    def ir_video(self):

        conn = get_connection()

        c = conn.cursor()

        c.execute("""
            SELECT estado
            FROM consultas
            WHERE id=?
        """, (session.current_consulta_id,))

        row = c.fetchone()

        conn.close()

        if not row:
            return

        if row[0] != "videollamada":
            return

        self.manager.current = "videollamada"

    # =====================================================
    # ESTADO CONSULTA
    # =====================================================

    def _get_estado_consulta(self):

        conn = get_connection()

        c = conn.cursor()

        c.execute("""
            SELECT estado, abogado, user_email, tipo_servicio
            FROM consultas
            WHERE id=?
        """, (session.current_consulta_id,))

        row = c.fetchone()

        conn.close()

        return row

    # =====================================================
    # UI
    # =====================================================

    def _setup_ui(self):

        row = self._get_estado_consulta()

        if not row:
            return

        estado, abogado, cliente, tipo = row

        es_abogado = (
            session.current_user and
            session.current_user[4] == "abogado"
        )

        finalizado = estado == "finalizado"

        interlocutor = cliente if es_abogado else abogado

        # evita superposición
        nombre_corto = (
            interlocutor[:18] + "..."
            if len(interlocutor) > 18
            else interlocutor
        )

        self.ids.lbl_chat_titulo.text = nombre_corto

        self.ids.lbl_chat_tipo.text = f"Consulta {tipo}"

        # =========================
        # ESTADO
        # =========================

        if es_abogado:

            self.ids.lbl_estado_linea.text = "Cliente conectado"

            self.ids.lbl_estado_linea.color = (
                0.90, 0.70, 0.10, 1
            )

        else:

            conn = get_connection()

            c = conn.cursor()

            c.execute("""
                SELECT estado_abogado
                FROM users
                WHERE email=?
            """, (abogado,))

            row_estado = c.fetchone()

            conn.close()

            estado_abogado = (
                row_estado[0]
                if row_estado else
                "disponible"
            )

            if estado_abogado == "disponible":

                self.ids.lbl_estado_linea.text = "En línea"

                self.ids.lbl_estado_linea.color = (
                    0.18, 0.80, 0.44, 1
                )

            elif estado_abogado == "guardia":

                self.ids.lbl_estado_linea.text = "En guardia"

                self.ids.lbl_estado_linea.color = (
                    0.95, 0.65, 0.10, 1
                )

            else:

                self.ids.lbl_estado_linea.text = "Ocupado"

                self.ids.lbl_estado_linea.color = (
                    0.90, 0.25, 0.25, 1
                )

        # =========================
        # BOTONES
        # =========================

        mostrar_video = estado == "videollamada"

        self.ids.btn_unirse_video.opacity = (
            1 if mostrar_video else 0
        )

        self.ids.btn_unirse_video.disabled = (
            not mostrar_video
        )

        if es_abogado and not finalizado:

            self.ids.btn_finalizar.opacity = 1
            self.ids.btn_finalizar.disabled = False

            if tipo == "video":

                self.ids.btn_invitar_video.opacity = 1
                self.ids.btn_invitar_video.disabled = False

            else:

                self.ids.btn_invitar_video.opacity = 0
                self.ids.btn_invitar_video.disabled = True

        else:

            self.ids.btn_finalizar.opacity = 0
            self.ids.btn_finalizar.disabled = True

            self.ids.btn_invitar_video.opacity = 0
            self.ids.btn_invitar_video.disabled = True

        # =========================
        # FINALIZADO
        # =========================

        if finalizado:

            self.ids.banner_finalizado.height = dp(38)

            self.ids.lbl_banner_fin.text = (
                "Esta consulta fue finalizada"
            )

            self.ids.input_area.disabled = True

            self.ids.input_area.opacity = 0.5

            # =====================================
            # IR A RESENA CLIENTE (solo si no envió reseña)
            # =====================================

            if (
                session.current_user and
                session.current_user[4] != "abogado" and
                not tiene_resena(session.current_consulta_id)
            ):

                Clock.schedule_once(
                    lambda dt: setattr(
                        self.manager,
                        "current",
                        "resena"
                    ),
                    1
                )

        else:

            self.ids.banner_finalizado.height = 0

            self.ids.lbl_banner_fin.text = ""

            self.ids.input_area.disabled = False

            self.ids.input_area.opacity = 1
    # =====================================================
    # MENSAJES
    # =====================================================

    def cargar_mensajes(self, scroll_final=False):

        self.ids.chat_box.clear_widgets()

        conn = get_connection()

        c = conn.cursor()

        c.execute("""
            SELECT emisor, mensaje, archivo
            FROM mensajes
            WHERE consulta_id=?
            ORDER BY id ASC
        """, (session.current_consulta_id,))

        mensajes = c.fetchall()

        conn.close()

        self.ultimo_total_mensajes = len(mensajes)

        mi_email = (
            session.current_user[2]
            if session.current_user else ""
        )

        # responsive
        ancho_ventana = self.width

        if ancho_ventana > 700:
            bubble_w = BUBBLE_W_DESKTOP
        else:
            bubble_w = BUBBLE_W_MOBILE

        for emisor, texto, archivo in mensajes:

            if emisor == "SISTEMA":

                lbl = Label(
                    text=texto,
                    font_size="11sp",
                    italic=True,
                    color=(0.45, 0.50, 0.58, 1),
                    size_hint_y=None,
                    height=dp(30),
                    halign="center",
                    valign="middle",
                )

                lbl.bind(
                    size=lambda s, *_:
                    setattr(s, "text_size", s.size)
                )

                self.ids.chat_box.add_widget(lbl)

                continue

            es_mio = emisor == mi_email

            if texto:

                self.ids.chat_box.add_widget(
                    _make_bubble(
                        texto,
                        es_mio,
                        bubble_w
                    )
                )

            if archivo:

                btn = Button(
                    text=f"📎 {os.path.basename(archivo)}",
                    size_hint_y=None,
                    height=dp(44),
                    background_normal="",
                    background_color=(0.92, 0.93, 0.96, 1),
                    color=(0.12, 0.14, 0.22, 1),
                    font_size="12sp",
                )

                btn.bind(
                    on_release=lambda x, p=archivo:
                    self.abrir_archivo(p)
                )

                self.ids.chat_box.add_widget(btn)

        if scroll_final:

            Clock.schedule_once(
                lambda dt: self.scroll_abajo(),
                0.1
            )

    # =====================================================
    # SCROLL
    # =====================================================

    def scroll_abajo(self):

        self.ids.scroll_chat.scroll_y = 0

    # =====================================================
    # ENVIAR
    # =====================================================

    def enviar(self):

        texto = self.ids.input_mensaje.text.strip()

        if not texto:
            return

        conn = get_connection()

        c = conn.cursor()

        c.execute("""
            INSERT INTO mensajes
            (consulta_id, emisor, mensaje)
            VALUES (?, ?, ?)
        """, (
            session.current_consulta_id,
            session.current_user[2],
            texto
        ))

        conn.commit()

        conn.close()

        self.ids.input_mensaje.text = ""

        self.ids.input_mensaje.focus = True

        self.cargar_mensajes(scroll_final=True)

    # =====================================================
    # ADJUNTAR
    # =====================================================

    def adjuntar(self):

        if PLYER_OK:

            try:

                filechooser.open_file(
                    on_selection=self.seleccionar_archivo
                )

                return

            except Exception:
                pass

    # =====================================================
    # ARCHIVO
    # =====================================================

    def seleccionar_archivo(self, selection):

        if not selection:
            return

        origen = selection[0]

        os.makedirs(UPLOAD_DIR, exist_ok=True)

        nombre = (
            f"{int(time.time())}_"
            f"{os.path.basename(origen)}"
        )

        destino = os.path.join(
            UPLOAD_DIR,
            nombre
        )

        shutil.copy(origen, destino)

        conn = get_connection()

        c = conn.cursor()

        c.execute("""
            INSERT INTO mensajes
            (consulta_id, emisor, archivo)
            VALUES (?, ?, ?)
        """, (
            session.current_consulta_id,
            session.current_user[2],
            destino
        ))

        conn.commit()

        conn.close()

        self.cargar_mensajes(scroll_final=True)

    # =====================================================
    # ABRIR ARCHIVO
    # =====================================================

    def abrir_archivo(self, path):

        if not os.path.exists(path):
            return

        try:

            os.startfile(path)

        except Exception as e:

            print("No se pudo abrir:", e)

    # =====================================================
    # FINALIZAR
    # =====================================================

    def finalizar_consulta(self):

        conn = get_connection()

        c = conn.cursor()

        c.execute("""
            UPDATE consultas
            SET estado='finalizado'
            WHERE id=?
        """, (
            session.current_consulta_id,
        ))

        c.execute("""
            INSERT INTO mensajes
            (consulta_id, emisor, mensaje)
            VALUES (?, ?, ?)
        """, (
            session.current_consulta_id,
            "SISTEMA",
            "El abogado finalizó esta consulta."
        ))

        conn.commit()

        conn.close()

        self._setup_ui()

        self.cargar_mensajes(
            scroll_final=True
        )

        # =====================================
        # IR A RESENA SOLO CLIENTE (solo si no envió reseña)
        # =====================================

        if (
                session.current_user and
                session.current_user[4] != "abogado" and
                not tiene_resena(session.current_consulta_id)
        ):
            Clock.schedule_once(
                lambda dt: setattr(
                    self.manager,
                    "current",
                    "resena"
                ),
                0.5
            )

    # =====================================================
    # VIDEO
    # =====================================================

    def invitar_videollamada(self):

        conn = get_connection()

        c = conn.cursor()

        c.execute("""
            UPDATE consultas
            SET estado='videollamada'
            WHERE id=?
        """, (session.current_consulta_id,))

        c.execute("""
            INSERT INTO mensajes
            (consulta_id, emisor, mensaje)
            VALUES (?, ?, ?)
        """, (
            session.current_consulta_id,
            "SISTEMA",
            "El abogado inició una videollamada."
        ))

        conn.commit()

        conn.close()

        self.manager.current = "videollamada"

    # =====================================================
    # VOLVER
    # =====================================================

    def volver(self):

        if (
            session.current_user and
            session.current_user[4] == "abogado"
        ):

            self.manager.current = "abogado_panel"

        else:

            self.manager.current = "historial"