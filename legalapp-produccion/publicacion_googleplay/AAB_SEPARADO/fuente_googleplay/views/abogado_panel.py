from functools import partial
import threading

from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from views.utils_avatar import set_avatar_image

import session
import supabase_config as fb


COLOR_TEXTO = (0.10, 0.12, 0.18, 1)
COLOR_MUTED = (0.45, 0.50, 0.58, 1)

FILTROS = {
    "todas": lambda c: c.get("estado") != "pendiente",
    "activas": lambda c: c.get("estado") in ["pagado", "en_curso", "videollamada"],
    "finalizadas": lambda c: c.get("estado") == "finalizado",
    "chat": lambda c: c.get("tipo_servicio") == "chat",
    "video": lambda c: c.get("tipo_servicio") == "video",
    "urgente": lambda c: c.get("tipo_servicio") == "urgente",
}


def _normalizar_texto_persona(texto):
    valor = str(texto or "").strip()
    if not valor:
        return ""
    if "@" in valor:
        return valor.lower()
    return " ".join(parte.capitalize() for parte in valor.split())


class AbogadoPanelScreen(Screen):
    _filtro = "todas"
    _consultas = []
    _cargando_panel = False

    def on_enter(self):
        self._filtro = "todas"
        self.cargar_panel()

    def cargar_panel(self):
        if self._cargando_panel:
            return

        user = session.current_user
        if not user:
            self.manager.current = "login"
            return

        self._cargando_panel = True
        uid = user.get("uid")

        def _worker():
            try:
                fb.sincronizar_saldo_abogado(uid)
                user_data = fb.obtener_usuario(uid) or user
                consultas = fb.obtener_consultas_usuario(uid, "abogado")
                Clock.schedule_once(
                    lambda dt, ud=user_data, cons=consultas: self._aplicar_panel_cargado(ud, cons),
                    0
                )
            except Exception as e:
                print(f"ERROR cargar_panel abogado: {e}")
                Clock.schedule_once(lambda dt: self._finalizar_carga_panel(), 0)

        threading.Thread(target=_worker, daemon=True).start()

    def _aplicar_panel_cargado(self, user_data, consultas):
        session.current_user = user_data
        session.guardar()

        nombre = _normalizar_texto_persona(
            user_data.get("username") or user_data.get("nombre") or user_data.get("email", "")
        )
        estado = user_data.get("estado_abogado", "disponible") or "disponible"
        saldo = user_data.get("saldo", 0) or 0

        self.ids.lbl_nombre_abogado.text = nombre
        if "img_avatar_abogado" in self.ids:
            set_avatar_image(
                self.ids.img_avatar_abogado,
                user_data.get("foto_url", ""),
                user_data.get("email", "")
            )
        self._aplicar_estado_boton(estado)

        try:
            from kivy.utils import platform
            if platform == "android":
                from fcm_service import obtener_fcm_token
                Clock.schedule_once(lambda dt: obtener_fcm_token(), 1)
        except Exception as e:
            print(f"Error refrescando FCM abogado: {e}")

        self._consultas = []
        for cid, cdata in consultas:
            cdata["id"] = cid
            self._consultas.append(cdata)

        activas = [c for c in self._consultas if c.get("estado") in ["pagado", "en_curso", "videollamada"]]
        self.ids.lbl_consultas.text = str(len(activas))
        self.ids.lbl_honorarios.text = f"${saldo:,.0f}"

        self._actualizar_filtros()
        self._render_consultas()
        self._finalizar_carga_panel()

    def _finalizar_carga_panel(self):
        self._cargando_panel = False

    def _aplicar_estado_boton(self, estado):
        self.ids.btn_estado.text = estado.upper()
        if estado == "disponible":
            self.ids.btn_estado.background_color = (0.18, 0.80, 0.44, 1)
        elif estado == "guardia":
            self.ids.btn_estado.background_color = (0.95, 0.65, 0.10, 1)
        else:
            self.ids.btn_estado.background_color = (0.90, 0.25, 0.25, 1)

    def cambiar_estado(self):
        user = session.current_user
        if not user:
            return

        estado_actual = user.get("estado_abogado", "disponible") or "disponible"
        nuevo = {
            "disponible": "guardia",
            "guardia": "ocupado",
            "ocupado": "disponible",
        }.get(estado_actual, "disponible")

        if fb.actualizar_usuario(user.get("uid"), {"estado_abogado": nuevo}):
            user["estado_abogado"] = nuevo
            session.current_user = user
            session.guardar()
            self._aplicar_estado_boton(nuevo)

    def filtrar(self, filtro):
        self._filtro = filtro
        self._actualizar_filtros()
        self._render_consultas()

    def _actualizar_filtros(self):
        botones = {
            "todas": self.ids.filtro_todas,
            "activas": self.ids.filtro_activas,
            "finalizadas": self.ids.filtro_finalizadas,
            "chat": self.ids.filtro_chat,
            "video": self.ids.filtro_video,
            "urgente": self.ids.filtro_urgente,
        }
        for clave, btn in botones.items():
            activo = clave == self._filtro
            btn.background_color = (0.24, 0.17, 0.55, 1) if activo else (0.90, 0.90, 0.96, 1)
            btn.color = (1, 1, 1, 1) if activo else (0.24, 0.17, 0.55, 1)

    def _render_consultas(self):
        lista = self.ids.lista_consultas
        lista.clear_widgets()

        filtro_fn = FILTROS.get(self._filtro, FILTROS["todas"])
        consultas = [c for c in self._consultas if filtro_fn(c)]

        if not consultas:
            lista.add_widget(Label(
                text="No hay consultas",
                size_hint_y=None,
                height=dp(70),
                font_size=sp(15),
                color=COLOR_MUTED,
            ))
            return

        for consulta in consultas:
            lista.add_widget(self._crear_card_consulta(consulta))

    def _crear_card_consulta(self, consulta):
        estado = consulta.get("estado", "pendiente")
        tipo = consulta.get("tipo_servicio", "chat")
        cliente = _normalizar_texto_persona(
            consulta.get("cliente_nombre")
            or consulta.get("cliente_username")
            or consulta.get("cliente_email", "Cliente")
        )
        monto = consulta.get("monto", 0) or 0
        consulta_id = consulta.get("id")

        card = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(126),
            padding=[dp(14), dp(12)],
            spacing=dp(10),
        )

        with card.canvas.before:
            Color(rgba=(0, 0, 0, 0.07))
            card._shadow = RoundedRectangle(pos=(card.x, card.y - dp(3)), size=card.size, radius=[dp(18)])
            Color(rgba=(1, 1, 1, 1))
            card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(18)])

        card.bind(
            pos=lambda w, v: (setattr(w._shadow, "pos", (v[0], v[1] - dp(3))), setattr(w._bg, "pos", v)),
            size=lambda w, v: (setattr(w._shadow, "size", v), setattr(w._bg, "size", v)),
        )

        info = BoxLayout(orientation="vertical", spacing=dp(3))
        for text, size, color, bold in [
            (cliente, 14, COLOR_TEXTO, True),
            (f"{tipo.upper()} - {estado.upper()}", 12, COLOR_MUTED, True),
            (f"Monto: ${monto:,.0f}", 12, COLOR_MUTED, False),
        ]:
            lbl = Label(
                text=text,
                font_size=sp(size),
                bold=bold,
                color=color,
                halign="left",
                valign="top",
                size_hint_y=None,
            )
            if bold and size == 14:
                lbl.height = dp(42)
                lbl.bind(size=lambda s, *_: setattr(s, "text_size", (s.width, None)))
            else:
                lbl.height = dp(22)
                lbl.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
            info.add_widget(lbl)

        acciones = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(96), spacing=dp(6))

        if estado == "pagado":
            btn_aceptar = Button(
                text="Aceptar",
                size_hint_y=None,
                height=dp(38),
                font_size=sp(12),
                bold=True,
                background_normal="",
                background_color=(0.18, 0.80, 0.44, 1),
                color=(1, 1, 1, 1),
            )
            btn_aceptar.bind(on_release=partial(self._aceptar_consulta, consulta_id))
            acciones.add_widget(btn_aceptar)

        btn_abrir = Button(
            text="Abrir",
            size_hint_y=None,
            height=dp(38),
            font_size=sp(12),
            bold=True,
            background_normal="",
            background_color=(0.30, 0.23, 0.67, 1),
            color=(1, 1, 1, 1),
        )
        btn_abrir.bind(on_release=partial(self._abrir_consulta, consulta_id))
        acciones.add_widget(btn_abrir)

        card.add_widget(info)
        card.add_widget(acciones)
        return card

    def _aceptar_consulta(self, consulta_id, instance):
        if not consulta_id:
            return
        consulta = fb.obtener_consulta(consulta_id)
        if not consulta:
            return
        fb.actualizar_estado_consulta(consulta_id, "en_curso")
        cliente_uid = consulta.get("cliente_uid")
        if cliente_uid:
            fb.notificar_consulta_aceptada(cliente_uid, consulta.get("tipo_servicio", "chat"), consulta_id)
        self.cargar_panel()

    def _abrir_consulta(self, consulta_id, instance):
        if not consulta_id:
            return
        session.current_consulta_id = consulta_id
        session.guardar()
        consulta = fb.obtener_consulta(consulta_id) or {}
        if consulta.get("tipo_servicio") == "video" and consulta.get("estado") == "videollamada":
            self.manager.current = "videollamada"
        else:
            self.manager.current = "chat"

    def solicitar_retiro_popup(self):
        user = session.current_user
        if not user:
            return

        saldo = user.get("saldo", 0) or 0
        cuenta_guardada = str(user.get("cuenta_bancaria", "") or "").strip()
        layout = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))

        info = Label(
            text=f"Saldo disponible: ${saldo:,.0f}",
            font_size=sp(14),
            color=COLOR_TEXTO,
            size_hint_y=None,
            height=dp(32),
        )
        cuenta = TextInput(
            hint_text="CBU / Alias / Cuenta destino",
            text=cuenta_guardada,
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            font_size=sp(14),
        )
        monto = TextInput(
            hint_text="Monto a retirar",
            text=str(int(saldo)) if saldo else "",
            input_filter="int",
            multiline=False,
            size_hint_y=None,
            height=dp(48),
            font_size=sp(14),
        )
        error = Label(text="", color=(0.90, 0.25, 0.25, 1), font_size=sp(12), size_hint_y=None, height=dp(24))
        btn = Button(text="Solicitar retiro", size_hint_y=None, height=dp(48), bold=True)

        layout.add_widget(info)
        layout.add_widget(cuenta)
        layout.add_widget(monto)
        layout.add_widget(error)
        layout.add_widget(btn)

        popup = Popup(title="Retirar honorarios", content=layout, size_hint=(0.88, None), height=dp(360))

        def _solicitar(instance):
            try:
                monto_valor = int(monto.text or "0")
            except Exception:
                monto_valor = 0
            if not cuenta.text.strip():
                error.text = "Ingresa cuenta destino"
                return
            ok, mensaje, _ = fb.solicitar_retiro(user.get("uid"), monto_valor, cuenta.text.strip())
            if ok:
                popup.dismiss()
                self.cargar_panel()
            else:
                error.text = mensaje

        btn.bind(on_release=_solicitar)
        popup.open()

    def ver_notificaciones(self):
        layout = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        with layout.canvas.before:
            from kivy.graphics import Rectangle
            Color(1, 1, 1, 1)
            layout._bg = Rectangle(pos=layout.pos, size=layout.size)
        layout.bind(
            pos=lambda w, v: setattr(w._bg, "pos", v),
            size=lambda w, v: setattr(w._bg, "size", v),
        )
        titulo = Label(
            text="Avisos recientes",
            size_hint_y=None,
            height=dp(26),
            bold=True,
            font_size=sp(16),
            color=(0.18, 0.12, 0.40, 1),
        )
        layout.add_widget(titulo)

        scroll = ScrollView(do_scroll_x=False)
        contenido = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8), padding=[dp(2), dp(2)])
        contenido.bind(minimum_height=contenido.setter("height"))

        consultas = self._consultas[:8]
        if not consultas:
            lbl = Label(
                text="No hay notificaciones por ahora.",
                size_hint_y=None,
                height=dp(56),
                font_size=sp(13),
                color=COLOR_MUTED,
                halign="center",
                valign="middle",
            )
            lbl.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
            contenido.add_widget(lbl)
        else:
            for consulta in consultas:
                cliente = consulta.get("cliente_email", "Cliente")
                tipo = str(consulta.get("tipo_servicio", "chat") or "chat").upper()
                estado = str(consulta.get("estado", "pendiente") or "pendiente").replace("_", " ").upper()
                lbl = Label(
                    text=f"{tipo} - {estado}\n{cliente}",
                    size_hint_y=None,
                    height=dp(56),
                    font_size=sp(12),
                    color=COLOR_TEXTO,
                    halign="left",
                    valign="middle",
                )
                lbl.bind(size=lambda s, *_: setattr(s, "text_size", (s.width, None)))
                contenido.add_widget(lbl)

                mensajes = fb.obtener_mensajes(consulta.get("id"))
                if mensajes:
                    ultimo = mensajes[-1]
                    texto = str(ultimo.get("texto") or "").strip()
                    if texto:
                        preview = texto[:44] + "..." if len(texto) > 44 else texto
                        msg = Label(
                            text=f"Mensaje reciente\n{preview}",
                            size_hint_y=None,
                            height=dp(52),
                            font_size=sp(11),
                            color=COLOR_MUTED,
                            halign="left",
                            valign="middle",
                        )
                        msg.bind(size=lambda s, *_: setattr(s, "text_size", (s.width, None)))
                        contenido.add_widget(msg)

        scroll.add_widget(contenido)
        layout.add_widget(scroll)

        btn = Button(
            text="Cerrar",
            size_hint_y=None,
            height=dp(44),
            bold=True,
            background_normal="",
            background_color=(0.30, 0.23, 0.67, 1),
            color=(1, 1, 1, 1),
        )
        layout.add_widget(btn)

        popup = Popup(title="Notificaciones", content=layout, size_hint=(0.88, 0.56))
        btn.bind(on_release=popup.dismiss)
        popup.open()

    def ir_perfil(self):
        self.manager.current = "perfil"

    def logout(self):
        session.cerrar_sesion()
        self.manager.current = "login"
