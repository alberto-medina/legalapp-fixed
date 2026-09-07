"""Helper para popups con el estilo visual de la app (tarjeta blanca
redondeada + cabecera violeta) en vez del popup gris oscuro por defecto
de Kivy. Usado por el retiro de honorarios y el selector de
provincia/ciudad (compartido entre cliente y abogado)."""

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp

COLOR_FONDO = (0.96, 0.95, 0.98, 1)
COLOR_HEADER = (0.24, 0.17, 0.55, 1)


def popup_estilizado(titulo, contenido, size_hint=(0.88, None), height=None, **extra):
    raiz = BoxLayout(orientation="vertical")
    with raiz.canvas.before:
        Color(*COLOR_FONDO)
        fondo = RoundedRectangle(pos=raiz.pos, size=raiz.size, radius=[dp(18)])
    raiz.bind(
        pos=lambda w, v: setattr(fondo, "pos", v),
        size=lambda w, v: setattr(fondo, "size", v),
    )

    cabecera = BoxLayout(size_hint_y=None, height=dp(52), padding=(dp(18), 0))
    with cabecera.canvas.before:
        Color(*COLOR_HEADER)
        fondo_cab = RoundedRectangle(
            pos=cabecera.pos, size=cabecera.size, radius=[dp(18), dp(18), 0, 0]
        )
    cabecera.bind(
        pos=lambda w, v: setattr(fondo_cab, "pos", v),
        size=lambda w, v: setattr(fondo_cab, "size", v),
    )
    cabecera.add_widget(Label(text=titulo, bold=True, color=(1, 1, 1, 1), font_size=sp(16)))

    cuerpo = BoxLayout(orientation="vertical", padding=dp(18), spacing=dp(10))
    cuerpo.add_widget(contenido)

    raiz.add_widget(cabecera)
    raiz.add_widget(cuerpo)

    kwargs = dict(
        title="",
        title_size=0,
        separator_height=0,
        background="",
        background_color=(0, 0, 0, 0),
        content=raiz,
        size_hint=size_hint,
    )
    if height is not None:
        kwargs["size_hint_y"] = None
        kwargs["height"] = height
    kwargs.update(extra)
    return Popup(**kwargs)


def input_estilizado(**kwargs):
    """TextInput con el mismo estilo (fondo gris claro, cursor violeta)
    que se usa en el resto de la app, para no repetirlo en cada popup."""
    from kivy.uix.textinput import TextInput

    base = dict(
        multiline=False,
        background_normal="",
        background_active="",
        background_color=(0.95, 0.94, 0.97, 1),
        foreground_color=(0.10, 0.06, 0.14, 1),
        hint_text_color=(0.60, 0.57, 0.68, 1),
        cursor_color=(0.30, 0.23, 0.67, 1),
        padding=[dp(14), dp(12)],
        font_size=sp(14),
        size_hint_y=None,
        height=dp(48),
    )
    base.update(kwargs)
    return TextInput(**base)


def boton_estilizado(fill_color=(0.30, 0.23, 0.67, 1), **kwargs):
    """Button solido con esquinas redondeadas, mismo estilo que los
    botones principales del resto de la app. Violeta por defecto (accion
    primaria); pasar `fill_color` para un secundario (ej. "Cerrar")."""
    from kivy.uix.button import Button
    from kivy.graphics import Color as _Color, RoundedRectangle as _RR

    base = dict(
        bold=True,
        background_normal="",
        background_color=(0, 0, 0, 0),
        color=(1, 1, 1, 1),
        size_hint_y=None,
        height=dp(48),
        font_size=sp(15),
    )
    base.update(kwargs)
    btn = Button(**base)
    with btn.canvas.before:
        _Color(*fill_color)
        fondo = _RR(pos=btn.pos, size=btn.size, radius=[dp(12)])
    btn.bind(
        pos=lambda w, v: setattr(fondo, "pos", v),
        size=lambda w, v: setattr(fondo, "size", v),
    )
    return btn
