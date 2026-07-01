from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
import threading
import supabase_config as fb
import session

ESTADOS_FILTRO = ["Todos", "pendiente", "pagado", "en_curso", "videollamada", "finalizado"]

TIPO_COLOR = {
    "chat":    (0.18, 0.80, 0.44, 1),
    "video":   (0.18, 0.55, 0.85, 1),
    "urgente": (0.91, 0.30, 0.24, 1),
}

ESTADO_COLOR = {
    "pendiente":     (0.90, 0.25, 0.25, 1),
    "pagado":        (0.85, 0.62, 0.05, 1),
    "en_curso":      (0.18, 0.80, 0.44, 1),
    "videollamada":  (0.18, 0.55, 0.85, 1),
    "finalizado":    (0.18, 0.80, 0.44, 1),
}

ESTADO_TEXTO = {
    "pendiente": "PENDIENTE DE PAGO",
    "pagado": "PENDIENTE DE APROBACION",
    "en_curso": "EN CURSO",
    "videollamada": "VIDEOLLAMADA",
    "finalizado": "FINALIZADO",
}


class HistorialScreen(Screen):

    _filtro = "Todos"
    _cargando_historial = False

    def on_enter(self):
        self.ids.filtro_spinner.values = ESTADOS_FILTRO
        self.ids.filtro_spinner.text = self._filtro
        self.cargar_historial()

    def aplicar_filtro(self, valor):
        self._filtro = valor
        self.cargar_historial()

    def cargar_historial(self):
        self.ids.lista.clear_widgets()

        if not session.current_user:
            return

        if self._cargando_historial:
            return

        uid = session.current_user.get('uid')
        self._cargando_historial = True

        self.ids.lista.add_widget(Label(
            text="Cargando consultas...",
            color=(0.50, 0.55, 0.65, 1),
            font_size="15sp",
            size_hint_y=None,
            height=dp(70),
        ))

        def _fetch():
            payload = []
            try:
                fb.recuperar_consultas_pagadas_cliente(uid)
                consultas = fb.obtener_consultas_usuario(uid, 'cliente')

                if self._filtro != "Todos":
                    consultas = [(cid, c) for cid, c in consultas if c.get('estado') == self._filtro]

                for cid, cdata in consultas:
                    estado = cdata.get('estado', 'pagado')
                    payload.append({
                        "cid": cid,
                        "abogado_email": cdata.get('abogado_email', ''),
                        "estado": estado,
                        "tipo": cdata.get('tipo_servicio', 'chat'),
                        "tiene_resena": fb.tiene_resena(cid) if estado == "finalizado" else True,
                    })
            except Exception as e:
                print(f"ERROR cargar_historial: {e}")
                payload = None
            finally:
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt, data=payload: self._aplicar_historial(data), 0)

        threading.Thread(target=_fetch, daemon=True).start()

    def _aplicar_historial(self, payload):
        self._cargando_historial = False
        self.ids.lista.clear_widgets()

        if payload is None:
            self.ids.lista.add_widget(Label(
                text="Error cargando consultas",
                color=(0.90, 0.25, 0.25, 1),
                font_size="15sp",
                size_hint_y=None,
                height=dp(70),
            ))
            return

        if not payload:
            self.ids.lista.add_widget(Label(
                text="No hay consultas",
                color=(0.50, 0.55, 0.65, 1),
                font_size="15sp",
                size_hint_y=None,
                height=dp(70),
            ))
            return

        for item in payload:
            self._add_card(
                item["cid"],
                item["abogado_email"],
                item["estado"],
                item["tipo"],
                item["tiene_resena"],
            )

    def _add_card(self, cid, abogado, estado, tipo, tiene_resena=True):
        card = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(112),
            spacing=dp(12),
            padding=[dp(14), dp(12)],
        )

        with card.canvas.before:
            Color(rgba=(1, 1, 1, 1))
            card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(18)])

        card.bind(
            pos=lambda w, v: setattr(w._bg, 'pos', v),
            size=lambda w, v: setattr(w._bg, 'size', v),
        )

        tipo_box = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(72))
        tipo_lbl = Label(
            text=tipo.upper(),
            font_size="12sp",
            bold=True,
            color=TIPO_COLOR.get(tipo, (0.5, 0.5, 0.5, 1)),
            halign="center",
            valign="middle",
        )
        tipo_lbl.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
        tipo_box.add_widget(tipo_lbl)

        info = BoxLayout(orientation="vertical", spacing=dp(4))

        abogado_lbl = Label(
            text=abogado,
            font_size="15sp",
            bold=True,
            color=(0.10, 0.12, 0.18, 1),
            halign="left",
            valign="middle",
        )
        abogado_lbl.bind(size=lambda s, *_: setattr(s, "text_size", s.size))

        estado_lbl = Label(
            text=ESTADO_TEXTO.get(estado, estado.upper()),
            font_size="12sp",
            bold=True,
            color=ESTADO_COLOR.get(estado, (0.55, 0.58, 0.65, 1)),
            halign="left",
            valign="middle",
        )
        estado_lbl.bind(size=lambda s, *_: setattr(s, "text_size", s.size))

        info.add_widget(abogado_lbl)
        info.add_widget(estado_lbl)

        btns = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(90), spacing=dp(6))

        btn_chat = Button(
            text="Pagar" if estado == "pendiente" else "Abrir",
            font_size="13sp",
            bold=True,
            size_hint_y=None,
            height=dp(40),
            background_normal="",
            background_color=(0.02, 0.58, 0.86, 1) if estado == "pendiente" else (0.24, 0.17, 0.55, 1),
            color=(1, 1, 1, 1),
        )
        if estado == "pendiente":
            btn_chat.bind(on_release=lambda x, c=cid: self.ir_pagar(c))
        else:
            btn_chat.bind(on_release=lambda x, c=cid: self.abrir_chat(c))
        btns.add_widget(btn_chat)

        if estado == "finalizado" and not tiene_resena:
            btn_resena = Button(
                text="Reseña",
                font_size="12sp",
                bold=True,
                size_hint_y=None,
                height=dp(36),
                background_normal="",
                background_color=(0.91, 0.30, 0.24, 1),
                color=(1, 1, 1, 1),
            )
            btn_resena.bind(on_release=lambda x, c=cid: self.ir_resena(c))
            btns.add_widget(btn_resena)

        card.add_widget(tipo_box)
        card.add_widget(info)
        card.add_widget(btns)

        self.ids.lista.add_widget(card)

    def abrir_chat(self, cid):
        session.current_consulta_id = cid
        session.guardar()
        consulta = fb.obtener_consulta(cid) or {}
        estado = str(consulta.get("estado") or "")
        tipo = consulta.get("tipo_servicio", "chat") or "chat"
        video_iniciado = (
            tipo == "video"
            and estado in ["en_curso", "videollamada"]
            and fb.consulta_tiene_videollamada_iniciada(cid)
        )

        if estado == "videollamada" or video_iniciado:
            self.manager.current = "videollamada"
        else:
            self.manager.current = "chat"

    def ir_pagar(self, cid):
        consulta = fb.obtener_consulta(cid)
        if not consulta:
            return

        session.current_consulta_id = cid
        session.pago_tipo = "consulta"
        session.tipo_servicio = consulta.get("tipo_servicio", "chat") or "chat"
        session.abogado_seleccionado = consulta.get("abogado_email", "")
        session.pago_pending_abogado_uid = consulta.get("abogado_uid")
        session.pago_pending_abogado_email = consulta.get("abogado_email", "")
        session.pago_pending_cliente_uid = consulta.get("cliente_uid")
        session.pago_pending_cliente_email = consulta.get("cliente_email", "")
        session.pago_pending_precio = consulta.get("monto", 0) or 0
        session.pago_external_reference = consulta.get("external_reference")
        session.pago_preference_id = None
        session.pago_init_point = None
        session.guardar()

        mp_screen = self.manager.get_screen("pago_mp")
        if hasattr(mp_screen, "preparar_pago_consulta"):
            mp_screen.preparar_pago_consulta({
                "abogado_uid": consulta.get("abogado_uid"),
                "abogado_email": consulta.get("abogado_email", ""),
                "cliente_uid": consulta.get("cliente_uid"),
                "cliente_email": consulta.get("cliente_email", ""),
                "tipo_servicio": consulta.get("tipo_servicio", "chat") or "chat",
                "monto": consulta.get("monto", 0) or 0,
                "area": consulta.get("area", "") or "",
            })

        self.manager.current = "pago_mp"

    def ir_resena(self, cid):
        session.current_consulta_id = cid
        self.manager.current = "resena"

    def volver(self):
        self.manager.current = "dashboard"
