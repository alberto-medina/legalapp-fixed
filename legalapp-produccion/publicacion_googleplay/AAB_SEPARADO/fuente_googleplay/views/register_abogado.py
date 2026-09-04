from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.uix.togglebutton import ToggleButton
import json

import supabase_config as fb
from views.ubicacion import PROVINCIAS_CIUDADES, abrir_selector
from views.form_keyboard import FormKeyboardMixin
import session

ESPECIALIDADES = [
    "Derecho Civil",
    "Derecho Penal",
    "Derecho Laboral",
    "Derecho de Familia",
    "Derecho Comercial",
    "Derecho Empresarial",
    "Derecho Administrativo",
    "Derecho Tributario",
    "Derecho Inmobiliario",
    "Derecho Sucesorio",
    "Derecho Previsional",
    "Derecho del Consumidor",
    "Derecho de Transito",
    "Derecho Migratorio",
    "Derecho Ambiental",
    "Derecho Informatico",
    "Derecho de Danos y Perjuicios",
    "Derecho Contractual",
    "Derecho Societario",
    "Derecho de Seguros",
    "Derecho de Salud",
    "Derecho Internacional",
    "Derecho Constitucional",
    "Mediacion",
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


class RegisterAbogadoScreen(FormKeyboardMixin, Screen):

    _provincia_seleccionada = None
    _ciudad_seleccionada = None

    def abrir_selector_provincia(self):
        provincias = list(PROVINCIAS_CIUDADES.keys())
        abrir_selector('Elegí tu provincia', provincias, self._on_provincia)

    def _on_provincia(self, provincia):
        self._provincia_seleccionada = provincia
        self._ciudad_seleccionada = None
        self.ids.btn_provincia.text = provincia
        self.ids.btn_ciudad.text = 'Elegí la ciudad'

    def abrir_selector_ciudad(self):
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
        self.ids.btn_ciudad.text = ciudad

    _registro_en_proceso = False
    _especialidades_seleccionadas = []

    def obtener_precios(self):
        config = fb.obtener_configuracion() or {}

        try:
            suscripcion_base = int(config.get("precio_suscripcion_base", 55000))
        except:
            suscripcion_base = 55000

        try:
            extra = int(config.get("precio_especialidad_extra", 10000))
        except:
            extra = 10000

        return suscripcion_base, extra

    def on_leave(self):
        self._teardown_form_keyboard()

    def on_enter(self):
        self._setup_form_keyboard("register_abogado_scroll")
        self._especialidades_seleccionadas = []
        self._registro_en_proceso = False
        self.ids.error.text = ""

        if "terms_check" in self.ids:
            self.ids.terms_check.active = False

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

        base, extra_unit = self.obtener_precios()

        n = len(self._especialidades_seleccionadas)

        if n == 0:
            precio = base
            detalle = f"Suscripcion base (incluye 1 especialidad): ${base:,}"

        elif n == 1:
            precio = base
            detalle = f"Suscripcion base (1 especialidad incluida): ${base:,}"

        else:
            extras = n - 1
            precio = base + (extras * extra_unit)

            detalle = (
                f"Suscripcion base: ${base:,} + "
                f"{extras} especialidad(es) extra: ${extras * extra_unit:,}"
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
        provincia = (self._provincia_seleccionada or '').strip()
        ciudad = (self._ciudad_seleccionada or '').strip()
        descripcion = self.ids.descripcion.text.strip()
        experiencia = self.ids.experiencia.text.strip()

        terms_accepted = self.ids.terms_check.active

        self.ids.error.color = (0.90, 0.25, 0.25, 1)
        self.ids.error.text = ""

        # FIX: Ciudad es obligatoria
        if not all([nombre, email, password, password_confirm, matricula, provincia, ciudad]):
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

        if not terms_accepted:
            self.ids.error.text = "Debes aceptar los terminos y privacidad"
            self._registro_en_proceso = False
            return

        # Verificar si email ya existe pero no verificado
        try:
            usuario_existente = fb.obtener_usuario_por_email(email)

            if usuario_existente:
                uid_existente = usuario_existente.get('uid')
                email_verificado = usuario_existente.get('email_verified', False)

                if not email_verificado:

                    # FIX: Actualizar datos incluyendo ciudad
                    fb.actualizar_usuario(uid_existente, {
                        'username': nombre,
                        'telefono': telefono,
                        'matricula': matricula,
                        'provincia': provincia,
                        'ciudad': ciudad,
                        'descripcion': descripcion,
                        'experiencia': experiencia,
                        'especialidad': self._especialidades_seleccionadas[0] if self._especialidades_seleccionadas else '',
                        'especialidades': json.dumps(self._especialidades_seleccionadas),
                    })

                    # Reenviar verificación (Firebase o fallback)
                    id_token = getattr(session, 'id_token', None)
                    ok, metodo = fb.reenviar_codigo_verificacion(email, uid_existente, id_token=id_token)

                    session.pending_uid = uid_existente
                    session.pending_email = email
                    session.abogado_registrando_uid = uid_existente
                    session.guardar()

                    self.ids.error.color = (0.2, 0.6, 0.9, 1)
                    self.ids.error.text = "Email ya registrado. Reenviando verificación..."

                    Clock.schedule_once(
                        lambda dt: setattr(self.manager, 'current', 'verification'),
                        1.5
                    )
                    self._registro_en_proceso = False
                    return

                else:
                    self.ids.error.text = "Este email ya esta registrado. Inicia sesion."
                    self._registro_en_proceso = False
                    return

        except Exception as e:
            print(f"ERROR check usuario existente: {e}")
            pass

        try:
            import json
            from datetime import datetime

            # FIX: Incluir ciudad en datos_extra
            datos_extra = {
                'ciudad': ciudad,
                'matricula': matricula,
                'provincia': provincia,
                'acepto_terminos': True,
                'fecha_aceptacion': datetime.now().isoformat(),
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
                session.guardar()

                # FIX: Obtener id_token Y refresh_token haciendo login con credenciales recién creadas
                ok_login, auth_data, login_error = fb.login_usuario_auth(email, password)
                id_token = None
                refresh_token = None
                if ok_login:
                    id_token = auth_data.get('idToken')
                    refresh_token = auth_data.get('refreshToken')
                    session.id_token = id_token
                    session.refresh_token = refresh_token
                    session.guardar()

                # Enviar verificación por Firebase (o fallback)
                fb_ok, metodo = fb.enviar_codigo_verificacion(email, uid, id_token=id_token)
                if not fb_ok:
                    print(f"WARNING: No se pudo enviar email de verificación: {metodo}")

                self.ids.error.color = (0.18, 0.80, 0.44, 1)
                self.ids.error.text = "Cuenta creada. Revisa tu email..."

                Clock.schedule_once(
                    lambda dt: setattr(self.manager, 'current', 'verification'),
                    1.0
                )

            else:
                self.ids.error.text = error or "Error al crear cuenta"

        except Exception as e:
            print(f"ERROR REGISTER ABOGADO: {e}")
            self.ids.error.text = "Error inesperado"

        self._registro_en_proceso = False

    def volver(self):
        self.manager.current = 'login'
