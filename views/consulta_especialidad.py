from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
import session


ESPECIALIDADES = [

    {
        "nombre": "Derecho Civil",
        "area": "Civil",
        "descripcion": "Contratos, daños, deudas, alquileres e inmuebles.",
        "keywords": [
            "civil", "contrato", "deuda", "inmueble",
            "alquiler", "propiedad", "daños", "perjuicios"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho Penal",
        "area": "Penal",
        "descripcion": "Denuncias, robos, estafas y defensa penal.",
        "keywords": [
            "penal", "robo", "estafa", "denuncia",
            "causa", "defensa", "violencia"
        ],
        "icono": "assets/penal.png"
    },

    {
        "nombre": "Derecho Laboral",
        "area": "Laboral",
        "descripcion": "Despidos, ART, trabajo en negro y sueldos.",
        "keywords": [
            "laboral", "despido", "trabajo",
            "art", "empleo", "indemnizacion", "sueldo"
        ],
        "icono": "assets/laboral.png"
    },

    {
        "nombre": "Derecho de Familia",
        "area": "Familia",
        "descripcion": "Divorcios, hijos, alimentos y tenencia.",
        "keywords": [
            "familia", "divorcio", "hijos",
            "cuota", "tenencia", "visitas", "herencia"
        ],
        "icono": "assets/familia.png"
    },

    {
        "nombre": "Derecho Comercial",
        "area": "Comercial",
        "descripcion": "Negocios, contratos comerciales y comercios.",
        "keywords": [
            "comercial", "negocio", "empresa",
            "comercio", "marca"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho Empresarial",
        "area": "Empresarial",
        "descripcion": "Empresas, inversiones y estructura societaria.",
        "keywords": [
            "empresa", "empresarial",
            "sociedad", "inversion"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho Administrativo",
        "area": "Administrativo",
        "descripcion": "Problemas con organismos publicos y multas.",
        "keywords": [
            "administrativo", "estado",
            "municipalidad", "tramite", "multa"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho Tributario",
        "area": "Tributario",
        "descripcion": "AFIP, impuestos y problemas fiscales.",
        "keywords": [
            "afip", "impuestos", "tributario",
            "fiscal", "monotributo"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho Inmobiliario",
        "area": "Inmobiliario",
        "descripcion": "Compra, venta, alquileres y propiedades.",
        "keywords": [
            "inmobiliario", "casa", "alquiler",
            "departamento", "propiedad"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho Sucesorio",
        "area": "Sucesorio",
        "descripcion": "Herencias, sucesiones y bienes familiares.",
        "keywords": [
            "sucesion", "herencia",
            "bienes", "testamento"
        ],
        "icono": "assets/familia.png"
    },

    {
        "nombre": "Derecho Previsional",
        "area": "Previsional",
        "descripcion": "Jubilaciones, ANSES y pensiones.",
        "keywords": [
            "anses", "jubilacion",
            "pension", "previsional"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho del Consumidor",
        "area": "Consumidor",
        "descripcion": "Defensa al consumidor y reclamos.",
        "keywords": [
            "consumidor", "garantia",
            "compra", "producto", "reclamo"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho de Transito",
        "area": "Transito",
        "descripcion": "Choques, multas y accidentes viales.",
        "keywords": [
            "transito", "multa",
            "accidente", "choque", "auto"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho Migratorio",
        "area": "Migratorio",
        "descripcion": "Residencias, ciudadania y migraciones.",
        "keywords": [
            "migracion", "visa",
            "residencia", "ciudadania"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho Ambiental",
        "area": "Ambiental",
        "descripcion": "Contaminacion y conflictos ambientales.",
        "keywords": [
            "ambiental", "contaminacion",
            "medio ambiente"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho Informatico",
        "area": "Informatico",
        "descripcion": "Hackeos, redes sociales y delitos digitales.",
        "keywords": [
            "hackeo", "instagram", "facebook",
            "cuenta", "online", "datos"
        ],
        "icono": "assets/penal.png"
    },

    {
        "nombre": "Derecho de Danos y Perjuicios",
        "area": "Danos",
        "descripcion": "Indemnizaciones y reclamos por daños.",
        "keywords": [
            "daños", "perjuicios",
            "indemnizacion", "accidente"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho Contractual",
        "area": "Contractual",
        "descripcion": "Problemas y redaccion de contratos.",
        "keywords": [
            "contrato", "acuerdo",
            "firma", "documento"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho Societario",
        "area": "Societario",
        "descripcion": "Sociedades, socios y empresas.",
        "keywords": [
            "sociedad", "socios",
            "empresa", "acciones"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho de Seguros",
        "area": "Seguros",
        "descripcion": "Problemas con seguros y coberturas.",
        "keywords": [
            "seguro", "aseguradora",
            "cobertura", "siniestro"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho de Salud",
        "area": "Salud",
        "descripcion": "Obras sociales, mala praxis y salud.",
        "keywords": [
            "obra social", "prepaga",
            "salud", "medico", "mala praxis"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho Internacional",
        "area": "Internacional",
        "descripcion": "Conflictos y tramites internacionales.",
        "keywords": [
            "internacional", "extranjero",
            "pais", "internacional privado"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Derecho Constitucional",
        "area": "Constitucional",
        "descripcion": "Derechos constitucionales y amparos.",
        "keywords": [
            "constitucion", "amparo",
            "derechos", "constitucional"
        ],
        "icono": "assets/civil.png"
    },

    {
        "nombre": "Mediacion",
        "area": "Mediacion",
        "descripcion": "Resolucion de conflictos mediante acuerdos.",
        "keywords": [
            "mediacion", "conflicto",
            "acuerdo", "negociacion"
        ],
        "icono": "assets/mediacion.png"
    },
]


class ConsultaEspecialidadScreen(Screen):

    def on_enter(self):
        self.cargar_especialidades(ESPECIALIDADES)

    # ======================================================
    # CREAR CARDS
    # ======================================================

    def cargar_especialidades(self, lista):

        container = self.ids.lista_especialidades
        container.clear_widgets()

        for item in lista:

            card = Builder.load_string(f'''
EspecialidadCard:
    on_release: app.root.get_screen("especialidad").seleccionar("{item["area"]}")

    AsyncImage:
        source: "{item["icono"]}"
        size_hint_x: None
        width: "68dp"

    BoxLayout:
        orientation: "vertical"
        spacing: "4dp"

        Label:
            text: "{item["nombre"]}"
            bold: True
            font_size: "16sp"
            color: 0.08, 0.12, 0.28, 1
            halign: "left"
            valign: "middle"
            text_size: self.size

        Label:
            text: "{item["descripcion"]}"
            font_size: "13sp"
            color: 0.45, 0.50, 0.60, 1
            halign: "left"
            valign: "middle"
            text_size: self.size
''')

            container.add_widget(card)

    # ======================================================
    # BUSCADOR
    # ======================================================

    def filtrar_especialidades(self, texto):

        texto = texto.lower().strip()

        if not texto:
            self.cargar_especialidades(ESPECIALIDADES)
            return

        resultados = []

        for item in ESPECIALIDADES:

            contenido = (
                item["nombre"] + " " +
                item["descripcion"] + " " +
                " ".join(item["keywords"])
            ).lower()

            if texto in contenido:
                resultados.append(item)

        self.cargar_especialidades(resultados)

    # ======================================================
    # FILTROS
    # ======================================================

    def aplicar_filtro(self, categoria):

        if categoria == "Todas":
            self.cargar_especialidades(ESPECIALIDADES)
            return

        filtradas = [
            x for x in ESPECIALIDADES
            if x["area"] == categoria
        ]

        self.cargar_especialidades(filtradas)

    # ======================================================
    # NAVEGACION
    # ======================================================

    def seleccionar(self, area):
        session.area_legal = area
        self.manager.current = "abogados"

    def volver(self):
        self.manager.current = "dashboard"