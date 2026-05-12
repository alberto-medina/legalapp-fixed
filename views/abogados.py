from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle

from database import get_connection

import session

from views.utils_avatar import get_avatar_source


ESTADO_COLOR = {
    "disponible": (0.18, 0.80, 0.44, 1),
    "guardia":    (0.95, 0.65, 0.10, 1),
    "ocupado":    (0.90, 0.25, 0.25, 1),
}

ESTADO_LABEL = {
    "disponible": "Disponible",
    "guardia":    "Urgente",
    "ocupado":    "Ocupado",
}


class AbogadosScreen(Screen):

    _todos = []

    # =====================================================
    # ENTER
    # =====================================================

    def on_enter(self):

        self.ids.lbl_area.text = (
            f"Especialidad: {session.area_legal or ''}"
        )

        self.ids.buscador.text = ""

        if "filtro_estado" in self.ids:
            self.ids.filtro_estado.text = "Todos"

        if "filtro_orden" in self.ids:
            self.ids.filtro_orden.text = "Mejor valorados"

        self.cargar_abogados()

    # =====================================================
    # CARGAR
    # =====================================================

    def cargar_abogados(self):

        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            SELECT
                username,
                email,
                estado_abogado,
                foto,
                matricula,
                experiencia,
                descripcion,
                especialidad
            FROM users
            WHERE rol='abogado'
        """)

        abogados = c.fetchall()

        conn.close()

        area = (session.area_legal or "").strip().lower()

        if area:

            filtrados = []

            for row in abogados:

                especialidad = (row[7] or "").lower()
                descripcion  = (row[6] or "").lower()

                if area in especialidad or area in descripcion:
                    filtrados.append(row)

            self._todos = filtrados if filtrados else abogados

        else:
            self._todos = abogados

        self.filtrar()

    # =====================================================
    # FILTRO
    # =====================================================

    def filtrar(self, *args):

        texto = self.ids.buscador.text.strip().lower()

        estado = "Todos"
        orden  = "Mejor valorados"

        if "filtro_estado" in self.ids:
            estado = self.ids.filtro_estado.text

        if "filtro_orden" in self.ids:
            orden = self.ids.filtro_orden.text

        filtrados = []

        for row in self._todos:

            (
                nombre,
                email,
                estado_abogado,
                foto,
                matricula,
                experiencia,
                descripcion,
                especialidad
            ) = row

            contenido = (
                f"{nombre or ''} "
                f"{descripcion or ''} "
                f"{experiencia or ''} "
                f"{especialidad or ''}"
            ).lower()

            # =============================================
            # BUSQUEDA
            # =============================================

            if texto and texto not in contenido:
                continue

            # =============================================
            # FILTRO ESTADO
            # =============================================

            if estado != "Todos":

                if (estado_abogado or "").lower() != estado.lower():
                    continue

            filtrados.append(row)

        # =============================================
        # ORDEN
        # =============================================

        if orden == "Nombre A-Z":

            filtrados.sort(
                key=lambda x: (x[0] or "").lower()
            )

        elif orden == "Mayor experiencia":

            def exp_num(v):

                try:
                    return int(
                        ''.join(filter(str.isdigit, str(v)))
                    )
                except:
                    return 0

            filtrados.sort(
                key=lambda x: exp_num(x[5]),
                reverse=True
            )

        elif orden == "Mejor valorados":

            def get_rating(email):

                conn = get_connection()
                c = conn.cursor()

                c.execute("""
                    SELECT AVG(puntaje)
                    FROM resenas
                    WHERE abogado_email=?
                """, (email,))

                row = c.fetchone()

                conn.close()

                return row[0] or 0

            filtrados.sort(
                key=lambda x: get_rating(x[1]),
                reverse=True
            )

        self.render(filtrados)

    # =====================================================
    # RENDER
    # =====================================================

    def render(self, abogados):

        self.ids.lista.clear_widgets()

        if not abogados:

            self.ids.lista.add_widget(Label(
                text="No se encontraron abogados",
                size_hint_y=None,
                height=70,
                font_size="15sp",
                color=(0.45, 0.50, 0.60, 1),
            ))

            return

        for row in abogados:

            (
                nombre,
                email,
                estado,
                foto,
                matricula,
                experiencia,
                descripcion,
                especialidad
            ) = row

            self.add_card(
                nombre or email,
                email,
                estado or "disponible",
                foto,
                experiencia,
                descripcion,
                especialidad
            )

    # =====================================================
    # CARD
    # =====================================================

    def add_card(
        self,
        nombre,
        email,
        estado,
        foto,
        experiencia,
        descripcion,
        especialidad
    ):

        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            SELECT AVG(puntaje), COUNT(*)
            FROM resenas
            WHERE abogado_email=?
        """, (email,))

        row = c.fetchone()

        conn.close()

        promedio = row[0] or 0
        cantidad = row[1] or 0

        estrellas = "★" * round(promedio)
        estrellas += "☆" * (5 - round(promedio))

        altura = 170

        if descripcion:
            altura = 220

        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=altura,
            padding=[16, 14],
            spacing=10,
        )

        with card.canvas.before:

            Color(rgba=(1, 1, 1, 1))

            card.bg = RoundedRectangle(
                pos=card.pos,
                size=card.size,
                radius=[20],
            )

        card.bind(
            pos=lambda w, v: setattr(w.bg, "pos", v),
            size=lambda w, v: setattr(w.bg, "size", v),
        )

        # =================================================
        # FILA SUPERIOR
        # =================================================

        top = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=90,
            spacing=14,
        )

        # =================================================
        # AVATAR
        # =================================================

        avatar = AsyncImage(
            source=get_avatar_source(foto),
            size_hint=(None, None),
            size=(70, 70),
        )

        top.add_widget(avatar)

        # =================================================
        # INFO
        # =================================================

        info = BoxLayout(
            orientation="vertical",
            spacing=2,
        )

        # NOMBRE

        lbl_nombre = Label(
            text=nombre,
            font_size="16sp",
            bold=True,
            color=(0.10, 0.06, 0.14, 1),
            size_hint_y=None,
            height=22,
            halign="left",
            valign="middle",
        )

        lbl_nombre.bind(
            size=lambda s, *_: setattr(s, "text_size", s.size)
        )

        info.add_widget(lbl_nombre)

        # ESPECIALIDAD

        if especialidad:

            lbl_esp = Label(
                text=especialidad,
                font_size="13sp",
                bold=True,
                color=(0.30, 0.23, 0.67, 1),
                size_hint_y=None,
                height=20,
                halign="left",
                valign="middle",
            )

            lbl_esp.bind(
                size=lambda s, *_: setattr(s, "text_size", s.size)
            )

            info.add_widget(lbl_esp)

        # ESTADO

        lbl_estado = Label(
            text=ESTADO_LABEL.get(estado, estado),
            font_size="12sp",
            bold=True,
            color=ESTADO_COLOR.get(estado, (0.5, 0.5, 0.5, 1)),
            size_hint_y=None,
            height=20,
            halign="left",
            valign="middle",
        )

        lbl_estado.bind(
            size=lambda s, *_: setattr(s, "text_size", s.size)
        )

        info.add_widget(lbl_estado)

        # RATING

        rating = (
            f"{estrellas}  {promedio:.1f} ({cantidad})"
            if cantidad
            else "Sin reseñas"
        )

        lbl_rating = Label(
            text=rating,
            font_size="12sp",
            color=(0.90, 0.62, 0.10, 1),
            size_hint_y=None,
            height=20,
            halign="left",
            valign="middle",
        )

        lbl_rating.bind(
            size=lambda s, *_: setattr(s, "text_size", s.size)
        )

        info.add_widget(lbl_rating)

        # EXPERIENCIA

        if experiencia:

            lbl_exp = Label(
                text=f"Experiencia: {experiencia}",
                font_size="11sp",
                color=(0.45, 0.48, 0.60, 1),
                size_hint_y=None,
                height=18,
                halign="left",
                valign="middle",
            )

            lbl_exp.bind(
                size=lambda s, *_: setattr(s, "text_size", s.size)
            )

            info.add_widget(lbl_exp)

        top.add_widget(info)

        # =================================================
        # BOTON
        # =================================================

        btn = Button(
            text="Elegir",
            size_hint=(None, None),
            size=(90, 52),
            bold=True,
            font_size="14sp",
            background_normal="",
            background_color=(0.30, 0.23, 0.67, 1),
            color=(1, 1, 1, 1),
        )

        btn.bind(
            on_release=lambda x, e=email, est=estado:
            self.seleccionar(e, est)
        )

        top.add_widget(btn)

        card.add_widget(top)

        # =================================================
        # DESCRIPCION
        # =================================================

        if descripcion:

            desc = descripcion.strip()

            if len(desc) > 140:
                desc = desc[:140] + "..."

            lbl_desc = Label(
                text=desc,
                font_size="12sp",
                color=(0.45, 0.50, 0.60, 1),
                halign="left",
                valign="top",
            )

            lbl_desc.bind(
                size=lambda s, *_: setattr(
                    s,
                    "text_size",
                    (s.width, None)
                )
            )

            card.add_widget(lbl_desc)

        self.ids.lista.add_widget(card)

    # =====================================================
    # SELECCIONAR
    # =====================================================

    def seleccionar(self, email, estado):

        session.abogado_seleccionado = email
        session.estado_abogado = estado

        self.manager.current = "tipo"

    # =====================================================
    # VOLVER
    # =====================================================

    def volver(self):

        self.manager.current = "especialidad"