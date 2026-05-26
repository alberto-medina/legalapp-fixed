from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
import supabase_config as fb
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

    def on_enter(self):
        provincia = getattr(session, 'provincia_busqueda', None)
        ciudad = getattr(session, 'ciudad_busqueda', None)

        if provincia and ciudad:
            self.ids.lbl_area.text = (
                f"Especialidad: {session.area_legal or ''} - "
                f"{ciudad}, {provincia}"
            )
        else:
            self.ids.lbl_area.text = f"Especialidad: {session.area_legal or ''}"

        self.ids.buscador.text = ""

        if "filtro_estado" in self.ids:
            self.ids.filtro_estado.text = "Todos"
        if "filtro_orden" in self.ids:
            self.ids.filtro_orden.text = "Mejor valorados"

        self.cargar_abogados()

    def cargar_abogados(self):
        provincia = getattr(session, 'provincia_busqueda', None)
        ciudad = getattr(session, 'ciudad_busqueda', None)

        abogados = fb.listar_abogados(
            disponibles=False,
            provincia=provincia,
            ciudad=ciudad
        )

        area = (session.area_legal or "").strip().lower()

        if area:
            filtrados = []
            for data in abogados:
                especialidad = (data.get('especialidad') or "").lower()
                descripcion = (data.get('descripcion') or "").lower()
                especialidades = (data.get('especialidades') or "").lower()
                if area in especialidad or area in descripcion or area in especialidades:
                    filtrados.append(data)
            self._todos = filtrados if filtrados else abogados
        else:
            self._todos = abogados

        self.filtrar()

    def filtrar(self, *args):
        texto = self.ids.buscador.text.strip().lower()
        estado = "Todos"
        orden = "Mejor valorados"

        if "filtro_estado" in self.ids:
            estado = self.ids.filtro_estado.text

        if "filtro_orden" in self.ids:
            orden = self.ids.filtro_orden.text

        filtrados = []

        for data in self._todos:

            # SOLO abogados aprobados
            if not data.get("aprobado", False):
                continue

            nombre = data.get('username', '') or data.get('nombre', '')
            descripcion = data.get('descripcion', '')
            experiencia = data.get('experiencia', '')
            especialidad = data.get('especialidad', '')
            estado_abogado = data.get('estado_abogado', 'disponible')

            contenido = (
                f"{nombre} "
                f"{descripcion} "
                f"{experiencia} "
                f"{especialidad}"
            ).lower()

            if texto and texto not in contenido:
                continue

            if estado != "Todos":
                if (estado_abogado or "").lower() != estado.lower():
                    continue

            filtrados.append(data)

        if orden == "Nombre A-Z":
            filtrados.sort(
                key=lambda x: (
                        x.get('username', '') or x.get('nombre', '')
                ).lower()
            )

        elif orden == "Mayor experiencia":

            def exp_num(v):
                try:
                    return int(
                        ''.join(filter(str.isdigit, str(v)))
                    )
                except Exception as e:
                    print("ERROR EXPERIENCIA:", e)
                    return 0

            filtrados.sort(
                key=lambda x: exp_num(
                    x.get('experiencia', '')
                ),
                reverse=True
            )

        elif orden == "Mejor valorados":

            def get_rating(email):
                try:
                    resenas = fb.obtener_resenas_abogado(email)

                    if not resenas:
                        return 0

                    return (
                            sum(
                                r.get('puntaje', 0)
                                for r in resenas
                            ) / len(resenas)
                    )

                except Exception as e:
                    print("ERROR RATING:", e)
                    return 0

            filtrados.sort(
                key=lambda x: get_rating(
                    x.get('email', '')
                ),
                reverse=True
            )

        self.render(filtrados)

    def render(self, abogados):
        self.ids.lista.clear_widgets()

        if not abogados:
            provincia = getattr(session, 'provincia_busqueda', None)
            ciudad = getattr(session, 'ciudad_busqueda', None)
            if provincia:
                msg = f"No se encontraron abogados en {ciudad}, {provincia}"
            else:
                msg = "No se encontraron abogados"

            self.ids.lista.add_widget(Label(
                text=msg,
                size_hint_y=None,
                height=70,
                font_size="15sp",
                color=(0.45, 0.50, 0.60, 1),
            ))
            return

        for data in abogados:
            nombre = data.get('username', '') or data.get('nombre', '')
            email = data.get('email', '')
            estado = data.get('estado_abogado', 'disponible')
            foto = data.get('foto_url', '')
            experiencia = data.get('experiencia', '')
            descripcion = data.get('descripcion', '')
            especialidad = data.get('especialidad', '')
            provincia = data.get('provincia', '')
            ciudad = data.get('ciudad', '')

            self.add_card(nombre, email, estado, foto, experiencia, descripcion, especialidad, provincia, ciudad)

    def add_card(self, nombre, email, estado, foto, experiencia, descripcion, especialidad, provincia="", ciudad=""):
        resenas = fb.obtener_resenas_abogado(email)
        cantidad = len(resenas)
        promedio = sum(r.get('puntaje', 0) for r in resenas) / cantidad if cantidad > 0 else 0

        estrellas = "★" * round(promedio) + "☆" * (5 - round(promedio))
        altura = 240 if descripcion else 190

        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=altura,
            padding=[16, 14],
            spacing=10,
        )

        with card.canvas.before:
            Color(rgba=(1, 1, 1, 1))
            card.bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[20])

        card.bind(
            pos=lambda w, v: setattr(w.bg, "pos", v),
            size=lambda w, v: setattr(w.bg, "size", v),
        )

        top = BoxLayout(orientation="horizontal", size_hint_y=None, height=90, spacing=14)

        avatar = AsyncImage(
            source=get_avatar_source(foto),
            size_hint=(None, None),
            size=(70, 70),
        )
        top.add_widget(avatar)

        info = BoxLayout(orientation="vertical", spacing=2)

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
        lbl_nombre.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
        info.add_widget(lbl_nombre)

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
            lbl_esp.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
            info.add_widget(lbl_esp)

        # Ubicacion
        if provincia or ciudad:
            ubicacion_txt = f"{ciudad}, {provincia}" if ciudad and provincia else provincia or ciudad
            lbl_ubic = Label(
                text=ubicacion_txt,
                font_size="11sp",
                color=(0.45, 0.50, 0.60, 1),
                size_hint_y=None,
                height=18,
                halign="left",
                valign="middle",
            )
            lbl_ubic.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
            info.add_widget(lbl_ubic)

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
        lbl_estado.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
        info.add_widget(lbl_estado)

        rating = f"{estrellas}  {promedio:.1f} ({cantidad})" if cantidad else "Sin resenas"
        lbl_rating = Label(
            text=rating,
            font_size="12sp",
            color=(0.90, 0.62, 0.10, 1),
            size_hint_y=None,
            height=20,
            halign="left",
            valign="middle",
        )
        lbl_rating.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
        info.add_widget(lbl_rating)

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
            lbl_exp.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
            info.add_widget(lbl_exp)

        top.add_widget(info)

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
        btn.bind(on_release=lambda x, e=email, est=estado: self.seleccionar(e, est))
        top.add_widget(btn)

        card.add_widget(top)

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
            lbl_desc.bind(size=lambda s, *_: setattr(s, "text_size", (s.width, None)))
            card.add_widget(lbl_desc)

        self.ids.lista.add_widget(card)

    def seleccionar(self, email, estado):
        session.abogado_seleccionado = email
        session.estado_abogado = estado
        self.manager.current = "tipo"

    def volver(self):
        self.manager.current = "especialidad"