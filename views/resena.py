from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button

from database import get_connection
import session

from datetime import datetime


class ResenaScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._puntaje_sel = 5

    # ==================================================
    # ENTER
    # ==================================================

    def on_enter(self):

        self._puntaje_sel = 5

        self._render_estrellas()

        self.ids.input_comentario.text = ""

        conn = get_connection()

        c = conn.cursor()

        c.execute("""
            SELECT abogado
            FROM consultas
            WHERE id=?
        """, (session.current_consulta_id,))

        row = c.fetchone()

        conn.close()

        abogado = row[0] if row else ""

        nombre_corto = abogado.split("@")[0] if abogado else ""

        self.ids.lbl_abogado_resena.text = (
            f"Abogado: {nombre_corto}"
        )

    # ==================================================
    # ESTRELLAS
    # ==================================================

    def _render_estrellas(self):

        box = self.ids.estrellas_box

        box.clear_widgets()

        for i in range(1, 6):

            seleccionado = i <= self._puntaje_sel

            btn = Button(

                text=str(i),

                bold=True,

                font_size="22sp",

                background_normal="",

                background_down="",

                background_color=(
                    (0.99, 0.84, 0.00, 1)
                    if seleccionado else
                    (0.15, 0.17, 0.30, 1)
                ),

                color=(
                    (0.00, 0.02, 0.12, 1)
                    if seleccionado else
                    (0.80, 0.82, 0.90, 1)
                ),
            )

            btn.bind(
                on_release=lambda x, v=i:
                self._set_puntaje(v)
            )

            box.add_widget(btn)

    # ==================================================
    # SET PUNTAJE
    # ==================================================

    def _set_puntaje(self, val):

        self._puntaje_sel = val

        self._render_estrellas()

    # ==================================================
    # ENVIAR
    # ==================================================

    def enviar_resena(self):

        conn = get_connection()

        c = conn.cursor()

        c.execute("""
            SELECT abogado, user_email
            FROM consultas
            WHERE id=?
        """, (session.current_consulta_id,))

        row = c.fetchone()

        if not row:

            conn.close()

            self.manager.current = "historial"

            return

        abogado_email, cliente_email = row

        comentario = (
            self.ids.input_comentario.text.strip()
        )

        fecha = datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )

        try:

            c.execute("""
                INSERT OR REPLACE INTO resenas
                (
                    consulta_id,
                    abogado_email,
                    cliente_email,
                    puntaje,
                    comentario,
                    fecha
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session.current_consulta_id,
                abogado_email,
                cliente_email,
                self._puntaje_sel,
                comentario,
                fecha
            ))

            conn.commit()

            print(
                "RESENA GUARDADA:",
                self._puntaje_sel,
                comentario
            )

        except Exception as e:

            print("ERROR RESENA:", e)

        finally:

            conn.close()

        self.manager.current = "historial"

    # ==================================================
    # OMITIR
    # ==================================================

    def omitir(self):

        self.manager.current = "historial"
