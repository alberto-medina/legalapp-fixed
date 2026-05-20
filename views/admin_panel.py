from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp
from kivy.core.window import Window
import firebase_config as fb
import session


class AdminPanelScreen(Screen):

    def on_enter(self):
        """Cargar lista de abogados y retiros al entrar"""
        self.cargar_abogados()
        self.cargar_retiros()

    # ============================================================
    # ABOGADOS
    # ============================================================
    def cargar_abogados(self):
        """Cargar abogados en la lista"""
        abogados = fb.listar_abogados(disponibles=False)

        container = self.ids.abogados_container
        container.clear_widgets()

        if not abogados:
            lbl = Label(
                text='No hay abogados registrados',
                size_hint_y=None,
                height=dp(40)
            )
            container.add_widget(lbl)
            return

        for abogado in abogados:
            box = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(80),
                spacing=dp(10),
                padding=[dp(5), dp(5)]
            )

            nombre = abogado.get('username', 'Sin nombre')
            email = abogado.get('email', '')
            estado = abogado.get('estado_abogado', 'desconocido')
            especialidad = abogado.get('especialidad', '')

            info = Label(
                text=f'{nombre}\n{email}\n{especialidad} | Estado: {estado}',
                size_hint_x=0.7,
                halign='left',
                valign='middle',
                text_size=(None, None),
                font_size=dp(12)
            )

            btn = Button(
                text='Ver',
                size_hint_x=0.3,
                background_color=(0.3, 0.23, 0.67, 1),
                font_size=dp(14)
            )
            btn.bind(on_release=lambda x, a=abogado: self.ver_abogado(a))

            box.add_widget(info)
            box.add_widget(btn)
            container.add_widget(box)

    def ver_abogado(self, abogado_data):
        """Mostrar detalles del abogado en popup"""
        popup_width = Window.width * 0.9
        content_width = popup_width - dp(40)

        main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        scroll = ScrollView(do_scroll_x=False, size_hint_y=1)

        content = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        campos = [
            ("Nombre", abogado_data.get('username', '')),
            ("Email", abogado_data.get('email', '')),
            ("Teléfono", abogado_data.get('telefono', '')),
            ("Matrícula", abogado_data.get('matricula', '')),
            ("Especialidad", abogado_data.get('especialidad', '')),
            ("Experiencia", abogado_data.get('experiencia', '')),
            ("Descripción", abogado_data.get('descripcion', '')),
            ("Estado", abogado_data.get('estado_abogado', '')),
            ("Saldo", f"${abogado_data.get('saldo', 0):,.2f}"),
            ("CBU/Cuenta", abogado_data.get('cuenta_bancaria', 'No cargado')),
        ]

        for titulo, valor in campos:
            campo_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))

            lbl_titulo = Label(
                text=f"[b]{titulo}:[/b]",
                markup=True,
                halign='left',
                valign='top',
                size_hint_y=None,
                font_size=dp(13),
                color=(0.7, 0.7, 0.7, 1),
                text_size=(content_width, None)
            )

            lbl_valor = Label(
                text=str(valor),
                halign='left',
                valign='top',
                size_hint_y=None,
                font_size=dp(14),
                color=(1, 1, 1, 1),
                text_size=(content_width, None)
            )

            def update_titulo_height(instance, value):
                lbl_titulo.height = value[1] + dp(4)

            def update_valor_height(instance, value):
                lbl_valor.height = value[1] + dp(4)

            lbl_titulo.bind(texture_size=update_titulo_height)
            lbl_valor.bind(texture_size=update_valor_height)

            lbl_titulo.texture_update()
            lbl_valor.texture_update()

            campo_box.add_widget(lbl_titulo)
            campo_box.add_widget(lbl_valor)

            def update_box_height(instance, value):
                campo_box.height = lbl_titulo.height + lbl_valor.height + dp(8)

            lbl_titulo.bind(height=update_box_height)
            lbl_valor.bind(height=update_box_height)
            update_box_height(None, None)

            content.add_widget(campo_box)

        scroll.add_widget(content)
        main_layout.add_widget(scroll)

        btn_cerrar = Button(
            text='Cerrar',
            size_hint_y=None,
            height=dp(50),
            background_color=(0.5, 0.5, 0.5, 1)
        )
        main_layout.add_widget(btn_cerrar)

        popup = Popup(
            title='Detalle Abogado',
            content=main_layout,
            size_hint=(None, None),
            width=popup_width,
            height=Window.height * 0.8
        )
        btn_cerrar.bind(on_release=popup.dismiss)
        popup.open()

    def mostrar_formulario_crear(self):
        """Mostrar popup para crear nuevo abogado"""
        layout = BoxLayout(orientation='vertical', padding=dp(15), spacing=dp(10))

        campos = {
            'email': TextInput(hint_text='Email', multiline=False),
            'password': TextInput(hint_text='Contraseña temporal', password=True, multiline=False),
            'nombre': TextInput(hint_text='Nombre completo', multiline=False),
            'telefono': TextInput(hint_text='Teléfono', multiline=False),
            'matricula': TextInput(hint_text='Matrícula', multiline=False),
            'especialidad': TextInput(hint_text='Especialidad', multiline=False),
            'experiencia': TextInput(hint_text='Años de experiencia', multiline=False),
            'descripcion': TextInput(hint_text='Descripción profesional', multiline=False),
        }

        for campo in campos.values():
            layout.add_widget(campo)

        lbl_error = Label(text='', color=(0.9, 0.2, 0.2, 1), size_hint_y=None, height=dp(30))
        layout.add_widget(lbl_error)

        btn_crear = Button(
            text='Crear Abogado',
            size_hint_y=None,
            height=dp(50),
            background_color=(0.18, 0.8, 0.44, 1)
        )
        btn_cancelar = Button(
            text='Cancelar',
            size_hint_y=None,
            height=dp(50)
        )

        btn_box = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(50))
        btn_box.add_widget(btn_crear)
        btn_box.add_widget(btn_cancelar)
        layout.add_widget(btn_box)

        popup = Popup(title='Nuevo Abogado', content=layout, size_hint=(0.9, 0.9))

        def crear(instance):
            email = campos['email'].text.strip()
            password = campos['password'].text.strip()
            nombre = campos['nombre'].text.strip()

            if not all([email, password, nombre]):
                lbl_error.text = 'Email, contraseña y nombre son obligatorios'
                return

            ok, uid, error = fb.crear_abogado_manual(
                email=email,
                password=password,
                nombre=nombre,
                telefono=campos['telefono'].text.strip(),
                matricula=campos['matricula'].text.strip(),
                especialidad=campos['especialidad'].text.strip(),
                experiencia=campos['experiencia'].text.strip(),
                descripcion=campos['descripcion'].text.strip()
            )

            if ok:
                popup.dismiss()
                self.cargar_abogados()
            else:
                lbl_error.text = f'Error: {error}'

        btn_crear.bind(on_release=crear)
        btn_cancelar.bind(on_release=popup.dismiss)

        popup.open()

    # ============================================================
    # RETIROS PENDIENTES
    # ============================================================
    def cargar_retiros(self):
        """Cargar retiros pendientes en la lista"""
        retiros = fb.listar_retiros_pendientes()

        container = self.ids.retiros_container
        container.clear_widgets()

        if not retiros:
            lbl = Label(
                text='No hay retiros pendientes',
                size_hint_y=None,
                height=dp(40)
            )
            container.add_widget(lbl)
            return

        for retiro in retiros:
            box = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(80),
                spacing=dp(10),
                padding=[dp(5), dp(5)]
            )

            email = retiro.get('abogado_email', 'Sin email')
            monto = retiro.get('monto_bruto', 0)
            cuenta = retiro.get('cuenta_destino', 'Sin cuenta')
            fecha = retiro.get('fecha', '')
            retiro_id = retiro.get('id', '')

            info = Label(
                text=f'{email}\nMonto: ${monto:,.2f}\nCuenta: {cuenta}\nFecha: {fecha}',
                size_hint_x=0.6,
                halign='left',
                valign='middle',
                text_size=(None, None),
                font_size=dp(11)
            )

            btn_pagar = Button(
                text='PAGAR',
                size_hint_x=0.4,
                background_color=(0.18, 0.8, 0.44, 1),
                font_size=dp(14)
            )
            btn_pagar.bind(on_release=lambda x, rid=retiro_id: self.procesar_retiro_pago(rid))

            box.add_widget(info)
            box.add_widget(btn_pagar)
            container.add_widget(box)

    def procesar_retiro_pago(self, retiro_id):
        """Procesar el pago de un retiro"""
        user = session.current_user
        if not user:
            self.mostrar_error("Error: No hay usuario logueado")
            return

        ok, mensaje = fb.procesar_retiro(retiro_id, user.get('uid'))

        if ok:
            self.mostrar_exito(mensaje)
            self.cargar_retiros()  # Recargar lista
        else:
            self.mostrar_error(mensaje)

    def mostrar_exito(self, mensaje):
        """Mostrar popup de éxito"""
        popup = Popup(
            title='Éxito',
            content=Label(text=mensaje, color=(0.18, 0.8, 0.44, 1)),
            size_hint=(0.8, 0.3)
        )
        popup.open()

    def mostrar_error(self, mensaje):
        """Mostrar popup de error"""
        popup = Popup(
            title='Error',
            content=Label(text=mensaje, color=(0.9, 0.2, 0.2, 1)),
            size_hint=(0.8, 0.3)
        )
        popup.open()

    def volver(self):
        """Volver al login"""
        self.manager.current = 'login'