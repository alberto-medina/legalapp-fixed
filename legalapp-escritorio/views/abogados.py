import threading
import json
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.resources import resource_find
from kivy.animation import Animation
import supabase_config as fb
import session
from views.utils_avatar import get_avatar_source

RATING_FONT = resource_find("data/fonts/DejaVuSans.ttf") or "data/fonts/DejaVuSans.ttf"


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

def _rating_text(puntaje):
    try:
        valor = max(0, min(5, int(round(float(puntaje or 0)))))
    except Exception:
        valor = 0
    return "★" * valor + "☆" * (5 - valor)


def _fecha_resena(fecha):
    texto = str(fecha or "")
    if "T" in texto:
        return texto.split("T", 1)[0]
    return texto[:10]


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
        from kivy.clock import Clock as _Clock

        self.mostrar_skeleton()

        def _fetch():
            provincia = getattr(session, 'provincia_busqueda', None)
            ciudad = getattr(session, 'ciudad_busqueda', None)

            # Normalizar provincia y ciudad a Title Case para matchear
            # independientemente de como el abogado haya completado el campo
            if provincia:
                provincia = provincia.strip().title()
            if ciudad and ciudad != "Otras":
                ciudad = ciudad.strip().title()
            elif ciudad == "Otras":
                ciudad = None

            abogados = fb.listar_abogados(
                disponibles=False,
                provincia=provincia,
                ciudad=ciudad
            )

            area = (session.area_legal or "").strip().lower()

            if area:
                filtrados = []
                for data in abogados:
                    especialidad = str(data.get('especialidad') or "").strip().lower()
                    especialidades_raw = data.get('especialidades') or []
                    try:
                        especialidades_lista = (
                            json.loads(especialidades_raw)
                            if isinstance(especialidades_raw, str)
                            else especialidades_raw
                        )
                    except Exception:
                        especialidades_lista = []

                    especialidades_lista = [
                        str(esp or "").strip().lower()
                        for esp in (especialidades_lista or [])
                    ]

                    coincide_principal = area in especialidad
                    coincide_lista = any(area in esp for esp in especialidades_lista)

                    if coincide_principal or coincide_lista:
                        filtrados.append(data)
                self._todos = filtrados
            else:
                self._todos = abogados

            _Clock.schedule_once(lambda dt: self.filtrar(), 0)

        threading.Thread(target=_fetch, daemon=True).start()

    def mostrar_skeleton(self, cantidad=3):
        """Placeholders animados mientras se espera la respuesta de Supabase,
        en vez de dejar la lista vacia."""
        self.ids.lista.clear_widgets()
        for _ in range(cantidad):
            self.ids.lista.add_widget(self._crear_skeleton_card())

    def _crear_skeleton_card(self):
        card = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(92),
            padding=[dp(16), dp(14)],
            spacing=dp(14),
        )

        with card.canvas.before:
            Color(rgba=(0, 0, 0, 0.07))
            card._shadow = RoundedRectangle(pos=(card.x, card.y - dp(3)), size=card.size, radius=[dp(20)])
            Color(rgba=(1, 1, 1, 1))
            card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(20)])

        card.bind(
            pos=lambda w, v: (setattr(w._shadow, "pos", (v[0], v[1] - dp(3))), setattr(w._bg, "pos", v)),
            size=lambda w, v: (setattr(w._shadow, "size", v), setattr(w._bg, "size", v)),
        )

        placeholders = []

        avatar_ph = BoxLayout(size_hint=(None, None), size=(dp(64), dp(64)))
        with avatar_ph.canvas.before:
            Color(rgba=(0.89, 0.87, 0.95, 1))
            avatar_ph._bg = RoundedRectangle(pos=avatar_ph.pos, size=avatar_ph.size, radius=[dp(32)])
        avatar_ph.bind(
            pos=lambda w, v: setattr(w._bg, "pos", v),
            size=lambda w, v: setattr(w._bg, "size", v),
        )
        card.add_widget(avatar_ph)
        placeholders.append(avatar_ph)

        lineas = BoxLayout(orientation="vertical", spacing=dp(10), padding=[0, dp(6)])
        for ancho in (0.65, 0.40, 0.30):
            linea = BoxLayout(size_hint=(ancho, None), height=dp(12))
            with linea.canvas.before:
                Color(rgba=(0.89, 0.87, 0.95, 1))
                linea._bg = RoundedRectangle(pos=linea.pos, size=linea.size, radius=[dp(6)])
            linea.bind(
                pos=lambda w, v: setattr(w._bg, "pos", v),
                size=lambda w, v: setattr(w._bg, "size", v),
            )
            fila = BoxLayout(size_hint_y=None, height=dp(12))
            fila.add_widget(linea)
            fila.add_widget(BoxLayout(size_hint_x=1 - ancho))
            lineas.add_widget(fila)
            placeholders.append(linea)

        card.add_widget(lineas)

        for widget in placeholders:
            pulso = Animation(opacity=0.4, duration=0.7) + Animation(opacity=1, duration=0.7)
            pulso.repeat = True
            pulso.start(widget)

        return card

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
            if data.get("aprobado") is False:
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

            matricula = data.get('matricula', '')
            self.add_card(
                nombre,
                email,
                estado,
                foto,
                experiencia,
                descripcion,
                especialidad,
                provincia,
                ciudad,
                matricula,
            )

    def add_card(self, nombre, email, estado, foto, experiencia, descripcion, especialidad, provincia="", ciudad="", matricula=""):
        from kivy.metrics import dp as _dp
        resenas = fb.obtener_resenas_abogado(email)
        cantidad = len(resenas)
        promedio = sum(r.get('puntaje', 0) for r in resenas) / cantidad if cantidad > 0 else 0

        # Card con altura dinamica - se expande segun contenido
        card = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            padding=[_dp(16), _dp(14)],
            spacing=_dp(10),
        )
        card.height = card.minimum_height

        with card.canvas.before:
            Color(rgba=(0, 0, 0, 0.07))
            card.shadow = RoundedRectangle(pos=(card.x, card.y - _dp(3)), size=card.size, radius=[_dp(20)])
            Color(rgba=(1, 1, 1, 1))
            card.bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[_dp(20)])

        card.bind(
            pos=lambda w, v: (setattr(w.shadow, "pos", (v[0], v[1] - _dp(3))), setattr(w.bg, "pos", v)),
            size=lambda w, v: (setattr(w.shadow, "size", v), setattr(w.bg, "size", v), setattr(w, "height", w.minimum_height)),
            minimum_height=lambda w, v: setattr(w, "height", v),
        )

        # ----- FILA SUPERIOR: avatar + info + boton -----
        top = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            spacing=_dp(14),
        )
        top.bind(minimum_height=lambda w, v: setattr(w, "height", max(v, _dp(92))))

        avatar = AsyncImage(
            source=get_avatar_source(foto, email),
            size_hint=(None, None),
            size=(_dp(72), _dp(72)),
        )
        top.add_widget(avatar)

        info = BoxLayout(
            orientation="vertical",
            spacing=_dp(3),
            size_hint_y=None,
        )
        info.bind(minimum_height=lambda w, v: setattr(w, "height", v))

        lbl_nombre = Label(
            text=nombre,
            font_size="16sp",
            bold=True,
            color=(0.10, 0.06, 0.14, 1),
            size_hint_y=None,
            height=_dp(22),
            halign="left",
            valign="top",
        )

        def _ajustar_nombre(lbl, *args):
            lbl.text_size = (lbl.width, None)
            lbl.texture_update()
            lbl.height = max(_dp(22), lbl.texture_size[1])

        lbl_nombre.bind(width=_ajustar_nombre, texture_size=_ajustar_nombre)
        info.add_widget(lbl_nombre)

        if especialidad:
            lbl_esp = Label(
                text=especialidad,
                font_size="13sp",
                bold=True,
                color=(0.30, 0.23, 0.67, 1),
                size_hint_y=None,
                height=_dp(20),
                halign="left",
                valign="middle",
            )
            lbl_esp.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
            info.add_widget(lbl_esp)

        if provincia or ciudad:
            ubicacion_txt = f"{ciudad}, {provincia}" if ciudad and provincia else provincia or ciudad
            lbl_ubic = Label(
                text=ubicacion_txt,
                font_size="11sp",
                color=(0.45, 0.50, 0.60, 1),
                size_hint_y=None,
                height=_dp(18),
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
            height=_dp(20),
            halign="left",
            valign="middle",
        )
        lbl_estado.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
        info.add_widget(lbl_estado)

        rating = f"{_rating_text(promedio)} {promedio:.1f}/5" if cantidad else "Sin resenas"
        lbl_rating = Label(
            text=rating,
            font_size="12sp",
            color=(0.90, 0.62, 0.10, 1),
            font_name=RATING_FONT,
            size_hint_y=None,
            height=_dp(20),
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
                height=_dp(18),
                halign="left",
                valign="middle",
            )
            lbl_exp.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
            info.add_widget(lbl_exp)

        top.add_widget(info)

        acciones = BoxLayout(
            orientation="vertical",
            size_hint=(None, None),
            width=_dp(94),
            spacing=_dp(6),
        )
        acciones.bind(minimum_height=lambda w, v: setattr(w, "height", max(v, _dp(96))))

        btn_ver = Button(
            text="Ver perfil",
            size_hint=(None, None),
            size=(_dp(88), _dp(36)),
            font_size="11sp",
            bold=True,
            background_normal="",
            background_color=(0.90, 0.89, 0.97, 1),
            color=(0.30, 0.23, 0.67, 1),
        )
        btn_ver.bind(
            on_release=lambda x, n=nombre, e=email, est=estado, f=foto, exp=experiencia, desc=descripcion, esp=especialidad, prov=provincia, ciu=ciudad, mat=matricula:
            self.ver_perfil_abogado(n, e, est, f, exp, desc, esp, prov, ciu, mat)
        )
        btn = Button(
            text="Elegir",
            size_hint=(None, None),
            size=(_dp(80), _dp(44)),
            bold=True,
            font_size="14sp",
            background_normal="",
            background_color=(0.30, 0.23, 0.67, 1),
            color=(1, 1, 1, 1),
        )
        btn.bind(on_release=lambda x, e=email, est=estado: self.seleccionar(e, est))
        acciones.add_widget(btn_ver)
        acciones.add_widget(btn)
        top.add_widget(acciones)

        card.add_widget(top)

        # ----- DESCRIPCION con altura dinamica -----
        if descripcion:
            desc = descripcion.strip()
            if len(desc) > 200:
                desc = desc[:200] + "..."

            lbl_desc = Label(
                text=desc,
                font_size="12sp",
                color=(0.45, 0.50, 0.60, 1),
                halign="left",
                valign="top",
                size_hint_y=None,
            )

            def _ajustar_desc(lbl, *args):
                lbl.text_size = (lbl.width, None)
                lbl.texture_update()
                lbl.height = max(_dp(18), lbl.texture_size[1] + _dp(4))

            lbl_desc.bind(width=_ajustar_desc, texture_size=_ajustar_desc)
            lbl_desc.height = _dp(36)
            card.add_widget(lbl_desc)

        self.ids.lista.add_widget(card)

    def ver_perfil_abogado(self, nombre, email, estado, foto, experiencia, descripcion, especialidad, provincia="", ciudad="", matricula=""):
        perfil = fb.obtener_usuario_por_email(email) or {}
        nombre = perfil.get('username', '') or perfil.get('nombre', '') or nombre
        estado = perfil.get('estado_abogado', estado) or estado
        foto = perfil.get('foto_url', foto) or foto
        experiencia = perfil.get('experiencia', experiencia) or experiencia
        descripcion = perfil.get('descripcion', descripcion) or descripcion
        especialidad = perfil.get('especialidad', especialidad) or especialidad
        provincia = perfil.get('provincia', provincia) or provincia
        ciudad = perfil.get('ciudad', ciudad) or ciudad
        matricula = perfil.get('matricula', matricula) or matricula

        resenas = fb.obtener_resenas_abogado(email) or []
        cantidad = len(resenas)
        promedio = sum(r.get('puntaje', 0) for r in resenas) / cantidad if cantidad > 0 else 0

        layout = BoxLayout(orientation="vertical", padding=[dp(14), dp(12)], spacing=dp(10))
        with layout.canvas.before:
            Color(1, 1, 1, 1)
            layout.bg = RoundedRectangle(pos=layout.pos, size=layout.size, radius=[dp(18)])
        layout.bind(
            pos=lambda w, v: setattr(w.bg, "pos", v),
            size=lambda w, v: setattr(w.bg, "size", v),
        )

        scroll = ScrollView(do_scroll_x=False)
        content = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))

        avatar = AsyncImage(
            source=get_avatar_source(foto, email),
            size_hint=(None, None),
            size=(dp(96), dp(96)),
            pos_hint={"center_x": 0.5},
        )
        content.add_widget(avatar)

        def _lbl(texto, size="14sp", color=(0.10, 0.12, 0.18, 1), bold=False, h=None, font_name=None):
            lbl = Label(
                text=texto,
                font_size=size,
                bold=bold,
                color=color,
                halign="left",
                valign="middle",
                size_hint_y=None,
                height=h or dp(24),
            )
            if font_name:
                lbl.font_name = font_name
            lbl.bind(size=lambda s, *_: setattr(s, "text_size", (s.width, None)))
            return lbl

        nombre_lbl = _lbl(nombre, size="20sp", color=(0.10, 0.06, 0.14, 1), bold=True, h=dp(34))
        nombre_lbl.halign = "center"
        nombre_lbl.valign = "middle"
        nombre_lbl.bind(
            size=lambda s, *_: setattr(s, "text_size", (s.width, None)),
            texture_size=lambda s, v: setattr(s, "height", max(dp(34), v[1] + dp(4))),
        )
        content.add_widget(nombre_lbl)

        if especialidad:
            esp = _lbl(especialidad, size="15sp", color=(0.30, 0.23, 0.67, 1), bold=True, h=dp(26))
            esp.halign = "center"
            esp.bind(size=lambda s, *_: setattr(s, "text_size", (s.width, None)))
            content.add_widget(esp)

        ubicacion = f"{ciudad}, {provincia}" if ciudad and provincia else provincia or ciudad
        if ubicacion:
            ubic = _lbl(ubicacion, size="12sp", color=(0.45, 0.50, 0.60, 1), h=dp(22))
            ubic.halign = "center"
            ubic.bind(size=lambda s, *_: setattr(s, "text_size", (s.width, None)))
            content.add_widget(ubic)

        if matricula:
            mat = _lbl(f"Matrícula: {matricula}", size="12sp", color=(0.28, 0.32, 0.42, 1), bold=True, h=dp(22))
            mat.halign = "center"
            mat.bind(size=lambda s, *_: setattr(s, "text_size", (s.width, None)))
            content.add_widget(mat)

        content.add_widget(_lbl(
            ESTADO_LABEL.get(estado, estado),
            size="13sp",
            color=ESTADO_COLOR.get(estado, (0.5, 0.5, 0.5, 1)),
            bold=True,
            h=dp(22)
        ))
        content.add_widget(_lbl(
            f"{_rating_text(promedio)}\n{promedio:.1f}/5 ({cantidad} reseñas)" if cantidad else "Sin reseñas",
            size="13sp",
            color=(0.90, 0.62, 0.10, 1),
            bold=True,
            h=dp(24),
            font_name=RATING_FONT if cantidad else None
        ))

        if experiencia:
            content.add_widget(_lbl(f"Años de experiencia: {experiencia}", size="13sp", color=(0.28, 0.32, 0.42, 1), h=dp(24)))

        if descripcion:
            content.add_widget(_lbl("Bio", size="14sp", color=(0.30, 0.23, 0.67, 1), bold=True, h=dp(24)))
            bio = _lbl(descripcion.strip(), size="13sp", color=(0.22, 0.24, 0.30, 1), h=dp(90))
            bio.valign = "top"
            bio.bind(texture_size=lambda s, v: setattr(s, "height", max(dp(54), v[1] + dp(8))))
            content.add_widget(bio)

        if resenas:
            content.add_widget(_lbl("Opiniones recientes", size="14sp", color=(0.30, 0.23, 0.67, 1), bold=True, h=dp(24)))
            for rdata in resenas[:5]:
                puntaje = int(rdata.get("puntaje", 0) or 0)
                comentario = str(rdata.get("comentario", "") or "").strip()
                fecha = str(rdata.get("fecha", "") or "")[:10]
                texto = f"{_rating_text(puntaje)}  {_fecha_resena(fecha)}"
                if comentario:
                    texto += f"\n{comentario}"
                card = _lbl(texto, size="12sp", color=(0.10, 0.12, 0.18, 1), h=dp(54 if comentario else 28), font_name=RATING_FONT)
                card.valign = "top" if comentario else "middle"
                card.bind(texture_size=lambda s, v: setattr(s, "height", max(dp(28), v[1] + dp(8))))
                content.add_widget(card)

        scroll.add_widget(content)
        layout.add_widget(scroll)

        botones = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        btn_cerrar = Button(
            text="Cerrar",
            background_normal="",
            background_color=(0.90, 0.89, 0.97, 1),
            color=(0.30, 0.23, 0.67, 1),
            bold=True,
        )
        btn_elegir = Button(
            text="Elegir abogado",
            background_normal="",
            background_color=(0.30, 0.23, 0.67, 1),
            color=(1, 1, 1, 1),
            bold=True,
        )
        botones.add_widget(btn_cerrar)
        botones.add_widget(btn_elegir)
        layout.add_widget(botones)

        from kivy.uix.popup import Popup
        popup = Popup(
            title="Perfil del abogado",
            content=layout,
            size_hint=(0.92, 0.86),
            separator_color=(0.30, 0.68, 0.95, 1),
            background_color=(1, 1, 1, 1),
        )
        btn_cerrar.bind(on_release=popup.dismiss)
        btn_elegir.bind(on_release=lambda *_: (popup.dismiss(), self.seleccionar(email, estado)))
        popup.open()


    def seleccionar(self, email, estado):
        session.abogado_seleccionado = email
        abogado = fb.obtener_usuario_por_email(email) or {}
        session.estado_abogado = (
            abogado.get("estado_abogado")
            or estado
            or "disponible"
        )
        session.guardar()
        self.manager.current = "tipo"

    def volver(self):
        self.manager.current = "especialidad"
