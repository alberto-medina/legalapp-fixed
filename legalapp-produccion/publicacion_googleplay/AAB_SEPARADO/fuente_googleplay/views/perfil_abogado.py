import json
import threading

from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.core.window import Window
from kivy.resources import resource_find

import supabase_config as fb
import session
from views.perfil_common import PerfilBaseMixin

RATING_FONT = resource_find("data/fonts/DejaVuSans.ttf") or "data/fonts/DejaVuSans.ttf"


def _rating_text(puntaje):
    try:
        valor = max(0, min(5, int(round(float(puntaje or 0)))))
    except Exception:
        valor = 0
    return "★" * valor + "☆" * (5 - valor)


def _fecha_resena(fecha):
    texto = str(fecha or "")
    if "T" in texto:
        return texto.split("T", 1)[0]
    return texto[:10]


class PerfilAbogadoScreen(PerfilBaseMixin, Screen):

    _precio_especialidad_extra = 10000

    def _aplicar_datos_rol(self, user_data):
        self.ids.lbl_rol_badge.text = "ABOGADO / A"
        self.ids.lbl_rol_badge.color = (1, 1, 1, 1)

        self.ids.matricula.text = user_data.get('matricula', '') or ""
        self.ids.experiencia.text = user_data.get('experiencia', '') or ""
        self.ids.descripcion.text = user_data.get('descripcion', '') or ""
        self.ids.cuenta_bancaria.text = user_data.get('cuenta_bancaria', '') or ""
        self.ids.provincia.text = user_data.get('provincia', '') or ""
        self.ids.ciudad.text = user_data.get('ciudad', '') or ""

        especialidades_raw = user_data.get('especialidades', '[]') or '[]'
        try:
            especialidades = json.loads(especialidades_raw) if isinstance(especialidades_raw, str) else especialidades_raw
        except Exception:
            especialidades = []
        self.ids.lbl_especialidades.text = ", ".join(especialidades) if especialidades else "Sin especialidades cargadas"
        self._actualizar_boton_especialidad(especialidades)

        suscripcion_activa = user_data.get('suscripcion_activa', False)
        suscripcion_fecha = user_data.get('suscripcion_fecha', '')
        suscripcion_monto = user_data.get('suscripcion_monto', 0)
        if suscripcion_activa:
            fecha_str = str(suscripcion_fecha)[:10] if suscripcion_fecha else "-"
            self.ids.lbl_suscripcion.text = f"Activa desde {fecha_str} — ${suscripcion_monto:,.0f}"
            self.ids.lbl_suscripcion.color = (0.18, 0.80, 0.44, 1)
        else:
            self.ids.lbl_suscripcion.text = "Inactiva"
            self.ids.lbl_suscripcion.color = (0.90, 0.25, 0.25, 1)

        self._cargar_resenas(user_data.get('email', ''))

    def _datos_extra_guardar(self):
        return {
            'matricula': self.ids.matricula.text.strip(),
            'experiencia': self.ids.experiencia.text.strip(),
            'descripcion': self.ids.descripcion.text.strip(),
            'cuenta_bancaria': self.ids.cuenta_bancaria.text.strip(),
            'provincia': self.ids.provincia.text.strip(),
            'ciudad': self.ids.ciudad.text.strip(),
        }

    def _actualizar_boton_especialidad(self, actuales):
        from views.register_abogado import ESPECIALIDADES
        disponibles = [e for e in ESPECIALIDADES if e not in actuales]
        precio_extra = getattr(self, "_precio_especialidad_extra", 10000)

        if disponibles:
            self.ids.btn_agregar_especialidad.text = f"+ Agregar especialidad (${precio_extra:,})"
            self.ids.btn_agregar_especialidad.disabled = False
            self.ids.btn_agregar_especialidad.opacity = 1
        else:
            self.ids.btn_agregar_especialidad.text = "Todas las especialidades activas"
            self.ids.btn_agregar_especialidad.disabled = True
            self.ids.btn_agregar_especialidad.opacity = 0.5

    def agregar_especialidad(self):
        from views.register_abogado import ESPECIALIDADES

        user_data = fb.obtener_usuario(session.get_uid())
        especialidades_raw = user_data.get('especialidades', '[]') or '[]'
        try:
            actuales = json.loads(especialidades_raw) if isinstance(especialidades_raw, str) else especialidades_raw
        except Exception:
            actuales = []

        disponibles = [e for e in ESPECIALIDADES if e not in actuales]
        if not disponibles:
            self._mostrar_error("Ya tenes todas las especialidades disponibles")
            return

        config = fb.obtener_configuracion() or {}
        try:
            precio_extra = int(config.get("precio_especialidad_extra", 10000))
        except Exception:
            precio_extra = 10000

        layout = BoxLayout(
            orientation='vertical',
            padding=[dp(14), dp(12), dp(14), dp(12)],
            spacing=dp(10)
        )
        layout.add_widget(Label(
            text='Selecciona especialidades a agregar:',
            size_hint_y=None,
            height=dp(42),
            font_size='14sp',
            bold=True,
            color=(0.23, 0.18, 0.55, 1),
            halign='center',
            valign='middle',
            text_size=(Window.width * 0.72, None),
        ))

        grid = GridLayout(cols=1, spacing=dp(6), size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        seleccion = []
        lbl_precio = Label(
            text=f'Precio: ${precio_extra:,}',
            size_hint_y=None,
            height=dp(34),
            font_size='14sp',
            color=(0.18, 0.80, 0.44, 1),
            bold=True,
            halign='center',
            valign='middle',
            text_size=(Window.width * 0.72, None),
        )

        def on_select(btn, esp):
            if btn.state == 'down':
                if esp not in seleccion:
                    seleccion.append(esp)
            else:
                if esp in seleccion:
                    seleccion.remove(esp)

            total = max(1, len(seleccion)) * precio_extra
            if len(seleccion) <= 1:
                lbl_precio.text = f'Precio: ${total:,}'
            else:
                lbl_precio.text = f'Precio: ${total:,} ({len(seleccion)} especialidades)'

        def _estilizar_toggle(btn, *args):
            if btn.state == 'down':
                btn.background_color = (0.18, 0.80, 0.44, 1)
                btn.color = (1, 1, 1, 1)
                btn.bold = True
            else:
                btn.background_color = (0.23, 0.18, 0.55, 1)
                btn.color = (1, 1, 1, 1)
                btn.bold = False

        for esp in disponibles:
            btn = ToggleButton(
                text=esp,
                size_hint_y=None,
                height=dp(42),
                font_size='13sp',
                background_normal='',
                background_down='',
                background_color=(0.23, 0.18, 0.55, 1),
                color=(1, 1, 1, 1),
            )
            btn.bind(on_release=lambda x, e=esp: on_select(x, e))
            btn.bind(state=lambda instance, value: _estilizar_toggle(instance))
            _estilizar_toggle(btn)
            grid.add_widget(btn)

        scroll = ScrollView(
            size_hint=(1, None),
            height=dp(230),
            do_scroll_x=False,
            bar_width=dp(4),
        )
        scroll.add_widget(grid)
        layout.add_widget(scroll)

        layout.add_widget(lbl_precio)

        btn_box = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        btn_cancelar = Button(
            text='Cancelar',
            font_size='12sp',
            background_color=(0.55, 0.55, 0.55, 1),
            color=(1, 1, 1, 1)
        )
        btn_pagar = Button(
            text='Pagar',
            font_size='12sp',
            background_color=(0.00, 0.55, 0.88, 1),
            color=(1, 1, 1, 1),
            bold=True
        )

        btn_box.add_widget(btn_cancelar)
        btn_box.add_widget(btn_pagar)
        layout.add_widget(btn_box)

        popup = Popup(
            title='Agregar Especialidad',
            content=layout,
            size_hint=(0.92, None),
            height=dp(470),
        )

        def cancelar(instance):
            popup.dismiss()

        def pagar(instance):
            if not seleccion:
                self._mostrar_error("Selecciona al menos una especialidad")
                return
            popup.dismiss()
            session.pago_tipo = 'especialidad_extra'
            session.pago_monto = len(seleccion) * precio_extra
            session.especialidad_a_agregar = list(seleccion)
            session.especialidades_actuales = actuales
            session.current_consulta_id = None
            session.guardar()
            self.manager.current = 'pago_mp'

        btn_cancelar.bind(on_release=cancelar)
        btn_pagar.bind(on_release=pagar)
        popup.open()

    def _cargar_resenas(self, email_abogado):
        box = self.ids.resenas_box
        box.clear_widgets()
        self.ids.lbl_promedio.text = "Cargando reseñas..."

        def _fetch():
            payload = {"resenas": [], "precio_extra": 10000}
            try:
                config = fb.obtener_configuracion() or {}
                try:
                    payload["precio_extra"] = int(config.get("precio_especialidad_extra", 10000))
                except Exception:
                    payload["precio_extra"] = 10000
                payload["resenas"] = fb.obtener_resenas_abogado(email_abogado) or []
            except Exception as e:
                print(f"ERROR cargar reseñas perfil: {e}")
            finally:
                Clock.schedule_once(lambda dt, data=payload: self._aplicar_resenas(data), 0)

        threading.Thread(target=_fetch, daemon=True).start()

    def _aplicar_resenas(self, payload):
        box = self.ids.resenas_box
        box.clear_widgets()

        self._precio_especialidad_extra = int((payload or {}).get("precio_extra", 10000) or 10000)
        user_data = session.current_user or {}
        especialidades_raw = user_data.get('especialidades', '[]') or '[]'
        try:
            especialidades = json.loads(especialidades_raw) if isinstance(especialidades_raw, str) else especialidades_raw
        except Exception:
            especialidades = []
        self._actualizar_boton_especialidad(especialidades)

        resenas = (payload or {}).get("resenas") or []
        total = len(resenas)
        promedio = sum(r.get('puntaje', 0) for r in resenas) / total if total > 0 else 0
        self.ids.lbl_promedio.font_name = RATING_FONT
        self.ids.lbl_promedio.text = f"{_rating_text(promedio)}\n{promedio:.1f}/5 ({total} resenas)"

        if not resenas:
            box.add_widget(Label(
                text="Sin resenas aun",
                color=(0.55, 0.58, 0.65, 1),
                size_hint_y=None,
                height=dp(36),
                font_size="14sp",
            ))
            return

        for rdata in resenas:
            puntaje = rdata.get('puntaje', 0)
            comentario = rdata.get('comentario', '')
            fecha = rdata.get('fecha', '')

            card = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                padding=[dp(14), dp(8)],
                spacing=dp(2),
            )

            with card.canvas.before:
                Color(rgba=(0, 0, 0, 0.07))
                card._shadow = RoundedRectangle(pos=(card.x, card.y - dp(3)), size=card.size, radius=[dp(10)])
                Color(rgba=(0.97, 0.98, 1.0, 1))
                card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(10)])

            card.bind(
                pos=lambda w, v: (setattr(w._shadow, "pos", (v[0], v[1] - dp(3))), setattr(w._bg, "pos", v)),
                size=lambda w, v: (setattr(w._shadow, "size", v), setattr(w._bg, "size", v)),
            )
            rating_lbl = Label(
                text=f"{_rating_text(puntaje)}  {_fecha_resena(fecha)}",
                font_name=RATING_FONT,
                font_size="13sp",
                bold=True,
                color=(0.80, 0.55, 0.05, 1),
                halign="left",
                valign="middle",
                size_hint_y=None,
            )
            rating_lbl.bind(
                width=lambda s, v: setattr(s, "text_size", (v, None)),
                texture_size=lambda s, v: setattr(s, "height", max(dp(20), v[1])),
            )
            card.add_widget(rating_lbl)

            if comentario:
                comentario_lbl = Label(
                    text=f'"{comentario}"',
                    font_size="12sp",
                    color=(0.35, 0.40, 0.52, 1),
                    halign="left",
                    valign="middle",
                    size_hint_y=None,
                )
                comentario_lbl.bind(
                    width=lambda s, v: setattr(s, "text_size", (v, None)),
                    texture_size=lambda s, v: setattr(s, "height", v[1]),
                )
                card.add_widget(comentario_lbl)

            card.bind(minimum_height=card.setter("height"))
            box.add_widget(card)

    def volver(self):
        self.manager.current = "abogado_panel"
