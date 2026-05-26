from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp
from kivy.core.window import Window

import supabase_config as fb
import session


class AdminPanelScreen(Screen):

    def on_enter(self):
        self.cargar_abogados()
        self.cargar_retiros()
        self.cargar_precios()

    # ============================================================
    # ABOGADOS
    # ============================================================

    def cargar_abogados(self):
        try:
            abogados = fb.supabase.table("usuarios") \
                .select("*") \
                .eq("rol", "abogado") \
                .execute()
            abogados = abogados.data
        except Exception as e:
            print("ERROR cargando abogados:", e)
            abogados = []

        container = self.ids.abogados_container
        container.clear_widgets()

        if not abogados:
            container.add_widget(Label(
                text='No hay abogados registrados',
                size_hint_y=None,
                height=dp(40)
            ))
            return

        for abogado in abogados:
            box = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(120),
                spacing=dp(10),
                padding=[dp(5), dp(5)]
            )

            nombre = abogado.get('username', 'Sin nombre')
            email = abogado.get('email', '')
            estado = abogado.get('estado_abogado', 'desconocido')
            especialidad = abogado.get('especialidad', '')
            aprobado = abogado.get("aprobado", False)
            estado_aprobacion = "APROBADO" if aprobado else "PENDIENTE"

            info = Label(
                text=f'{nombre}\n{email}\n{especialidad}\nEstado: {estado}\n{estado_aprobacion}',
                size_hint_x=0.55,
                halign='left',
                valign='middle',
                text_size=(None, None),
                font_size=dp(12)
            )

            btn_ver = Button(
                text='Ver',
                size_hint_x=0.15,
                background_color=(0.3, 0.23, 0.67, 1),
                font_size=dp(14)
            )

            btn_aprobar = Button(
                text='Aprobar',
                size_hint_x=0.15,
                background_color=(0.18, 0.8, 0.44, 1),
                font_size=dp(14)
            )

            btn_bloquear = Button(
                text='Bloquear',
                size_hint_x=0.15,
                background_color=(0.9, 0.2, 0.2, 1),
                font_size=dp(14)
            )

            btn_ver.bind(on_release=lambda x, a=abogado: self.ver_abogado(a))
            btn_aprobar.bind(on_release=lambda x, uid=abogado["uid"]: self.aprobar_abogado(uid))
            btn_bloquear.bind(on_release=lambda x, uid=abogado["uid"]: self.bloquear_abogado(uid))

            box.add_widget(info)
            box.add_widget(btn_ver)
            box.add_widget(btn_aprobar)
            box.add_widget(btn_bloquear)

            container.add_widget(box)

    def aprobar_abogado(self, uid):
        try:
            fb.supabase.table("usuarios") \
                .update({"aprobado": True}) \
                .eq("uid", uid) \
                .execute()
            self.mostrar_exito("Abogado aprobado")
            self.cargar_abogados()
        except Exception as e:
            self.mostrar_error(str(e))

    def bloquear_abogado(self, uid):
        try:
            fb.supabase.table("usuarios") \
                .update({"aprobado": False}) \
                .eq("uid", uid) \
                .execute()
            self.mostrar_exito("Abogado bloqueado")
            self.cargar_abogados()
        except Exception as e:
            self.mostrar_error(str(e))

    def ver_abogado(self, abogado_data):
        popup_width = Window.width * 0.9
        content_width = popup_width - dp(40)

        main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        scroll = ScrollView(do_scroll_x=False, size_hint_y=1)
        content = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        aprobado = abogado_data.get("aprobado", False)

        campos = [
            ("Nombre", abogado_data.get('username', '')),
            ("Email", abogado_data.get('email', '')),
            ("Telefono", abogado_data.get('telefono', '')),
            ("Matricula", abogado_data.get('matricula', '')),
            ("Especialidad", abogado_data.get('especialidad', '')),
            ("Experiencia", abogado_data.get('experiencia', '')),
            ("Descripcion", abogado_data.get('descripcion', '')),
            ("Estado", abogado_data.get('estado_abogado', '')),
            ("Aprobado", "SI" if aprobado else "NO"),
            ("Saldo", f"${abogado_data.get('saldo', 0):,.2f}"),
            ("CBU/Cuenta", abogado_data.get('cuenta_bancaria', 'No cargado')),
        ]

        for titulo, valor in campos:
            campo_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))

            lbl_titulo = Label(
                text=f"[b]{titulo}:[/b]", markup=True,
                halign='left', valign='top', size_hint_y=None,
                font_size=dp(13), color=(0.7, 0.7, 0.7, 1),
                text_size=(content_width, None)
            )
            lbl_valor = Label(
                text=str(valor), halign='left', valign='top',
                size_hint_y=None, font_size=dp(14), color=(1, 1, 1, 1),
                text_size=(content_width, None)
            )

            lbl_titulo.bind(texture_size=lambda i, v: setattr(i, 'height', v[1] + dp(4)))
            lbl_valor.bind(texture_size=lambda i, v: setattr(i, 'height', v[1] + dp(4)))
            lbl_titulo.texture_update()
            lbl_valor.texture_update()

            campo_box.add_widget(lbl_titulo)
            campo_box.add_widget(lbl_valor)

            def update_box(i, v, box=campo_box, t=lbl_titulo, val=lbl_valor):
                box.height = t.height + val.height + dp(8)

            lbl_titulo.bind(height=update_box)
            lbl_valor.bind(height=update_box)
            update_box(None, None)
            content.add_widget(campo_box)

        scroll.add_widget(content)
        main_layout.add_widget(scroll)

        btn_cerrar = Button(text='Cerrar', size_hint_y=None, height=dp(50), background_color=(0.5, 0.5, 0.5, 1))
        main_layout.add_widget(btn_cerrar)

        popup = Popup(
            title='Detalle Abogado', content=main_layout,
            size_hint=(None, None), width=popup_width, height=Window.height * 0.8
        )
        btn_cerrar.bind(on_release=popup.dismiss)
        popup.open()

    # ============================================================
    # RETIROS PENDIENTES
    # ============================================================

    def cargar_retiros(self):
        try:
            retiros = fb.listar_retiros_pendientes()
        except:
            retiros = []

        container = self.ids.retiros_container
        container.clear_widgets()

        if not retiros:
            container.add_widget(Label(
                text='No hay retiros pendientes',
                size_hint_y=None,
                height=dp(40)
            ))
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
        user = session.current_user
        if not user:
            self.mostrar_error("Error: No hay usuario logueado")
            return

        ok, mensaje = fb.procesar_retiro(retiro_id, user.get('uid'))

        if ok:
            self.mostrar_exito(mensaje)
            self.cargar_retiros()
        else:
            self.mostrar_error(mensaje)

    # ============================================================
    # PRECIOS
    # ============================================================

    def cargar_precios(self):
        try:
            precios = fb.obtener_configuracion()
            container = self.ids.precios_container
            container.clear_widgets()

            claves = [
                ("precio_chat", "Consulta Chat"),
                ("precio_video", "Consulta Video"),
                ("precio_urgente", "Consulta Urgente"),
                ("precio_suscripcion_base", "Suscripcion base abogado"),
                ("precio_especialidad_extra", "Especialidad adicional"),
            ]

            for clave, descripcion in claves:
                valor = precios.get(clave, "0")

                row = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=None,
                    height=dp(52),
                    spacing=dp(10),
                )

                lbl = Label(
                    text=descripcion,
                    size_hint_x=0.55,
                    halign='left',
                    valign='middle',
                    text_size=(None, None),
                    font_size=dp(13),
                    color=(0.10, 0.12, 0.18, 1),
                )

                inp = TextInput(
                    text=str(valor),
                    size_hint_x=0.25,
                    multiline=False,
                    input_filter='int',
                    font_size=dp(14),
                    padding=[dp(8), dp(10)],
                )

                btn = Button(
                    text='Guardar',
                    size_hint_x=0.20,
                    background_normal='',
                    background_color=(0.24, 0.17, 0.55, 1),
                    color=(1, 1, 1, 1),
                    font_size=dp(12),
                    bold=True,
                )
                btn.bind(on_release=lambda x, k=clave, i=inp: self.guardar_precio(k, i))

                row.add_widget(lbl)
                row.add_widget(inp)
                row.add_widget(btn)
                container.add_widget(row)

        except Exception as e:
            print(f"ERROR cargar_precios: {e}")

    def guardar_precio(self, clave, input_widget):
        valor = input_widget.text.strip()
        if not valor:
            self.mostrar_error("Ingresa un valor")
            return
        try:
            int(valor)
        except:
            self.mostrar_error("El valor debe ser un numero")
            return

        ok = fb.actualizar_configuracion(clave, valor)
        if ok:
            self.mostrar_exito(f"Precio actualizado: ${valor}")
        else:
            self.mostrar_error("Error al guardar")

    # ============================================================
    # POPUPS
    # ============================================================

    def mostrar_exito(self, mensaje):
        popup = Popup(
            title='Exito',
            content=Label(text=mensaje, color=(0.18, 0.8, 0.44, 1)),
            size_hint=(0.8, 0.3)
        )
        popup.open()

    def mostrar_error(self, mensaje):
        popup = Popup(
            title='Error',
            content=Label(text=mensaje, color=(0.9, 0.2, 0.2, 1)),
            size_hint=(0.8, 0.3)
        )
        popup.open()

    def volver(self):
        self.manager.current = 'login'