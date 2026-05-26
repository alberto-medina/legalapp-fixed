from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
import session

PROVINCIAS_CIUDADES = {
    "Buenos Aires": ["La Plata", "Mar del Plata", "Quilmes", "Lanus", "Tigre", "San Isidro", "Morón", "Otras"],
    "CABA": ["CABA"],
    "Cordoba": ["Cordoba Capital", "Villa Carlos Paz", "Rio Cuarto", "Otras"],
    "Santa Fe": ["Rosario", "Santa Fe Capital", "Rafaela", "Otras"],
    "Mendoza": ["Mendoza Capital", "San Rafael", "Godoy Cruz", "Otras"],
    "Tucuman": ["San Miguel de Tucuman", "Otras"],
    "Salta": ["Salta Capital", "Otras"],
    "Entre Rios": ["Parana", "Concordia", "Otras"],
    "Misiones": ["Posadas", "Otras"],
    "Chaco": ["Resistencia", "Otras"],
    "Corrientes": ["Corrientes Capital", "Otras"],
    "Santiago del Estero": ["Santiago del Estero Capital", "Otras"],
    "San Juan": ["San Juan Capital", "Otras"],
    "Jujuy": ["San Salvador de Jujuy", "Otras"],
    "Rio Negro": ["Bariloche", "Viedma", "Otras"],
    "Neuquen": ["Neuquen Capital", "Otras"],
    "Formosa": ["Formosa Capital", "Otras"],
    "Chubut": ["Rawson", "Comodoro Rivadavia", "Otras"],
    "San Luis": ["San Luis Capital", "Otras"],
    "Catamarca": ["Catamarca Capital", "Otras"],
    "La Rioja": ["La Rioja Capital", "Otras"],
    "La Pampa": ["Santa Rosa", "Otras"],
    "Santa Cruz": ["Rio Gallegos", "Otras"],
    "Tierra del Fuego": ["Ushuaia", "Otras"],
}


class UbicacionScreen(Screen):

    _provincia_seleccionada = None
    _ciudad_seleccionada = None

    def on_enter(self):
        self._provincia_seleccionada = None
        self._ciudad_seleccionada = None
        self.ids.lbl_ciudad_titulo.opacity = 0
        self.ids.grid_ciudades.opacity = 0
        self.ids.btn_buscar.disabled = True
        self.ids.btn_buscar.opacity = 0.45
        self._cargar_provincias()

    def _cargar_provincias(self):
        self.ids.grid_provincias.clear_widgets()
        for provincia in PROVINCIAS_CIUDADES.keys():
            btn = Button(
                text=provincia,
                size_hint_y=None,
                height="44dp",
                font_size="14sp",
                bold=False,
                background_normal="",
                background_color=(1, 1, 1, 1),
                color=(0.10, 0.12, 0.18, 1),
            )
            btn.bind(on_release=lambda x, p=provincia: self._seleccionar_provincia(p))
            self.ids.grid_provincias.add_widget(btn)

    def _seleccionar_provincia(self, provincia):
        self._provincia_seleccionada = provincia
        self._ciudad_seleccionada = None
        self.ids.btn_buscar.disabled = True
        self.ids.btn_buscar.opacity = 0.45

        # Resetear colores provincias
        for btn in self.ids.grid_provincias.children:
            btn.background_color = (1, 1, 1, 1)
            btn.color = (0.10, 0.12, 0.18, 1)
            if btn.text == provincia:
                btn.background_color = (0.23, 0.18, 0.55, 1)
                btn.color = (1, 1, 1, 1)

        # Cargar ciudades
        self._cargar_ciudades(provincia)

    def _cargar_ciudades(self, provincia):
        ciudades = PROVINCIAS_CIUDADES.get(provincia, [])
        self.ids.grid_ciudades.clear_widgets()

        for ciudad in ciudades:
            btn = Button(
                text=ciudad,
                size_hint_y=None,
                height="44dp",
                font_size="14sp",
                background_normal="",
                background_color=(1, 1, 1, 1),
                color=(0.10, 0.12, 0.18, 1),
            )
            btn.bind(on_release=lambda x, c=ciudad: self._seleccionar_ciudad(c))
            self.ids.grid_ciudades.add_widget(btn)

        self.ids.lbl_ciudad_titulo.opacity = 1
        self.ids.grid_ciudades.opacity = 1

    def _seleccionar_ciudad(self, ciudad):
        self._ciudad_seleccionada = ciudad

        # Resetear colores ciudades
        for btn in self.ids.grid_ciudades.children:
            btn.background_color = (1, 1, 1, 1)
            btn.color = (0.10, 0.12, 0.18, 1)
            if btn.text == ciudad:
                btn.background_color = (0.23, 0.18, 0.55, 1)
                btn.color = (1, 1, 1, 1)

        self.ids.btn_buscar.disabled = False
        self.ids.btn_buscar.opacity = 1.0

    def buscar(self):
        if not self._provincia_seleccionada or not self._ciudad_seleccionada:
            return
        session.provincia_busqueda = self._provincia_seleccionada
        session.ciudad_busqueda = self._ciudad_seleccionada
        self.manager.current = "especialidad"

    def buscar_todas(self):
        session.provincia_busqueda = None
        session.ciudad_busqueda = None
        self.manager.current = "especialidad"

    def volver(self):
        self.manager.current = "dashboard"