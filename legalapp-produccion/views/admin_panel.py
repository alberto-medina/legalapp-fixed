from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle

import supabase_config as fb
import session

# Color de texto oscuro para fondos claros
COLOR_TEXTO = (0.10, 0.12, 0.18, 1)
COLOR_TEXTO_CLARO = (0.45, 0.50, 0.58, 1)


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
            # Usar _rest_get directo para traer TODOS los abogados (incluso no aprobados)
            abogados = fb._rest_get("usuarios", filters={"rol": "eq.abogado"})
        except Exception as e:
            print("ERROR cargando abogados:", e)
            abogados = []

        container = self.ids.abogados_container
        container.clear_widgets()

        if not abogados:
            container.add_widget(Label(
                text='No hay abogados registrados',
                size_hint_y=None,
                height=dp(40),
                color=COLOR_TEXTO,
                font_size=sp(14)
            ))
            return

        for abogado in abogados:
            # Fila principal
            row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(128),
                spacing=dp(8),
                padding=[dp(8), dp(8)]
            )

            nombre = abogado.get('username', 'Sin nombre')
            email = abogado.get('email', '')
            estado = abogado.get('estado_abogado', 'desconocido')
            especialidad = abogado.get('especialidad', '')
            aprobado = abogado.get("aprobado", False)
            suscripcion_activa = abogado.get("suscripcion_activa", False)
            suscripcion_ok = fb.suscripcion_habilitada(abogado)
            estado_aprobacion = "✅ APROBADO" if aprobado else "⏳ PENDIENTE"
            estado_suscripcion = "💳 SUSCRIPCIÓN OK" if suscripcion_ok else "⚠ SUSCRIPCIÓN INVÁLIDA"

            # Info del abogado
            info = Label(
                text=f"[b]{nombre}[/b]\n{email}\n{especialidad}\nEstado: {estado}\n{estado_aprobacion}\n{estado_suscripcion}",
                markup=True,
                size_hint_x=0.50,
                halign='left',
                valign='middle',
                text_size=(None, None),
                font_size=sp(12),
                color=COLOR_TEXTO,
            )
            info.bind(size=lambda s, *_: setattr(s, 'text_size', s.size))

            # Botones más compactos
            btn_ver = Button(
                text='Ver',
                size_hint_x=0.16,
                background_color=(0.3, 0.23, 0.67, 1),
                color=(1, 1, 1, 1),
                font_size=sp(11),
                bold=True
            )

            btn_aprobar = Button(
                text='Aprobar' if suscripcion_ok else 'Sin pago',
                size_hint_x=0.16,
                background_color=(0.18, 0.8, 0.44, 1) if suscripcion_ok else (0.55, 0.55, 0.60, 1),
                color=(1, 1, 1, 1),
                font_size=sp(11),
                bold=True,
                disabled=not suscripcion_ok
            )

            # Toggle Bloquear / Desbloquear según estado
            if suscripcion_activa:
                btn_accion = Button(
                    text='Bloquear',
                    size_hint_x=0.16,
                    background_color=(0.9, 0.2, 0.2, 1),
                    color=(1, 1, 1, 1),
                    font_size=sp(11),
                    bold=True
                )
                btn_accion.bind(on_release=lambda x, uid=abogado["uid"]: self.bloquear_abogado(uid))
            else:
                btn_accion = Button(
                    text='Desbloquear',
                    size_hint_x=0.16,
                    background_color=(0.18, 0.8, 0.44, 1),
                    color=(1, 1, 1, 1),
                    font_size=sp(11),
                    bold=True
                )
                btn_accion.bind(on_release=lambda x, uid=abogado["uid"]: self.reactivar_abogado(uid))

            btn_ver.bind(on_release=lambda x, a=abogado: self.ver_abogado(a))
            btn_aprobar.bind(on_release=lambda x, uid=abogado["uid"]: self.aprobar_abogado(uid))

            row.add_widget(info)
            row.add_widget(btn_ver)
            row.add_widget(btn_aprobar)
            row.add_widget(btn_accion)

            container.add_widget(row)

    def aprobar_abogado(self, uid):
        try:
            ok, mensaje = fb.aprobar_abogado(uid)
            if ok:
                self.mostrar_exito(mensaje)
                self.cargar_abogados()
            else:
                self.mostrar_error(mensaje)
        except Exception as e:
            self.mostrar_error(str(e))

    def bloquear_abogado(self, uid):
        try:
            ok = fb.desactivar_suscripcion_abogado(uid)
            if ok:
                self.mostrar_exito("Abogado bloqueado")
                self.cargar_abogados()
            else:
                self.mostrar_error("Error al bloquear")
        except Exception as e:
            self.mostrar_error(str(e))

    def reactivar_abogado(self, uid):
        try:
            ok, mensaje = fb.reactivar_abogado(uid)
            if ok:
                self.mostrar_exito(mensaje)
                self.cargar_abogados()
            else:
                self.mostrar_error(mensaje)
        except Exception as e:
            self.mostrar_error(str(e))

    def ver_abogado(self, abogado_data):
        popup_width = min(Window.width * 0.9, dp(500))
        content_width = popup_width - dp(50)

        # Layout principal con fondo claro
        main_layout = BoxLayout(
            orientation='vertical',
            padding=dp(15),
            spacing=dp(10),
        )

        # Fondo claro vía canvas.before
        with main_layout.canvas.before:
            Color(rgba=(0.96, 0.97, 0.98, 1))
            rect = Rectangle(pos=main_layout.pos, size=main_layout.size)

        # Actualizar rectángulo cuando cambie tamaño/posición
        def update_rect(instance, value):
            rect.pos = instance.pos
            rect.size = instance.size

        main_layout.bind(pos=update_rect, size=update_rect)

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
            campo_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(4))

            lbl_titulo = Label(
                text=f"[b]{titulo}:[/b]", markup=True,
                halign='left', valign='top', size_hint_y=None,
                font_size=sp(13), color=(0.45, 0.50, 0.58, 1),
                text_size=(content_width, None)
            )
            lbl_valor = Label(
                text=str(valor), halign='left', valign='top',
                size_hint_y=None, font_size=sp(15), color=(0.10, 0.12, 0.18, 1),
                text_size=(content_width, None)
            )

            lbl_titulo.bind(texture_size=lambda i, v: setattr(i, 'height', v[1] + dp(4)))
            lbl_valor.bind(texture_size=lambda i, v: setattr(i, 'height', v[1] + dp(4)))
            lbl_titulo.texture_update()
            lbl_valor.texture_update()

            campo_box.add_widget(lbl_titulo)
            campo_box.add_widget(lbl_valor)

            def update_box(i, v, box=campo_box, t=lbl_titulo, val=lbl_valor):
                box.height = t.height + val.height + dp(10)

            lbl_titulo.bind(height=update_box)
            lbl_valor.bind(height=update_box)
            update_box(None, None)
            content.add_widget(campo_box)

        scroll.add_widget(content)
        main_layout.add_widget(scroll)

        btn_cerrar = Button(
            text='Cerrar',
            size_hint_y=None,
            height=dp(50),
            background_color=(0.24, 0.17, 0.55, 1),
            color=(1, 1, 1, 1),
            font_size=sp(14),
            bold=True
        )
        main_layout.add_widget(btn_cerrar)

        popup = Popup(
            title='Detalle Abogado',
            content=main_layout,
            size_hint=(None, None),
            width=popup_width,
            height=min(Window.height * 0.8, dp(600)),
            background_color=(0.96, 0.97, 0.98, 1),
            title_color=(0.10, 0.12, 0.18, 1),
            title_size=dp(18),
            separator_color=(0.24, 0.17, 0.55, 1),
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
                height=dp(40),
                color=COLOR_TEXTO,
                font_size=sp(14)
            ))
            return

        for retiro in retiros:
            row = BoxLayout(
                orientation='horizontal',
                size_hint_y=None,
                height=dp(126),
                spacing=dp(8),
                padding=[dp(8), dp(8)]
            )

            email = retiro.get('abogado_email', 'Sin email')
            monto = retiro.get('monto_bruto', 0)
            monto_neto = retiro.get('monto_neto', monto)
            cuenta = retiro.get('cuenta_destino', 'Sin cuenta')
            fecha = retiro.get('fecha', '')
            retiro_id = retiro.get('id', '')

            info = Label(
                text=f"[b]{email}[/b]\nBruto: ${monto:,.2f}\nNeto a transferir: ${monto_neto:,.2f}\nCuenta: {cuenta}\nFecha: {fecha[:10]}",
                markup=True,
                size_hint_x=0.60,
                halign='left',
                valign='middle',
                text_size=(None, None),
                font_size=sp(12),
                color=COLOR_TEXTO,
            )
            info.bind(size=lambda s, *_: setattr(s, 'text_size', s.size))

            btn_pagar = Button(
                text='PAGAR',
                size_hint_x=0.35,
                background_color=(0.18, 0.8, 0.44, 1),
                color=(1, 1, 1, 1),
                font_size=sp(13),
                bold=True
            )
            btn_pagar.bind(
                on_release=lambda x, rid=retiro_id, mail=email, cta=cuenta, neto=monto_neto:
                self.confirmar_retiro_pago(rid, mail, cta, neto)
            )

            row.add_widget(info)
            row.add_widget(btn_pagar)
            container.add_widget(row)

    def confirmar_retiro_pago(self, retiro_id, email, cuenta, monto_neto):
        layout = BoxLayout(
            orientation='vertical',
            padding=dp(16),
            spacing=dp(10)
        )

        lbl = Label(
            text=f"[b]{email}[/b]\nTransferir: ${monto_neto:,.2f}\nDestino: {cuenta}",
            markup=True,
            halign='left',
            valign='middle',
            color=COLOR_TEXTO,
        )
        lbl.bind(size=lambda s, *_: setattr(s, 'text_size', s.size))

        botones = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(46),
            spacing=dp(10)
        )

        btn_cancelar = Button(
            text='Cancelar',
            background_normal='',
            background_color=(0.90, 0.90, 0.96, 1),
            color=(0.24, 0.17, 0.55, 1),
            bold=True
        )
        btn_confirmar = Button(
            text='Marcar pagado',
            background_normal='',
            background_color=(0.18, 0.8, 0.44, 1),
            color=(1, 1, 1, 1),
            bold=True
        )

        botones.add_widget(btn_cancelar)
        botones.add_widget(btn_confirmar)
        layout.add_widget(lbl)
        layout.add_widget(botones)

        popup = Popup(
            title='Confirmar retiro',
            content=layout,
            size_hint=(0.88, None),
            height=dp(250),
            auto_dismiss=False
        )

        btn_cancelar.bind(on_release=popup.dismiss)
        btn_confirmar.bind(on_release=lambda *_: self._procesar_retiro_confirmado(retiro_id, popup))
        popup.open()

    def _procesar_retiro_confirmado(self, retiro_id, popup):
        try:
            popup.dismiss()
        except Exception:
            pass
        self.procesar_retiro_pago(retiro_id)

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

            # Fallbacks por defecto
            defaults = {
                "precio_chat": 1000,
                "precio_video": 3000,
                "precio_urgente": 5000,
                "precio_suscripcion_base": 55000,
                "precio_especialidad_extra": 10000
            }

            for clave, descripcion in claves:
                # Obtener valor, con fallback a defaults
                valor = precios.get(clave)
                if not valor or valor == "0" or valor == 0:
                    valor = defaults.get(clave, 0)
                else:
                    try:
                        valor = int(valor)
                    except:
                        valor = defaults.get(clave, 0)

                row = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=None,
                    height=dp(56),
                    spacing=dp(10),
                )

                lbl = Label(
                    text=descripcion,
                    size_hint_x=0.50,
                    halign='left',
                    valign='middle',
                    text_size=(None, None),
                    font_size=sp(14),
                    color=COLOR_TEXTO,
                    bold=True
                )

                inp = TextInput(
                    text=str(valor),
                    size_hint_x=0.30,
                    multiline=False,
                    input_filter='int',
                    font_size=sp(16),
                    padding=[dp(10), dp(12)],
                    foreground_color=COLOR_TEXTO,
                    background_color=(1, 1, 1, 1),
                    cursor_color=(0.24, 0.17, 0.55, 1),
                )

                btn = Button(
                    text='Guardar',
                    size_hint_x=0.20,
                    background_normal='',
                    background_color=(0.24, 0.17, 0.55, 1),
                    color=(1, 1, 1, 1),
                    font_size=sp(12),
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

        print(f"ADMIN: guardando {clave} = {valor}")
        ok = fb.actualizar_configuracion(clave, valor)
        print(f"ADMIN: resultado = {ok}")

        if ok:
            self.mostrar_exito(f"Precio actualizado: ${valor}")
        else:
            self.mostrar_error("Error al guardar en Supabase. Verifica conexion y permisos.")

    # ============================================================
    # POPUPS
    # ============================================================

    def mostrar_exito(self, mensaje):
        popup = Popup(
            title='Exito',
            content=Label(text=mensaje, color=(0.18, 0.8, 0.44, 1), font_size=sp(16)),
            size_hint=(0.8, 0.25)
        )
        popup.open()

    def mostrar_error(self, mensaje):
        popup = Popup(
            title='Error',
            content=Label(text=mensaje, color=(0.9, 0.2, 0.2, 1), font_size=sp(16)),
            size_hint=(0.8, 0.25)
        )
        popup.open()

    def volver(self):
        self.manager.current = 'login'
