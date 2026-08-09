from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle
import session

# =============================================================
# DICCIONARIO COMPLETO DE PROVINCIAS Y LOCALIDADES DE ARGENTINA
# Usado por UbicacionScreen (cliente) y register_abogado (abogado)
# =============================================================
PROVINCIAS_CIUDADES = {
    "Buenos Aires": [
        "La Plata", "Mar del Plata", "Quilmes", "Lanus", "Tigre", "San Isidro",
        "Moron", "Lomas de Zamora", "Almirante Brown", "Merlo", "General San Martin",
        "Tres de Febrero", "Florencio Varela", "Berazategui", "Esteban Echeverria",
        "La Matanza", "Avellaneda", "Vicente Lopez", "San Fernando", "Pilar",
        "Escobar", "Campana", "Zarate", "San Nicolas de los Arroyos", "Junin",
        "Bahia Blanca", "Tandil", "Olavarria", "Azul", "Necochea",
        "Pergamino", "San Pedro", "Lujan", "Mercedes", "Chivilcoy",
        "Lobos", "Chascomus", "Dolores", "Las Flores", "Pehuajo",
        "Trenque Lauquen", "9 de Julio", "Bragado", "General Pico", "Lincoln",
        "Otras",
    ],
    "CABA": [
        "Balvanera", "Belgrano", "Boedo", "Caballito", "Chacarita",
        "Coghlan", "Colegiales", "Constitucion", "Flores", "Floresta",
        "La Boca", "Liniers", "Mataderos", "Monte Castro", "Montserrat",
        "Nueva Pompeya", "Nunez", "Palermo", "Parque Avellaneda", "Parque Chacabuco",
        "Parque Chas", "Parque Patricios", "Paternal", "Puerto Madero", "Recoleta",
        "Retiro", "Saavedra", "San Cristobal", "San Nicolas", "San Telmo",
        "Velez Sarsfield", "Versalles", "Villa Crespo", "Villa del Parque",
        "Villa Devoto", "Villa General Mitre", "Villa Lugano", "Villa Luro",
        "Villa Ortuzar", "Villa Pueyrredon", "Villa Real", "Villa Riachuelo",
        "Villa Santa Rita", "Villa Soldati", "Villa Urquiza", "Otras",
    ],
    "Cordoba": [
        "Cordoba Capital", "Villa Carlos Paz", "Rio Cuarto", "San Francisco",
        "Villa Maria", "Rio Tercero", "Cosquin", "La Falda", "Alta Gracia",
        "Jesus Maria", "Arroyito", "Bell Ville", "Marcos Juarez", "Villa Dolores",
        "Cruz del Eje", "Dean Funes", "Laboulaye", "Rio Ceballos", "Unquillo",
        "Capilla del Monte", "Mina Clavero", "Huerta Grande", "Otras",
    ],
    "Santa Fe": [
        "Rosario", "Santa Fe Capital", "Rafaela", "Venado Tuerto", "Reconquista",
        "Santo Tome", "Casilda", "Esperanza", "Ceres", "Vera",
        "San Lorenzo", "Villa Constitucion", "Fray Luis Beltran", "Firmat",
        "Sunchales", "Las Rosas", "Rufino", "Tostado", "Otras",
    ],
    "Mendoza": [
        "Mendoza Capital", "San Rafael", "Godoy Cruz", "Guaymallen", "Las Heras",
        "Lujan de Cuyo", "Maipu", "General Alvear", "Rivadavia", "Junin",
        "La Paz", "San Carlos", "Tunuyan", "Tupungato", "Malargue",
        "San Martin", "Otras",
    ],
    "Tucuman": [
        "San Miguel de Tucuman", "Tafi Viejo", "Yerba Buena", "Concepcion",
        "Monteros", "Aguilares", "Famailla", "Lules", "Banda del Rio Sali",
        "Alderetes", "Las Talitas", "Tafi del Valle", "Otras",
    ],
    "Salta": [
        "Salta Capital", "Tartagal", "Oran", "San Ramon de la Nueva Oran",
        "Joaquin V. Gonzalez", "Embarcacion", "Rosario de la Frontera",
        "Cafayate", "Cachi", "Molinos", "General Guemes", "Rivadavia",
        "Aguaray", "Professor Salvador Mazza", "Otras",
    ],
    "Entre Rios": [
        "Parana", "Concordia", "Gualeguaychu", "Colon", "Villaguay",
        "Gualeguay", "Victoria", "La Paz", "Federacion", "Concepcion del Uruguay",
        "Diamante", "Chajarí", "Otras",
    ],
    "Misiones": [
        "Posadas", "Oberá", "Eldorado", "Puerto Iguazu", "Apostoles",
        "San Vicente", "Leandro N. Alem", "Jardin America", "Montecarlo",
        "Wanda", "Puerto Rico", "Capitan Manueco", "Otras",
    ],
    "Chaco": [
        "Resistencia", "Presidencia Roque Saenz Pena", "Villa Angela",
        "Charata", "General Pinedo", "Las Breñas", "Fontana",
        "Barranqueras", "Puerto Tirol", "Otras",
    ],
    "Corrientes": [
        "Corrientes Capital", "Goya", "Paso de los Libres", "Curuzú Cuatiá",
        "Mercedes", "Esquina", "Bella Vista", "Monte Caseros", "Ituzaingo",
        "Santo Tome", "Otras",
    ],
    "Jujuy": [
        "San Salvador de Jujuy", "Palpalá", "San Pedro de Jujuy",
        "Libertador General San Martin", "La Quiaca", "Humahuaca",
        "Tilcara", "Abra Pampa", "El Carmen", "Otras",
    ],
    "Rio Negro": [
        "Bariloche", "Viedma", "General Roca", "Cipolletti", "Allen",
        "Centenario", "Cinco Saltos", "Villa Regina", "Catriel",
        "El Bolson", "Ingeniero Jacobacci", "Las Grutas", "Otras",
    ],
    "Neuquen": [
        "Neuquen Capital", "Plottier", "Cipolletti", "Cutral Co",
        "Plaza Huincul", "Zapala", "San Martin de los Andes",
        "Villa La Angostura", "Junin de los Andes", "Otras",
    ],
    "Formosa": [
        "Formosa Capital", "Clorinda", "Pirané", "El Colorado",
        "General Mosconi", "Ingeniero Juarez", "Otras",
    ],
    "Chubut": [
        "Rawson", "Comodoro Rivadavia", "Trelew", "Puerto Madryn",
        "Esquel", "Rada Tilly", "Sarmiento", "Rio Mayo", "Otras",
    ],
    "San Juan": [
        "San Juan Capital", "Rivadavia", "Chimbas", "Santa Lucia",
        "Pocito", "Rawson", "Caucete", "Villa Krause", "Otras",
    ],
    "San Luis": [
        "San Luis Capital", "Villa Mercedes", "Merlo", "Justo Daract",
        "Arizona", "Quines", "Otras",
    ],
    "Catamarca": [
        "Catamarca Capital", "San Fernando del Valle de Catamarca",
        "Andalgala", "Belen", "Santa Maria", "Tinogasta", "Otras",
    ],
    "La Rioja": [
        "La Rioja Capital", "Chilecito", "Chamical", "Aimogasta",
        "Vinchina", "Otras",
    ],
    "Santiago del Estero": [
        "Santiago del Estero Capital", "La Banda", "Termas de Rio Hondo",
        "Frías", "Loreto", "Añatuya", "Otras",
    ],
    "La Pampa": [
        "Santa Rosa", "General Pico", "Toay", "Realico", "Victorica",
        "General Acha", "Otras",
    ],
    "Santa Cruz": [
        "Rio Gallegos", "Caleta Olivia", "El Calafate", "Puerto Deseado",
        "Pico Truncado", "Las Heras", "Puerto Madryn", "Otras",
    ],
    "Tierra del Fuego": [
        "Ushuaia", "Rio Grande", "Tolhuin", "Otras",
    ],
}


# =============================================================
# SELECTOR GENERICO - popup con buscador y lista scrolleable
# Usado por UbicacionScreen y register_abogado
# =============================================================
def abrir_selector(titulo, opciones, callback):
    """Muestra un popup con buscador y lista de opciones.
    Al tocar una opcion llama a callback(opcion)."""

    contenido = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(10))

    # Buscador
    buscador = TextInput(
        hint_text='Buscar...',
        multiline=False,
        size_hint_y=None,
        height=dp(44),
        background_normal='',
        background_active='',
        background_color=(0.95, 0.94, 0.97, 1),
        foreground_color=(0.10, 0.06, 0.14, 1),
        hint_text_color=(0.60, 0.57, 0.68, 1),
        cursor_color=(0.30, 0.23, 0.67, 1),
        padding=[dp(12), dp(10)],
        font_size='15sp',
    )

    scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
    grid = GridLayout(cols=1, spacing=dp(4), size_hint_y=None)
    grid.bind(minimum_height=grid.setter('height'))
    scroll.add_widget(grid)

    popup = Popup(
        title=titulo,
        content=contenido,
        size_hint=(0.92, 0.82),
        separator_color=(0.30, 0.23, 0.67, 1),
        title_color=(0.10, 0.06, 0.14, 1),
        title_size='16sp',
    )

    def _build_lista(filtro=''):
        grid.clear_widgets()
        filtro_lower = filtro.strip().lower()
        for op in opciones:
            if filtro_lower and filtro_lower not in op.lower():
                continue
            btn = Button(
                text=op,
                size_hint_y=None,
                height=dp(46),
                font_size='14sp',
                background_normal='',
                background_color=(1, 1, 1, 1),
                color=(0.10, 0.06, 0.14, 1),
                halign='left',
                text_size=(None, None),
            )
            with btn.canvas.before:
                Color(rgba=(0.93, 0.92, 0.97, 1))
                btn._bg = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(8)])
            btn.bind(
                pos=lambda w, v: setattr(w._bg, 'pos', v),
                size=lambda w, v: setattr(w._bg, 'size', v),
            )

            def _on_select(instance, opcion=op):
                popup.dismiss()
                callback(opcion)

            btn.bind(on_release=_on_select)
            grid.add_widget(btn)

    buscador.bind(text=lambda inst, val: _build_lista(val))

    contenido.add_widget(buscador)
    contenido.add_widget(scroll)

    _build_lista()
    popup.open()


# =============================================================
# SCREEN DE UBICACION PARA EL CLIENTE
# =============================================================
class UbicacionScreen(Screen):

    _provincia_seleccionada = None
    _ciudad_seleccionada = None

    def on_enter(self):
        self._provincia_seleccionada = None
        self._ciudad_seleccionada = None
        self._actualizar_ui()

    def _actualizar_ui(self):
        prov = self._provincia_seleccionada or 'Elegí la provincia'
        ciudad = self._ciudad_seleccionada or 'Elegí la ciudad'
        self.ids.btn_provincia.text = prov
        self.ids.btn_ciudad.text = ciudad
        self.ids.btn_ciudad.disabled = self._provincia_seleccionada is None
        self.ids.btn_ciudad.opacity = 1.0 if self._provincia_seleccionada else 0.45
        puede_buscar = self._provincia_seleccionada and self._ciudad_seleccionada
        self.ids.btn_buscar.disabled = not puede_buscar
        self.ids.btn_buscar.opacity = 1.0 if puede_buscar else 0.45

    def abrir_provincias(self):
        provincias = list(PROVINCIAS_CIUDADES.keys())
        abrir_selector('Elegí tu provincia', provincias, self._on_provincia)

    def _on_provincia(self, provincia):
        self._provincia_seleccionada = provincia
        self._ciudad_seleccionada = None
        self._actualizar_ui()

    def abrir_ciudades(self):
        if not self._provincia_seleccionada:
            return
        ciudades = PROVINCIAS_CIUDADES.get(self._provincia_seleccionada, [])
        abrir_selector(
            f'Ciudad en {self._provincia_seleccionada}',
            ciudades,
            self._on_ciudad,
        )

    def _on_ciudad(self, ciudad):
        self._ciudad_seleccionada = ciudad
        self._actualizar_ui()

    def buscar(self):
        if not self._provincia_seleccionada or not self._ciudad_seleccionada:
            return
        session.provincia_busqueda = self._provincia_seleccionada
        if self._ciudad_seleccionada == 'Otras':
            session.ciudad_busqueda = None
        else:
            session.ciudad_busqueda = self._ciudad_seleccionada
        self.manager.current = 'especialidad'

    def buscar_todas(self):
        session.provincia_busqueda = None
        session.ciudad_busqueda = None
        self.manager.current = 'especialidad'

    def volver(self):
        self.manager.current = 'dashboard'
