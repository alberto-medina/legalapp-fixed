from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

import supabase_config as fb
import session

PRECIO_SUSCRIPCION = 55000
PRECIO_ESPECIALIDAD_EXTRA = 10000

ESPECIALIDADES = [
    "Derecho Penal",
    "Derecho Civil",
    "Derecho Laboral",
    "Derecho de Familia",
    "Derecho Comercial",
    "Derecho Administrativo",
    "Derecho Tributario",
    "Derecho Inmobiliario",
    "Derecho Societario",
    "Derecho Previsional",
]

PROVINCIAS = [
    "Buenos Aires",
    "CABA",
    "Cordoba",
    "Santa Fe",
    "Mendoza",
    "Tucuman",
    "Entre Rios",
    "Salta",
    "Misiones",
    "Chaco",
    "Corrientes",
    "Santiago del Estero",
    "San Juan",
    "Jujuy",
    "Rio Negro",
    "Neuquen",
    "Formosa",
    "Chubut",
    "San Luis",
    "Catamarca",
    "La Rioja",
    "La Pampa",
    "Santa Cruz",
    "Tierra del Fuego",
]


class RegisterAbogadoScreen(Screen):

    _registro_en_proceso = False
    _especialidades_seleccionadas = []

    def on_enter(self):
        self._especialidades_seleccionadas = []
        self._registro_en_proceso = False
        self.ids.error.text = ""
        self._cargar_especialidades()
        self._actualizar_precio()

    def _cargar_especialidades(self):
        self.ids.grid_especialidades.clear_widgets()

        for esp in ESPECIALIDADES:
            btn = ToggleButton(
                text=esp,
                size_hint_y=None,
                height="44dp",
                font_size="13sp",
                background_normal="",
                background_down="",
                background_color=(0.23, 0.18, 0.55, 1),
                color=(1, 1, 1, 1),
            )
            btn.bind(on_press=self._toggle_especialidad)
            self.ids.grid_especialidades.add_widget(btn)

    def _toggle_especialidad(self, btn):
        esp = btn.text
        if esp in self._especialidades_seleccionadas:
            self._especialidades_seleccionadas.remove(esp)
            btn.background_color = (0.23, 0.18, 0.55, 1)
        else:
            self._especialidades_seleccionadas.append(esp)
            btn.background_color = (0.18, 0.80, 0.44, 1)

        self._actualizar_precio()

    def _actualizar_precio(self):
        n = len(self._especialidades_seleccionadas)
        if n == 0:
            precio = PRECIO_SUSCRIPCION
            detalle = f"Suscripcion base (incluye 1 especialidad): ${PRECIO_SUSCRIPCION:,}"
        elif n == 1:
            precio = PRECIO_SUSCRIPCION
            detalle = f"Suscripcion base (1 especialidad incluida): ${PRECIO_SUSCRIPCION:,}"
        else:
            extras = n - 1
            precio = PRECIO_SUSCRIPCION + (extras * PRECIO_ESPECIALIDAD_EXTRA)
            detalle = (
                f"Suscripcion base: ${PRECIO_SUSCRIPCION:,} + "
                f"{extras} especialidad(es) extra: ${extras * PRECIO_ESPECIALIDAD_EXTRA:,}"
            )

        self.ids.lbl_precio.text = f"Total a pagar: ${precio:,}"
        self.ids.lbl_detalle_precio.text = detalle
        session.monto_suscripcion = precio
        session.especialidades_abogado = list(self._especialidades_seleccionadas)

    def registrar(self):
        if self._registro_en_proceso:
            return

        self._registro_en_proceso = True

        nombre = self.ids.nombre.text.strip()
        email = self.ids.email.text.strip().lower()
        password = self.ids.password.text.strip()
        password_confirm = self.ids.password_confirm.text.strip()
        telefono = self.ids.telefono.text.strip()
        matricula = self.ids.matricula.text.strip()
        provincia = self.ids.provincia.text.strip()
        descripcion = self.ids.descripcion.text.strip()
        experiencia = self.ids.experiencia.text.strip()

        self.ids.error.color = (0.90, 0.25, 0.25, 1)
        self.ids.error.text = ""

        if not all([nombre, email, password, password_confirm, matricula, provincia]):
            self.ids.error.text = "Completa todos los campos obligatorios (*)"
            self._registro_en_proceso = False
            return

        if len(self._especialidades_seleccionadas) == 0:
            self.ids.error.text = "Selecciona al menos una especialidad"
            self._registro_en_proceso = False
            return

        if password != password_confirm:
            self.ids.error.text = "Las contrasenas no coinciden"
            self._registro_en_proceso = False
            return

        if len(password) < 6:
            self.ids.error.text = "La contrasena debe tener al menos 6 caracteres"
            self._registro_en_proceso = False
            return

        try:
            import json
            datos_extra = {
                'matricula': matricula,
                'provincia': provincia,
                'acepto_terminos': True,
                'fecha_aceptacion': __import__('datetime').datetime.now().isoformat(),
                'version_terminos': '1.0',
                'descripcion': descripcion,
                'experiencia': experiencia,
                'especialidad': self._especialidades_seleccionadas[0],
                'especialidades': json.dumps(self._especialidades_seleccionadas),
                'estado_abogado': 'ocupado',
                'aprobado': False,
                'suscripcion_activa': False,
                'username': nombre,
            }

            ok, uid, error = fb.crear_usuario(
                email=email,
                password=password,
                nombre=nombre,
                rol="abogado",
                telefono=telefono,
                datos_extra=datos_extra
            )

            if ok:
                session.pending_uid = uid
                session.pending_email = email
                session.abogado_registrando_uid = uid

                self.ids.error.color = (0.18, 0.80, 0.44, 1)
                self.ids.error.text = "Cuenta creada. Procesando pago..."

                Clock.schedule_once(
                    lambda dt: setattr(self.manager, 'current', 'pago_suscripcion'),
                    1.0
                )
            else:
                self.ids.error.text = error or "Error al crear cuenta"

        except Exception as e:
            print(f"ERROR REGISTER ABOGADO: {e}")
            self.ids.error.text = "Error inesperado"

        self._registro_en_proceso = False

    def volver(self):
        self.manager.current = 'register'