import os
import hashlib
import time
import threading

from kivy.clock import Clock
from kivy.uix.image import AsyncImage
from kivy.graphics import Color, Ellipse, Line
from kivy.properties import ListProperty, NumericProperty

AVATAR_DEFAULT = "assets/avatar_default.png"

# Lado en pixeles al que se redimensiona cualquier avatar antes de mostrarlo
# o guardarlo en cache -- evita cargar fotos de camara a resolucion completa
# (varios MB cada una) solo para mostrarlas en un circulo de 40-100dp. Ver
# project_legalapp_memoria_avatares: la app quedaba matada por el
# lowmemorykiller con varias fotos de abogados sin redimensionar cargadas
# a la vez en la lista.
AVATAR_CACHE_SIZE = 240

_CACHE_DIR = os.path.join("assets", "avatar_cache")
_locks_por_ruta = {}
_locks_lock = threading.Lock()


class CircularAvatar(AsyncImage):
    """AsyncImage recortada en circulo, con un anillo de color alrededor.

    Se usa para el avatar propio en el dashboard (anillo blanco, decorativo)
    y para la foto de cada abogado en la lista (anillo verde/naranja/rojo
    segun disponibilidad -- ver ESTADO_COLOR en views/abogados.py). Reemplaza
    el dibujo por defecto de AsyncImage (un rectangulo con la textura) por
    una Ellipse con la misma textura, asi la foto queda recortada en circulo
    en vez de cuadrada.
    """

    ring_color = ListProperty([1, 1, 1, 1])
    ring_width = NumericProperty(2)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(
            pos=self._redibujar_mascara,
            size=self._redibujar_mascara,
            texture=self._redibujar_mascara,
            ring_color=self._redibujar_mascara,
            ring_width=self._redibujar_mascara,
        )
        self._redibujar_mascara()

    def _redibujar_mascara(self, *args):
        self.canvas.clear()
        with self.canvas:
            if self.texture:
                Color(1, 1, 1, 1)
                Ellipse(texture=self.texture, pos=self.pos, size=self.size)
            Color(*self.ring_color)
            Line(ellipse=(self.x, self.y, self.width, self.height), width=self.ring_width)


def _obtener_lock_para(ruta):
    with _locks_lock:
        lock = _locks_por_ruta.get(ruta)
        if lock is None:
            lock = threading.Lock()
            _locks_por_ruta[ruta] = lock
        return lock


def _avatar_local_por_email(email):
    if not email:
        return None
    safe = str(email).replace("@", "_").replace(".", "_")
    base = os.path.join("assets", "fotos")
    if not os.path.isdir(base):
        return None

    candidatos = []
    prefijo = f"perfil_{safe}".lower()
    for nombre in os.listdir(base):
        nombre_lower = nombre.lower()
        if not nombre_lower.startswith(prefijo):
            continue
        if not any(nombre_lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
            continue
        path = os.path.join(base, nombre)
        if os.path.isfile(path):
            candidatos.append(path)

    if not candidatos:
        return None

    candidatos.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return os.path.abspath(candidatos[0])


def _ruta_cache_redimensionada(ruta_original):
    try:
        mtime = os.path.getmtime(ruta_original)
    except OSError:
        mtime = 0
    clave = f"{ruta_original}|{mtime}|{AVATAR_CACHE_SIZE}"
    nombre_cache = hashlib.md5(clave.encode("utf-8")).hexdigest() + ".jpg"
    return os.path.join(_CACHE_DIR, nombre_cache)


def _redimensionar_a_cache(ruta_original):
    """Devuelve una copia de ruta_original redimensionada a
    AVATAR_CACHE_SIZE x AVATAR_CACHE_SIZE (mantiene aspecto, recorta al
    centro), guardada en disco para no repetir el trabajo. Si algo falla
    (Pillow no disponible, archivo corrupto, etc.) devuelve la ruta
    original tal cual -- nunca bloquea mostrar el avatar por esto."""
    lock = _obtener_lock_para(ruta_original)
    with lock:
        try:
            destino = _ruta_cache_redimensionada(ruta_original)
            if os.path.isfile(destino):
                return destino

            from PIL import Image

            os.makedirs(_CACHE_DIR, exist_ok=True)
            with Image.open(ruta_original) as img:
                img = img.convert("RGB")
                lado = min(img.width, img.height)
                izq = (img.width - lado) // 2
                arriba = (img.height - lado) // 2
                img = img.crop((izq, arriba, izq + lado, arriba + lado))
                img = img.resize((AVATAR_CACHE_SIZE, AVATAR_CACHE_SIZE), Image.LANCZOS)
                tmp = destino + ".tmp"
                img.save(tmp, "JPEG", quality=85)
                os.replace(tmp, destino)
            return destino
        except Exception as e:
            print(f"ERROR redimensionando avatar {ruta_original}: {e}")
            return ruta_original


def _cargar_local_redimensionado(ruta_original):
    return _redimensionar_a_cache(ruta_original)


def _ruta_original_remota(url_base):
    nombre = hashlib.md5(url_base.encode("utf-8")).hexdigest() + "_orig"
    return os.path.join(_CACHE_DIR, nombre)


def _descargar_y_redimensionar_remoto(url_base):
    """Descarga la foto remota una sola vez y la deja redimensionada en
    cache -- devuelve la ruta local ya chica, o None si algo fallo (sin
    conexion, url caida, etc.)."""
    lock = _obtener_lock_para(url_base)
    with lock:
        try:
            ruta_original = _ruta_original_remota(url_base)
            destino = _ruta_cache_redimensionada(ruta_original) if os.path.isfile(ruta_original) else None
            if destino and os.path.isfile(destino):
                return destino

            import requests

            os.makedirs(_CACHE_DIR, exist_ok=True)
            resp = requests.get(url_base, timeout=15)
            resp.raise_for_status()
            with open(ruta_original, "wb") as f:
                f.write(resp.content)
            return _redimensionar_a_cache(ruta_original)
        except Exception as e:
            print("DEBUG AVATAR: error redimensionando remoto:", e)
            return None


def _cargar_remoto_redimensionado(url, widget=None):
    """Las fotos remotas (Supabase Storage) se descargan UNA vez y quedan
    redimensionadas en cache en disco -- si no, AsyncImage decodifica la
    foto a resolucion completa cada vez que se muestra, y con varias fotos
    de abogados en la lista a la vez eso saturaba memoria y hacia que
    Android matara la app (lowmemorykiller, ver
    project_legalapp_memoria_avatares).

    Devuelve la URL original de una para no dejar el avatar en blanco
    mientras se descarga -- si se paso `widget`, ademas dispara la descarga
    en un hilo aparte y reemplaza la source por la version chica en cache
    apenas este lista (en el hilo principal, via Clock)."""
    base = url.split("?")[0]
    ruta_original = _ruta_original_remota(base)
    ya_cacheada = _ruta_cache_redimensionada(ruta_original) if os.path.isfile(ruta_original) else None
    if ya_cacheada and os.path.isfile(ya_cacheada):
        return ya_cacheada

    if widget is not None:
        def _worker():
            destino = _descargar_y_redimensionar_remoto(base)
            if destino:
                Clock.schedule_once(
                    lambda dt: _aplicar_source_si_corresponde(widget, destino, force=True), 0
                )

        threading.Thread(target=_worker, daemon=True).start()

    return url


def _source_con_cache_buster(source):
    """Le agrega un parametro de tiempo a las URLs remotas para forzar una
    recarga real. Sin esto: subir una foto nueva que Supabase guarda en la
    MISMA url que la anterior (reemplaza el archivo, no cambia el nombre)
    hacia que set_avatar_image() viera "la url no cambio" y nunca volviera
    a pedir la imagen -- la foto se subia bien pero la app seguia mostrando
    la vieja sin importar cuantas veces se tocara "Cambiar foto"."""
    if not source or not str(source).startswith(("http://", "https://")):
        return source
    separador = "&" if "?" in source else "?"
    return f"{source}{separador}_cb={int(time.time() * 1000)}"


def _fallback_avatar(email=None):
    local_email = _avatar_local_por_email(email)
    if local_email:
        return _cargar_local_redimensionado(local_email)
    return AVATAR_DEFAULT


def get_avatar_source(foto_path, email=None, widget=None):
    if foto_path and str(foto_path).startswith(("http://", "https://")):
        return _cargar_remoto_redimensionado(str(foto_path), widget=widget)

    if foto_path and os.path.isfile(foto_path):
        return _cargar_local_redimensionado(os.path.abspath(foto_path))

    return _fallback_avatar(email)


def _asegurar_fallback_error(widget, email=None):
    """Si AsyncImage no puede cargar la source (URL caida, archivo
    corrompido), Kivy la deja en blanco -- se cae al avatar por defecto en
    vez de dejar el circulo vacio."""
    try:
        widget.source = _fallback_avatar(email)
        widget.reload()
    except Exception:
        pass


def _aplicar_source_si_corresponde(widget, source, force=False):
    actual = str(getattr(widget, "source", "") or "")
    if not force and actual == source:
        return False
    widget.source = source
    try:
        widget.reload()
    except Exception:
        pass
    return True


def set_avatar_image(widget, foto_path, email=None, force=False):
    """force=True se usa despues de subir una foto nueva -- ahi se sabe que
    hay contenido fresco, asi que se agrega cache-buster a las URLs
    remotas para garantizar que se vea la version nueva y no una vieja
    servida desde cache (del lado de Kivy o de una CDN intermedia)."""
    source = get_avatar_source(foto_path, email, widget=widget)
    if force and str(source).startswith(("http://", "https://")):
        source = _source_con_cache_buster(source)

    aplicado = _aplicar_source_si_corresponde(widget, source, force=force)
    if not aplicado:
        return source

    try:
        widget.bind(on_error=lambda *_: _asegurar_fallback_error(widget, email))
    except Exception:
        pass
    return source
