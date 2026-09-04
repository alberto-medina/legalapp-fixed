import os
import time
import shutil
import threading
import mimetypes
from datetime import datetime
from urllib.parse import unquote

from kivy.clock import Clock
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import AsyncImage
from kivy.uix.camera import Camera
from kivy.uix.popup import Popup
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.utils import platform

import supabase_config as fb
import session
from views.utils_avatar import get_avatar_source, set_avatar_image

try:
    from plyer import filechooser, camera
    PLYER_OK = True
except Exception:
    camera = None
    PLYER_OK = False

UPLOAD_DIR = "assets/uploads"

BUBBLE_W_DESKTOP = 420
BUBBLE_W_MOBILE = 260

# Limite de tamano para archivos del chat.
MAX_FILE_SIZE_MB = 50
EXTENSIONES_CHAT = {
    ".pdf",
    ".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif",
    ".doc", ".docx",
    ".mp4", ".mov", ".m4v", ".3gp", ".webm",
    ".mp3", ".m4a", ".aac", ".wav", ".ogg", ".opus",
}


def _chat_upload_dir():
    try:
        app = App.get_running_app()
        if app and app.user_data_dir:
            return os.path.join(app.user_data_dir, "chat_uploads")
    except Exception:
        pass
    return UPLOAD_DIR


def _limpiar_nombre_archivo(nombre):
    nombre = unquote(str(nombre or "")).replace("\\", "/").split("/")[-1]
    nombre = nombre.split("?")[0].split("#")[0].strip()
    if not nombre:
        nombre = "archivo"

    seguro = []
    for char in nombre:
        if char.isalnum() or char in "._-":
            seguro.append(char)
        else:
            seguro.append("_")

    nombre = "".join(seguro).strip("._") or "archivo"
    if "." not in nombre:
        nombre += ".bin"
    return nombre


def _nombre_desde_url(url):
    nombre = str(url or "").split("?")[0].split("#")[0].rstrip("/").split("/")[-1]
    return _limpiar_nombre_archivo(nombre or "archivo")


def _nombre_corto_archivo(nombre, max_chars=34):
    nombre = str(nombre or "archivo")
    if len(nombre) <= max_chars:
        return nombre
    base, ext = os.path.splitext(nombre)
    espacio_base = max(8, max_chars - len(ext) - 3)
    return f"{base[:espacio_base]}...{ext}"


def _mime_desde_nombre(nombre):
    ext = os.path.splitext(str(nombre or ""))[1].lower()
    if ext == ".pdf":
        return "application/pdf"
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    if ext in [".heic", ".heif"]:
        return "image/*"
    if ext == ".doc":
        return "application/msword"
    if ext == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if ext in [".mp4", ".m4v"]:
        return "video/mp4"
    if ext == ".mov":
        return "video/quicktime"
    if ext == ".3gp":
        return "video/3gpp"
    if ext == ".webm":
        return "video/webm"
    if ext == ".mp3":
        return "audio/mpeg"
    if ext in [".m4a", ".aac"]:
        return "audio/mp4"
    if ext == ".wav":
        return "audio/wav"
    if ext in [".ogg", ".opus"]:
        return "audio/ogg"
    return mimetypes.guess_type(str(nombre or ""))[0] or "*/*"


def _es_imagen(nombre_o_url):
    ext = os.path.splitext(str(nombre_o_url or "").split("?")[0].lower())[1]
    return ext in [".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif"]


def _es_video(nombre_o_url):
    ext = os.path.splitext(str(nombre_o_url or "").split("?")[0].lower())[1]
    return ext in [".mp4", ".mov", ".m4v", ".3gp", ".webm"]


def _es_audio(nombre_o_url):
    ext = os.path.splitext(str(nombre_o_url or "").split("?")[0].lower())[1]
    return ext in [".mp3", ".m4a", ".aac", ".wav", ".ogg", ".opus"]


def _es_pdf(nombre_o_url):
    ext = os.path.splitext(str(nombre_o_url or "").split("?")[0].lower())[1]
    return ext == ".pdf"


def _etiqueta_archivo(nombre_o_url):
    ext = os.path.splitext(str(nombre_o_url or "").split("?")[0].lower())[1]
    if _es_imagen(nombre_o_url):
        return "Imagen"
    if _es_video(nombre_o_url):
        return "Video"
    if _es_audio(nombre_o_url):
        return "Audio"
    if ext == ".pdf":
        return "PDF"
    return "Documento"


def _inferir_extension_archivo(path_local):
    try:
        with open(path_local, "rb") as archivo:
            cabecera = archivo.read(16)
    except Exception:
        return ""

    if cabecera.startswith(b"%PDF"):
        return ".pdf"
    if cabecera.startswith(b"\x89PNG"):
        return ".png"
    if cabecera.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if cabecera[:4] == b"RIFF" and cabecera[8:12] == b"WEBP":
        return ".webp"
    if cabecera.startswith(b"PK\x03\x04"):
        return ".docx"
    if cabecera.startswith(b"\xd0\xcf\x11\xe0"):
        return ".doc"
    return ""


def _normalizar_extension_archivo(path_local, nombre, extension_preferida=""):
    base, ext = os.path.splitext(nombre)
    ext = ext.lower()
    extension_preferida = (extension_preferida or "").lower()

    if ext in EXTENSIONES_CHAT:
        return path_local, nombre

    nueva_ext = extension_preferida if extension_preferida in EXTENSIONES_CHAT else ""
    if not nueva_ext:
        nueva_ext = _inferir_extension_archivo(path_local)

    if not nueva_ext:
        return path_local, nombre

    nuevo_nombre = f"{base}{nueva_ext}"
    nuevo_path = os.path.join(os.path.dirname(path_local), nuevo_nombre)
    if nuevo_path != path_local:
        try:
            os.replace(path_local, nuevo_path)
            return nuevo_path, nuevo_nombre
        except Exception:
            pass

    return path_local, nuevo_nombre


def _nombre_desde_content_uri(uri_text):
    if platform != "android":
        return ""

    cursor = None
    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Uri = autoclass("android.net.Uri")
        OpenableColumns = autoclass("android.provider.OpenableColumns")

        resolver = PythonActivity.mActivity.getContentResolver()
        cursor = resolver.query(Uri.parse(uri_text), None, None, None, None)
        if cursor and cursor.moveToFirst():
            idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if idx >= 0:
                return cursor.getString(idx) or ""
    except Exception as e:
        print(f"ERROR nombre content uri: {e}")
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass

    return ""


def _extension_desde_content_uri(uri_text):
    if platform != "android":
        return ""

    try:
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Uri = autoclass("android.net.Uri")

        resolver = PythonActivity.mActivity.getContentResolver()
        mime = str(resolver.getType(Uri.parse(uri_text)) or "").lower()
        return {
            "application/pdf": ".pdf",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/webp": ".webp",
            "image/heic": ".heic",
            "image/heif": ".heif",
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/3gpp": ".3gp",
            "video/webm": ".webm",
            "audio/mpeg": ".mp3",
            "audio/mp4": ".m4a",
            "audio/aac": ".aac",
            "audio/wav": ".wav",
            "audio/x-wav": ".wav",
            "audio/ogg": ".ogg",
            "audio/opus": ".opus",
            "application/msword": ".doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        }.get(mime, "")
    except Exception as e:
        print(f"ERROR mime content uri: {e}")
        return ""


def _copiar_content_uri(uri_text, destino):
    """Lee un content:// URI de Android y lo escribe en destino con buffer Java."""
    from jnius import autoclass

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    Uri = autoclass("android.net.Uri")
    FileOutputStream = autoclass("java.io.FileOutputStream")

    resolver = PythonActivity.mActivity.getContentResolver()
    uri_obj = Uri.parse(uri_text)
    stream = resolver.openInputStream(uri_obj)
    if not stream:
        raise Exception("No se pudo abrir el archivo seleccionado")

    salida = None
    try:
        from jnius import jarray
        salida = FileOutputStream(destino)
        buffer = jarray("b")([0] * 65536)
        while True:
            leidos = stream.read(buffer)
            if leidos == -1:
                break
            if leidos > 0:
                salida.write(buffer, 0, leidos)
        salida.flush()
    except Exception as e:
        print(f"ERROR copia Java buffer content uri: {e}")
        try:
            if salida:
                salida.close()
        except Exception:
            pass
        try:
            stream.close()
        except Exception:
            pass

        stream = resolver.openInputStream(uri_obj)
        if not stream:
            raise Exception("No se pudo reabrir el archivo seleccionado")
        with open(destino, "wb") as archivo_py:
            while True:
                b = stream.read()
                if b == -1:
                    break
                archivo_py.write(bytes([b & 0xFF]))
    finally:
        try:
            if salida:
                salida.close()
        except Exception:
            pass
        try:
            stream.close()
        except Exception:
            pass


def _preparar_archivo_chat(origen):
    origen = str(origen or "")
    if not origen:
        raise Exception("No se selecciono archivo")

    upload_dir = _chat_upload_dir()
    os.makedirs(upload_dir, exist_ok=True)

    es_content_uri = origen.startswith("content://")
    origen_limpio = origen
    if origen_limpio.startswith("file://"):
        origen_limpio = unquote(origen_limpio.replace("file://", "", 1))

    nombre_base = ""
    if es_content_uri:
        extension = _extension_desde_content_uri(origen)
        nombre_base = _nombre_desde_content_uri(origen)
        if not nombre_base:
            nombre_base = f"archivo{extension or '.bin'}"
        elif os.path.splitext(os.path.basename(str(nombre_base)))[1].lower() not in EXTENSIONES_CHAT:
            nombre_base = f"{nombre_base}{extension}"
    else:
        nombre_base = origen_limpio

    nombre = f"{int(time.time())}_{_limpiar_nombre_archivo(nombre_base)}"
    destino = os.path.join(upload_dir, nombre)

    if es_content_uri:
        _copiar_content_uri(origen, destino)
    else:
        if not os.path.exists(origen_limpio):
            raise Exception("No se encontro el archivo seleccionado")
        shutil.copy(origen_limpio, destino)

    destino, nombre = _normalizar_extension_archivo(destino, nombre, extension if es_content_uri else "")

    ext_final = os.path.splitext(nombre)[1].lower()
    if ext_final not in EXTENSIONES_CHAT:
        raise Exception(f"Tipo no permitido: {ext_final or 'sin extension'} ({nombre})")

    tamano_mb = os.path.getsize(destino) / (1024 * 1024)
    if tamano_mb > MAX_FILE_SIZE_MB:
        try:
            os.remove(destino)
        except Exception:
            pass
        raise Exception(f"Archivo muy grande. Maximo {MAX_FILE_SIZE_MB}MB")

    return destino, nombre


def _make_bubble(texto, es_mio, ancho_max, on_delete=None, avatar_source=None):
    """Burbuja de chat con altura estable para evitar superposiciones.

    avatar_source: si no es None (solo aplica a mensajes del otro), muestra un
    avatar chico al lado de la burbuja. Se pasa None cuando el mensaje anterior
    es del mismo emisor, para no repetirlo — pero igual se reserva el espacio
    con un widget invisible, asi las burbujas quedan alineadas."""
    import time as _time

    # Colores
    if es_mio:
        cor_fondo   = (0.30, 0.23, 0.67, 1)   # violeta
        cor_texto   = (1, 1, 1, 1)
        cor_hora    = (0.80, 0.76, 1.00, 1)
    else:
        cor_fondo   = (1, 1, 1, 1)             # blanco
        cor_texto   = (0.10, 0.12, 0.18, 1)
        cor_hora    = (0.55, 0.58, 0.68, 1)

    hora_str = _time.strftime("%H:%M")

    # Wrapper exterior alineado izq/der
    wrapper = BoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        padding=[dp(8), dp(4)],
        spacing=dp(6),
    )

    if es_mio:
        wrapper.add_widget(BoxLayout(size_hint_x=1))
    else:
        avatar_widget = AsyncImage(
            source=avatar_source or "assets/avatar_default.png",
            size_hint=(None, None),
            size=(dp(24), dp(24)),
            allow_stretch=True,
            keep_ratio=True,
            opacity=1 if avatar_source else 0,
        )
        wrapper.add_widget(avatar_widget)

    col = BoxLayout(
        orientation="vertical",
        size_hint=(None, None),
        width=ancho_max,
        spacing=dp(2),
    )

    bubble = BoxLayout(
        orientation="vertical",
        size_hint=(None, None),
        width=ancho_max,
        padding=[dp(14), dp(10), dp(14), dp(8)],
    )
    with bubble.canvas.before:
        Color(rgba=cor_fondo)
        bubble.bg = RoundedRectangle(
            pos=bubble.pos, size=bubble.size,
            radius=[dp(18), dp(18), dp(4) if es_mio else dp(18), dp(18) if es_mio else dp(4)]
        )
    bubble.bind(
        pos=lambda w, v: setattr(w.bg, "pos", v),
        size=lambda w, v: setattr(w.bg, "size", v),
    )

    texto_lbl = Label(
        text=texto,
        font_size="15sp",
        color=cor_texto,
        halign="left",
        valign="top",
        size_hint_y=None,
    )
    texto_lbl.text_size = (ancho_max - dp(28), None)

    def ajustar(*args):
        texto_lbl.text_size = (ancho_max - dp(28), None)
        texto_lbl.texture_update()
        alt_texto = max(dp(20), texto_lbl.texture_size[1])
        texto_lbl.height = alt_texto
        altura_burbuja = alt_texto + dp(22)
        bubble.height = altura_burbuja
        col.height = altura_burbuja + dp(18)
        wrapper.height = col.height + dp(8)

    texto_lbl.bind(texture_size=ajustar, width=ajustar)
    texto_lbl.width = ancho_max - dp(28)
    bubble.add_widget(texto_lbl)

    lbl_hora = Label(
        text=hora_str,
        font_size="10sp",
        color=cor_hora,
        size_hint_y=None,
        height=dp(14),
        halign="right" if es_mio else "left",
        valign="middle",
    )
    lbl_hora.bind(size=lambda s, *_: setattr(s, "text_size", s.size))

    col.add_widget(bubble)
    col.add_widget(lbl_hora)

    if es_mio and on_delete:
        wrapper.add_widget(_make_delete_button(on_delete))

    wrapper.add_widget(col)

    if not es_mio:
        wrapper.add_widget(BoxLayout(size_hint_x=1))

    Clock.schedule_once(lambda dt: ajustar(), 0)
    return wrapper


def _fecha_legible(fecha_str):
    """'Hoy' / 'Ayer' / dd/mm/aaaa a partir de un created_at tipo ISO."""
    try:
        fecha = datetime.strptime(str(fecha_str)[:19], "%Y-%m-%dT%H:%M:%S").date()
    except Exception:
        return None

    hoy = datetime.now().date()
    if fecha == hoy:
        return "Hoy"
    if (hoy - fecha).days == 1:
        return "Ayer"
    return fecha.strftime("%d/%m/%Y")


def _make_date_separator(texto):
    wrapper = BoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(28),
        padding=[0, dp(6)],
    )

    pill = BoxLayout(
        size_hint=(None, None),
        size=(dp(18) * max(len(texto), 4), dp(20)),
        pos_hint={"center_x": 0.5},
    )
    with pill.canvas.before:
        Color(rgba=(0.90, 0.88, 0.96, 1))
        pill._bg = RoundedRectangle(pos=pill.pos, size=pill.size, radius=[dp(10)])
    pill.bind(
        pos=lambda w, v: setattr(w._bg, "pos", v),
        size=lambda w, v: setattr(w._bg, "size", v),
    )

    lbl = Label(
        text=texto,
        font_size="10sp",
        bold=True,
        color=(0.45, 0.40, 0.60, 1),
    )
    pill.add_widget(lbl)

    wrapper.add_widget(BoxLayout(size_hint_x=1))
    wrapper.add_widget(pill)
    wrapper.add_widget(BoxLayout(size_hint_x=1))
    return wrapper


def _make_delete_button(on_delete):
    """Insignia de "tachito" -- circulo blanco con borde rojo suave y un
    icono de tacho de basura dibujado a mano (tapa + agarre + cuerpo con
    Line/RoundedRectangle), mismo criterio sin-fuente-de-iconos que la
    campanita de avisos (ver dashboard.kv). Reemplaza el cuadrado rojo con
    "X" de antes."""
    from kivy.graphics import Color, Ellipse, Line, RoundedRectangle

    btn = Button(
        size_hint=(None, None),
        width=dp(26),
        height=dp(26),
        background_normal="",
        background_color=(0, 0, 0, 0),
    )

    def _dibujar(*_a):
        btn.canvas.before.clear()
        btn.canvas.after.clear()
        with btn.canvas.before:
            Color(1, 1, 1, 1)
            Ellipse(pos=btn.pos, size=btn.size)
        with btn.canvas.after:
            Color(0.90, 0.30, 0.30, 1)
            Line(circle=(btn.center_x, btn.center_y, dp(12)), width=dp(1.3))

            Color(0.80, 0.20, 0.20, 1)
            cx, cy = btn.center_x, btn.center_y
            # tapa
            Line(points=[cx - dp(5), cy + dp(3), cx + dp(5), cy + dp(3)], width=dp(1.3))
            # agarre
            RoundedRectangle(pos=(cx - dp(2), cy + dp(3)), size=(dp(4), dp(2)), radius=[dp(1)])
            # cuerpo (tacho)
            Line(
                points=[
                    cx - dp(4), cy + dp(3),
                    cx - dp(3), cy - dp(5),
                    cx + dp(3), cy - dp(5),
                    cx + dp(4), cy + dp(3),
                ],
                width=dp(1.3),
            )

    btn.bind(pos=_dibujar, size=_dibujar)
    _dibujar()
    btn.bind(on_release=lambda *_: on_delete())
    return btn


def _make_file_bubble(nombre, archivo, es_mio, ancho_max, on_open, on_delete=None):
    nombre = _nombre_corto_archivo(nombre)
    etiqueta = _etiqueta_archivo(nombre)

    wrapper = BoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(86),
        padding=[dp(8), dp(4)],
    )

    if es_mio:
        wrapper.add_widget(BoxLayout(size_hint_x=1))

    btn = Button(
        text=f"{etiqueta}\n{nombre}",
        size_hint=(None, None),
        width=min(ancho_max, dp(250)),
        height=dp(74),
        font_size="12sp",
        bold=True,
        halign="left",
        valign="middle",
        text_size=(min(ancho_max, dp(250)) - dp(28), dp(64)),
        background_normal="",
        background_color=(0.92, 0.93, 0.96, 1) if not es_mio else (0.30, 0.23, 0.67, 1),
        color=(0.12, 0.14, 0.22, 1) if not es_mio else (1, 1, 1, 1),
    )
    btn.bind(size=lambda s, *_: setattr(s, "text_size", (s.width - dp(28), s.height - dp(10))))
    btn.bind(on_release=lambda x: on_open(archivo))
    if es_mio and on_delete:
        wrapper.add_widget(_make_delete_button(on_delete))
    wrapper.add_widget(btn)

    if not es_mio:
        wrapper.add_widget(BoxLayout(size_hint_x=1))

    return wrapper



class ChatScreen(Screen):

    listener = None
    consulta_listener = None
    ultimo_total_mensajes = -1
    _poll_event = None
    _android_file_request = 9087
    _android_camera_request = 9088
    _camera_uri = None
    _grabando_audio = False
    _recorder = None
    _audio_path = ""
    _audio_inicio = 0
    _aviso_error_event = None
    _cargando_mensajes = False
    _pendiente_scroll_final = False
    _cargando_ui = False
    _chat_otro_avatar = ""
    _audio_player = None
    _audio_popup = None
    _audio_preview_popup = None
    _camera_en_proceso = False
    _camera_permiso_pendiente = False
    _camera_result_pendiente = False
    _enviando_mensaje = False
    _mensajes_cache = []

    def on_enter(self):
        self._setup_ui()
        self.cargar_mensajes(scroll_final=True)
        self._reanudar_actualizaciones_chat()

    def on_leave(self):
        self._cerrar_audio_interno()
        if self._audio_preview_popup:
            try:
                self._audio_preview_popup.dismiss()
            except Exception:
                pass
            self._audio_preview_popup = None
        self._pausar_actualizaciones_chat()

    def _pausar_actualizaciones_chat(self):
        if self.listener:
            try:
                self.listener.unsubscribe()
            except Exception:
                pass
            self.listener = None
        if self.consulta_listener:
            try:
                self.consulta_listener.unsubscribe()
            except Exception:
                pass
            self.consulta_listener = None
        if self._poll_event is not None:
            try:
                self._poll_event.cancel()
            except Exception:
                pass
            self._poll_event = None

    def _reanudar_actualizaciones_chat(self):
        if session.current_consulta_id and not self.listener:
            self.listener = fb.escuchar_mensajes(
                session.current_consulta_id,
                self.on_new_message
            )

        if session.current_consulta_id and not self.consulta_listener:
            self.consulta_listener = fb.escuchar_consulta(
                session.current_consulta_id,
                self.on_consulta_changed
            )

        if self._poll_event is None:
            self._poll_event = Clock.schedule_interval(
                lambda dt: self._poll_mensajes(), 4
            )

    def on_app_resume(self):
        Clock.schedule_once(lambda dt: self._reanudar_actualizaciones_chat(), 0.4)

    def on_new_message(self, msg_data):
        # Solo mostrar notificacion local si NO estoy viendo esta conversacion.
        emisor_uid = msg_data.get('emisor_uid', '')
        mi_uid = session.get_uid()
        app = App.get_running_app()
        pantalla_actual = ""
        try:
            pantalla_actual = app.sm.current if app and getattr(app, "sm", None) else ""
        except Exception:
            pantalla_actual = ""

        if emisor_uid != mi_uid and platform == 'android' and pantalla_actual != 'chat':
            from fcm_service import mostrar_notificacion_local
            emisor = msg_data.get('emisor_email', 'Alguien')
            texto = msg_data.get('texto', '')[:50]
            mostrar_notificacion_local(emisor, texto, "chat_channel")

        Clock.schedule_once(lambda dt: self.cargar_mensajes(scroll_final=True), 0)

    def on_consulta_changed(self, consulta_data):
        """Se llama cuando cambia el estado de la consulta (videollamada, finalizado, etc)"""
        Clock.schedule_once(lambda dt: self._setup_ui(), 0)

    def _poll_mensajes(self):
        """Polling de respaldo: refresca mensajes y estado de consulta en Android."""
        import threading as _threading

        def _check():
            try:
                consulta = fb.obtener_consulta(session.current_consulta_id)
                estado_actual = ""
                if consulta:
                    estado_actual = str(consulta.get("estado") or "")
                if estado_actual != getattr(self, "_ultimo_estado_consulta", ""):
                    self._ultimo_estado_consulta = estado_actual
                    Clock.schedule_once(lambda dt: self._setup_ui(), 0)

                mensajes = fb.obtener_mensajes(session.current_consulta_id)
                total = len(mensajes) if mensajes else 0
                if total != self.ultimo_total_mensajes:
                    Clock.schedule_once(
                        lambda dt: self.cargar_mensajes(scroll_final=True), 0
                    )
            except Exception:
                pass  # Red caida - el proximo poll lo reintentara

        _threading.Thread(target=_check, daemon=True).start()

    def _setup_ui(self):
        consulta_id = session.current_consulta_id
        if not consulta_id or self._cargando_ui:
            return

        self._cargando_ui = True

        def _cargar():
            payload = {
                "consulta": None,
                "interlocutor_data": None,
                "abogado_data": None,
                "video_iniciado": False,
                "tiene_resena": False,
                "es_abogado": session.es_abogado(),
            }
            try:
                consulta = fb.obtener_consulta(consulta_id)
                payload["consulta"] = consulta
                if not consulta:
                    return

                abogado_email = consulta.get('abogado_email', '')
                cliente_email = consulta.get('cliente_email', '')
                es_abogado = payload["es_abogado"]
                interlocutor = cliente_email if es_abogado else abogado_email

                if interlocutor:
                    payload["interlocutor_data"] = fb.obtener_usuario_por_email(interlocutor)
                if not es_abogado and abogado_email:
                    payload["abogado_data"] = fb.obtener_usuario_por_email(abogado_email)

                estado = consulta.get('estado', '')
                tipo = consulta.get('tipo_servicio', '')
                if tipo == "video" and estado in ["en_curso", "videollamada"]:
                    payload["video_iniciado"] = fb.consulta_tiene_videollamada_iniciada(consulta_id)
                if estado == "finalizado" and not es_abogado:
                    payload["tiene_resena"] = fb.tiene_resena(consulta_id)
            finally:
                Clock.schedule_once(lambda dt, data=payload: self._aplicar_setup_ui(data), 0)

        threading.Thread(target=_cargar, daemon=True).start()

    def _aplicar_setup_ui(self, payload):
        self._cargando_ui = False
        consulta = (payload or {}).get("consulta")
        if not consulta:
            return

        estado = consulta.get('estado', '')
        self._ultimo_estado_consulta = str(estado or "")
        abogado_email = consulta.get('abogado_email', '')
        cliente_email = consulta.get('cliente_email', '')
        tipo = consulta.get('tipo_servicio', '')

        es_abogado = bool((payload or {}).get("es_abogado"))
        finalizado = estado == "finalizado"
        interlocutor = cliente_email if es_abogado else abogado_email
        nombre_corto = interlocutor[:18] + "..." if len(interlocutor) > 18 else interlocutor
        interlocutor_data = (payload or {}).get("interlocutor_data") or None

        self.ids.lbl_chat_titulo.text = nombre_corto
        self.ids.lbl_chat_tipo.text = f"Consulta {tipo}"
        # FIX: antes esto limpiaba la source a "" y hacia reload() antes de
        # poner la real -- pensado para forzar una recarga al cambiar de
        # chat, pero el doble reload() podia dejar el avatar en blanco (la
        # segunda carga a veces terminaba antes que la primera "limpieza"
        # terminara de aplicarse). set_avatar_image() con force=True hace
        # lo mismo (fuerza la recarga) de forma segura, reusando el mismo
        # cache-buster/fallback ya probado en el resto de la app.
        self._chat_otro_avatar = set_avatar_image(
            self.ids.img_avatar_chat,
            (interlocutor_data or {}).get("foto_url", ""),
            (interlocutor_data or {}).get("email", interlocutor),
            force=True,
        )

        if es_abogado:
            self.ids.lbl_estado_linea.text = "Cliente conectado"
            self.ids.lbl_estado_linea.color = (0.90, 0.70, 0.10, 1)
        else:
            abogado_data = (payload or {}).get("abogado_data") or {}
            estado_abogado = abogado_data.get('estado_abogado', 'disponible')
            if estado_abogado == "disponible":
                self.ids.lbl_estado_linea.text = "En linea"
                self.ids.lbl_estado_linea.color = (0.18, 0.80, 0.44, 1)
            elif estado_abogado == "guardia":
                self.ids.lbl_estado_linea.text = "En guardia"
                self.ids.lbl_estado_linea.color = (0.95, 0.65, 0.10, 1)
            else:
                self.ids.lbl_estado_linea.text = "Ocupado"
                self.ids.lbl_estado_linea.color = (0.90, 0.25, 0.25, 1)

        video_iniciado = bool((payload or {}).get("video_iniciado"))
        mostrar_video = estado == "videollamada" or (tipo == "video" and video_iniciado)
        self.ids.btn_unirse_video.opacity = 1 if mostrar_video else 0
        self.ids.btn_unirse_video.disabled = not mostrar_video

        consulta_activa = estado in ["en_curso", "videollamada"]
        puede_invitar_video = es_abogado and tipo == "video" and estado == "en_curso"

        if es_abogado and consulta_activa and not finalizado:
            self.ids.btn_finalizar.opacity = 1
            self.ids.btn_finalizar.disabled = False
            if puede_invitar_video:
                self.ids.btn_invitar_video.opacity = 1
                self.ids.btn_invitar_video.disabled = False
            else:
                self.ids.btn_invitar_video.opacity = 0
                self.ids.btn_invitar_video.disabled = True
        else:
            self.ids.btn_finalizar.opacity = 0
            self.ids.btn_finalizar.disabled = True
            self.ids.btn_invitar_video.opacity = 0
            self.ids.btn_invitar_video.disabled = True

        chat_bloqueado = estado not in ["en_curso", "videollamada"]

        if chat_bloqueado and not finalizado:
            self.ids.banner_finalizado.height = dp(38)
            if estado == "pagado":
                self.ids.lbl_banner_fin.text = "Esperando que el abogado acepte la consulta..."
            elif estado == "pendiente":
                self.ids.lbl_banner_fin.text = "Pendiente de pago"
            else:
                self.ids.lbl_banner_fin.text = "Consulta no disponible"
            self.ids.lbl_banner_fin.color = (0.85, 0.62, 0.05, 1)
            self.ids.input_area.disabled = True
            self.ids.input_area.opacity = 0.5
        elif finalizado:
            self.ids.banner_finalizado.height = dp(38)
            self.ids.lbl_banner_fin.text = "Esta consulta fue finalizada"
            self.ids.lbl_banner_fin.color = (0.55, 0.58, 0.65, 1)
            self.ids.input_area.disabled = True
            self.ids.input_area.opacity = 0.5

            if not es_abogado and not bool((payload or {}).get("tiene_resena")):
                Clock.schedule_once(lambda dt: setattr(self.manager, "current", "resena"), 1)
        else:
            self.ids.banner_finalizado.height = 0
            self.ids.lbl_banner_fin.text = ""
            self.ids.input_area.disabled = False
            self.ids.input_area.opacity = 1

    def cargar_mensajes(self, scroll_final=False):
        consulta_id = session.current_consulta_id
        if not consulta_id:
            return
        if self._cargando_mensajes:
            self._pendiente_scroll_final = self._pendiente_scroll_final or scroll_final
            return

        self._cargando_mensajes = True
        self._pendiente_scroll_final = self._pendiente_scroll_final or scroll_final

        def _cargar():
            try:
                mensajes = fb.obtener_mensajes(consulta_id)
            except Exception:
                mensajes = []
            Clock.schedule_once(lambda dt, data=mensajes: self._aplicar_mensajes(data), 0)

        threading.Thread(target=_cargar, daemon=True).start()

    def _aplicar_mensajes(self, mensajes):
        self._cargando_mensajes = False
        scroll_final = self._pendiente_scroll_final
        self._pendiente_scroll_final = False

        self.ids.chat_box.clear_widgets()

        mensajes = mensajes or []
        mensajes_filtrados = []
        ids_vistos = set()
        firmas_vistas = set()

        for msg in mensajes:
            msg_id = msg.get("id")
            if msg_id:
                if msg_id in ids_vistos:
                    continue
                ids_vistos.add(msg_id)

            firma = (
                str(msg.get("emisor_uid") or ""),
                str(msg.get("emisor_email") or ""),
                str(msg.get("texto") or msg.get("mensaje") or ""),
                str(msg.get("archivo") or msg.get("archivo_url") or ""),
                str(msg.get("created_at") or "")[:19],
            )
            if firma in firmas_vistas:
                continue
            firmas_vistas.add(firma)
            mensajes_filtrados.append(msg)

        mensajes = mensajes_filtrados
        self._mensajes_cache = list(mensajes)
        self.ultimo_total_mensajes = len(mensajes)
        mi_email = session.get_email() or ""
        mi_uid = session.get_uid() or ""

        ancho_ventana = self.width
        bubble_w = BUBBLE_W_DESKTOP if ancho_ventana > 700 else BUBBLE_W_MOBILE

        ultima_fecha_legible = None
        ultimo_emisor_key = None

        for msg_data in mensajes:
            mensaje_id = msg_data.get("id")
            emisor_uid = msg_data.get('emisor_uid', '')
            emisor_email = msg_data.get('emisor_email', '')
            texto = msg_data.get('texto', '') or msg_data.get('mensaje', '')
            archivo = msg_data.get('archivo', '') or msg_data.get('archivo_url', '')


            if texto == getattr(fb, "MENSAJE_ELIMINADO_TEXTO", "__LEGALAPP_MSG_ELIMINADO__"):
                continue

            fecha_legible = _fecha_legible(msg_data.get('created_at'))
            if fecha_legible and fecha_legible != ultima_fecha_legible:
                self.ids.chat_box.add_widget(_make_date_separator(fecha_legible))
                ultima_fecha_legible = fecha_legible
                ultimo_emisor_key = None

            if emisor_email == "SISTEMA" or emisor_uid == "SISTEMA":
                lbl = Label(
                    text=texto,
                    font_size="11sp",
                    italic=True,
                    color=(0.45, 0.50, 0.58, 1),
                    size_hint_y=None,
                    height=dp(30),
                    halign="center",
                    valign="middle",
                )
                lbl.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
                self.ids.chat_box.add_widget(lbl)
                ultimo_emisor_key = None
                continue

            es_mio = (emisor_uid == mi_uid) or (emisor_email == mi_email)
            emisor_key = emisor_uid or emisor_email

            if not archivo and texto and "http" in texto and "\n" in texto:
                partes = texto.splitlines()
                posible_url = partes[-1].strip()
                if posible_url.startswith("http://") or posible_url.startswith("https://"):
                    archivo = posible_url
                    texto = "\n".join(partes[:-1]).strip()

            avatar_source = None
            if not es_mio and emisor_key != ultimo_emisor_key:
                avatar_source = self._chat_otro_avatar

            if texto and not archivo:
                self.ids.chat_box.add_widget(
                    _make_bubble(
                        texto,
                        es_mio,
                        bubble_w,
                        (lambda mid=mensaje_id, arc=archivo: self.confirmar_borrado_mensaje(mid, arc)) if es_mio and mensaje_id else None,
                        avatar_source,
                    )
                )

            ultimo_emisor_key = emisor_key

            if archivo:
                nombre_archivo = _nombre_desde_url(archivo)
                self.ids.chat_box.add_widget(
                    _make_file_bubble(
                        nombre_archivo,
                        archivo,
                        es_mio,
                        bubble_w,
                        self.abrir_archivo,
                        (lambda mid=mensaje_id, arc=archivo: self.confirmar_borrado_mensaje(mid, arc)) if es_mio and mensaje_id else None,
                    )
                )

        if scroll_final:
            Clock.schedule_once(lambda dt: self.scroll_abajo(), 0.1)

    def scroll_abajo(self):
        self.ids.scroll_chat.scroll_y = 0

    def on_keyboard_height_changed(self, height):
        if height:
            Clock.schedule_once(lambda dt: self.scroll_abajo(), 0.15)

    def on_input_focus(self, focused):
        if focused:
            Clock.schedule_once(lambda dt: self.scroll_abajo(), 0.15)
            Clock.schedule_once(lambda dt: self.scroll_abajo(), 0.45)

    def enviar(self):
        texto = self.ids.input_mensaje.text.strip()
        if not texto:
            return
        if self._enviando_mensaje:
            return

        mi_uid = session.get_uid()
        if not mi_uid or not session.current_consulta_id:
            return

        consulta_id = session.current_consulta_id
        self._enviando_mensaje = True
        self.ids.input_mensaje.disabled = True
        self.ids.input_mensaje.hint_text = "Enviando..."

        def _procesar():
            ok = fb.enviar_mensaje(consulta_id, mi_uid, texto)
            if ok:
                Clock.schedule_once(lambda dt: self._mensaje_enviado_ok(), 0)
            else:
                Clock.schedule_once(lambda dt: self._archivo_enviado_error("No se pudo enviar el mensaje"), 0)

        threading.Thread(target=_procesar, daemon=True).start()

    def _mensaje_enviado_ok(self):
        self._enviando_mensaje = False
        self.ids.input_mensaje.disabled = False
        self.ids.input_mensaje.text = ""
        self.ids.input_mensaje.hint_text = "Escribe un mensaje..."
        self.ids.input_mensaje.focus = True
        self._ocultar_error_chat()
        self.cargar_mensajes(scroll_final=True)

    def adjuntar(self):
        if platform == "android":
            print("[DEBUG] adjuntar: usando selector nativo Android")
            self.ids.input_mensaje.hint_text = "Seleccionando archivo..."
            if self._abrir_selector_android():
                return
            self.ids.input_mensaje.hint_text = "Escribe un mensaje..."
            self.mostrar_error("No se pudo abrir el selector nativo de Android")
            return

        if PLYER_OK:
            try:
                self.ids.input_mensaje.hint_text = "Seleccionando archivo..."
                filechooser.open_file(
                    on_selection=self.seleccionar_archivo,
                    multiple=False
                )
                return
            except Exception as e:
                self.mostrar_error(f"No se pudo abrir selector: {e}")
                return

        self.mostrar_error("Selector de archivos no disponible")

    def abrir_camara(self):
        if not session.current_consulta_id or not session.get_uid():
            self.mostrar_error("No hay consulta activa")
            return
        if self._camera_en_proceso:
            return

        self._camera_en_proceso = True
        if platform != "android":
            try:
                self._abrir_camara_kivy()
                return
            except Exception as e:
                self._camera_en_proceso = False
                self.mostrar_error(f"No se pudo abrir camara: {e}")
                return

        try:
            from android.permissions import request_permissions, Permission
            self._camera_permiso_pendiente = True
            request_permissions([Permission.CAMERA], self._on_camera_permission_result)
        except Exception:
            self._camera_permiso_pendiente = False
            self._abrir_camara_android()

    def _on_camera_permission_result(self, permissions, grants):
        self._camera_permiso_pendiente = False
        try:
            permitido = True
            if grants:
                permitido = all(grant for grant in grants)
            if not permitido:
                self._camera_en_proceso = False
                Clock.schedule_once(
                    lambda dt: self.mostrar_error("Acepta el permiso de camara y volve a intentarlo."),
                    0
                )
                return
            Clock.schedule_once(lambda dt: self._abrir_camara_android(), 0)
        except Exception as e:
            self._camera_en_proceso = False
            Clock.schedule_once(
                lambda dt, err=str(e): self.mostrar_error(f"No se pudo abrir camara: {err}"),
                0
            )

    def _abrir_camara_android(self):
        try:
            from android import activity
            from jnius import autoclass

            Intent = autoclass("android.content.Intent")
            MediaStore = autoclass("android.provider.MediaStore")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)

            try:
                activity.unbind(on_activity_result=self._on_android_camera_result)
            except Exception:
                pass
            activity.bind(on_activity_result=self._on_android_camera_result)
            self._camera_result_pendiente = True

            PythonActivity.mActivity.startActivityForResult(intent, self._android_camera_request)
        except Exception as e:
            self._camera_en_proceso = False
            self._camera_result_pendiente = False
            self.mostrar_error(f"No se pudo abrir camara: {e}")

    def _on_android_camera_result(self, request_code, result_code, intent):
        if request_code != self._android_camera_request:
            return
        if not self._camera_result_pendiente:
            return

        try:
            from android import activity
            activity.unbind(on_activity_result=self._on_android_camera_result)
        except Exception:
            pass

        self._camera_result_pendiente = False
        self._camera_en_proceso = False

        if result_code != -1:
            Clock.schedule_once(lambda dt: self._restaurar_input_chat(), 0)
            return

        Clock.schedule_once(lambda dt: self._marcar_input_chat_ocupado("Procesando foto..."), 0)

        def _procesar():
            try:
                from jnius import autoclass

                extras = intent.getExtras() if intent else None
                if not extras:
                    Clock.schedule_once(lambda dt: self._archivo_enviado_error("No se recibio imagen de la camara"), 0)
                    return

                bitmap = extras.get("data")
                if not bitmap:
                    Clock.schedule_once(lambda dt: self._archivo_enviado_error("No se recibio imagen de la camara"), 0)
                    return

                ByteArrayOutputStream = autoclass("java.io.ByteArrayOutputStream")
                CompressFormat = autoclass("android.graphics.Bitmap$CompressFormat")
                baos = ByteArrayOutputStream()
                bitmap.compress(CompressFormat.JPEG, 92, baos)
                datos = baos.toByteArray()
                baos.close()
                datos_py = bytes((b & 0xFF) for b in datos)

                upload_dir = _chat_upload_dir()
                os.makedirs(upload_dir, exist_ok=True)
                foto_path = os.path.join(upload_dir, f"{int(time.time())}_camara.jpg")

                with open(foto_path, "wb") as f:
                    f.write(datos_py)

                Clock.schedule_once(
                    lambda dt, path=foto_path: self._enviar_archivo_local(path, os.path.basename(path), "Imagen"),
                    0
                )
            except Exception as e:
                Clock.schedule_once(lambda dt, err=str(e): self._archivo_enviado_error(f"Error al procesar foto: {err}"), 0)

        threading.Thread(target=_procesar, daemon=True).start()

    def _marcar_input_chat_ocupado(self, texto):
        self.ids.input_mensaje.hint_text = texto
        self.ids.input_mensaje.disabled = True

    def _restaurar_input_chat(self):
        self.ids.input_mensaje.disabled = False
        self.ids.input_mensaje.hint_text = "Escribe un mensaje..."

    def _abrir_camara_kivy(self):
        try:
            upload_dir = _chat_upload_dir()
            os.makedirs(upload_dir, exist_ok=True)
            path = os.path.join(upload_dir, f"{int(time.time())}_camara.jpg")

            layout = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
            cam = Camera(play=True, resolution=(720, 1280))
            layout.add_widget(cam)

            botones = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(48),
                spacing=dp(8),
            )
            btn_cancelar = Button(
                text="Cancelar",
                background_normal="",
                background_color=(0.92, 0.89, 0.98, 1),
                color=(0.30, 0.23, 0.67, 1),
            )
            btn_sacar = Button(
                text="Enviar foto",
                bold=True,
                background_normal="",
                background_color=(0.30, 0.23, 0.67, 1),
                color=(1, 1, 1, 1),
            )
            botones.add_widget(btn_cancelar)
            botones.add_widget(btn_sacar)
            layout.add_widget(botones)

            popup = Popup(
                title="Camara",
                content=layout,
                size_hint=(0.96, 0.88),
            )

            def cancelar(_):
                cam.play = False
                popup.dismiss()

            def sacar(_):
                try:
                    if not cam.texture:
                        self.mostrar_error("La camara todavia no esta lista")
                        return
                    cam.export_to_png(path)
                    cam.play = False
                    popup.dismiss()
                    self._enviar_archivo_local(path, os.path.basename(path), "Imagen")
                except Exception as err:
                    self.mostrar_error(f"No se pudo sacar foto: {err}")

            btn_cancelar.bind(on_release=cancelar)
            btn_sacar.bind(on_release=sacar)
            popup.bind(on_dismiss=lambda *_: setattr(cam, "play", False))
            popup.open()
        except Exception as e:
            self.mostrar_error(f"No se pudo abrir camara: {e}")

    def _abrir_selector_android(self):
        try:
            from android import activity
            from jnius import autoclass

            Intent = autoclass("android.content.Intent")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType("*/*")
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            intent.addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
            intent.addFlags(Intent.FLAG_GRANT_PREFIX_URI_PERMISSION)

            try:
                activity.unbind(on_activity_result=self._on_android_file_result)
            except Exception:
                pass
            activity.bind(on_activity_result=self._on_android_file_result)

            print("[DEBUG] _abrir_selector_android: startActivityForResult directo")
            PythonActivity.mActivity.startActivityForResult(intent, self._android_file_request)
            return True
        except Exception as e:
            print(f"ERROR selector android: {e}")
            return False

    def _on_android_file_result(self, request_code, result_code, intent):
        if request_code != self._android_file_request:
            return

        try:
            from android import activity
            activity.unbind(on_activity_result=self._on_android_file_result)
        except Exception:
            pass

        if result_code != -1 or not intent:
            Clock.schedule_once(
                lambda dt: setattr(self.ids.input_mensaje, "hint_text", "Escribe un mensaje..."),
                0
            )
            return

        try:
            uri = intent.getData()
            print(f"[DEBUG] _on_android_file_result getData={uri}")
            if not uri:
                clip = intent.getClipData()
                print(f"[DEBUG] _on_android_file_result clip={clip}")
                if clip and clip.getItemCount() > 0:
                    uri = clip.getItemAt(0).getUri()
            if not uri:
                Clock.schedule_once(lambda dt: self._archivo_enviado_error("No se recibio archivo del selector"), 0)
                return

            uri_text = str(uri.toString())
            print(f"[DEBUG] _on_android_file_result uri={uri_text[:140]}")
            try:
                from jnius import autoclass
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                Intent = autoclass("android.content.Intent")
                flags = intent.getFlags() & (
                    Intent.FLAG_GRANT_READ_URI_PERMISSION
                    | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                )
                if flags:
                    PythonActivity.mActivity.getContentResolver().takePersistableUriPermission(uri, flags)
            except Exception as e_perm:
                print(f"[DEBUG] permiso persistente no tomado: {e_perm}")
            Clock.schedule_once(lambda dt, uri_text=uri_text: self.seleccionar_archivo([uri_text]), 0)
        except Exception as e:
            error_msg = str(e)
            Clock.schedule_once(lambda dt, err=error_msg: self._archivo_enviado_error(f"No se pudo leer archivo: {err}"), 0)

    def seleccionar_archivo(self, selection):
        if not selection:
            print("[DEBUG] seleccionar_archivo: selection vacia")
            return

        if isinstance(selection, (list, tuple)):
            origen = selection[0]
        else:
            origen = selection

        if not origen:
            print("[DEBUG] seleccionar_archivo: origen vacio")
            return

        print(f"[DEBUG] seleccionar_archivo: origen={str(origen)[:140]}")

        mi_uid = session.get_uid()
        if not mi_uid or not session.current_consulta_id:
            self.mostrar_error("No hay consulta activa")
            return

        self.ids.input_mensaje.hint_text = "Subiendo archivo..."
        self.ids.input_mensaje.text = ""
        self.ids.input_mensaje.disabled = True

        consulta_id = session.current_consulta_id

        def _procesar():
            try:
                print(f"[DEBUG] Preparando archivo: {str(origen)[:120]}")
                destino, nombre = _preparar_archivo_chat(origen)
                try:
                    tamano = os.path.getsize(destino)
                except Exception:
                    tamano = -1
                print(f"[DEBUG] Archivo preparado: nombre={nombre} destino={destino} bytes={tamano}")
                etiqueta = _etiqueta_archivo(nombre)
                print(f"[DEBUG] Subiendo a Supabase: {nombre} ({etiqueta})")
                ok, url = fb.subir_archivo_chat(consulta_id, destino, nombre)

                if not ok:
                    raise Exception(str(url or "No se pudo cargar el archivo"))

                print(f"[DEBUG] Subido OK, enviando mensaje: {str(url)[:120]}")
                enviado = fb.enviar_mensaje(
                    consulta_id,
                    mi_uid,
                    f"{etiqueta}: {nombre}",
                    archivo=url
                )

                if not enviado:
                    raise Exception("El archivo subio, pero no se pudo enviar el mensaje")

                print("[DEBUG] Mensaje de archivo enviado OK")
                Clock.schedule_once(lambda dt: self._archivo_enviado_ok(), 0)

            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] seleccionar_archivo _procesar: {error_msg}")
                Clock.schedule_once(lambda dt, err=error_msg: self._archivo_enviado_error(err), 0)

        threading.Thread(target=_procesar, daemon=True).start()

    def _archivo_enviado_ok(self):
        self._enviando_mensaje = False
        self._restaurar_input_chat()
        self._ocultar_error_chat()
        self.cargar_mensajes(scroll_final=True)

    def _archivo_enviado_error(self, error):
        self._enviando_mensaje = False
        self._restaurar_input_chat()
        self.mostrar_error(error)
        self.cargar_mensajes(scroll_final=True)

    def iniciar_audio(self):
        if platform != "android":
            self.mostrar_error("La grabacion de audio esta disponible en Android")
            return
        if self._grabando_audio:
            return
        if not session.current_consulta_id or not session.get_uid():
            self.mostrar_error("No hay consulta activa")
            return

        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.RECORD_AUDIO])
        except Exception:
            pass

        try:
            from jnius import autoclass

            MediaRecorder = autoclass("android.media.MediaRecorder")
            AudioSource = autoclass("android.media.MediaRecorder$AudioSource")
            OutputFormat = autoclass("android.media.MediaRecorder$OutputFormat")
            AudioEncoder = autoclass("android.media.MediaRecorder$AudioEncoder")

            upload_dir = _chat_upload_dir()
            os.makedirs(upload_dir, exist_ok=True)
            self._audio_path = os.path.join(upload_dir, f"{int(time.time())}_audio.m4a")

            recorder = MediaRecorder()
            recorder.setAudioSource(AudioSource.MIC)
            recorder.setOutputFormat(OutputFormat.MPEG_4)
            recorder.setAudioEncoder(AudioEncoder.AAC)
            recorder.setOutputFile(self._audio_path)
            recorder.prepare()
            recorder.start()

            self._recorder = recorder
            self._grabando_audio = True
            self._audio_inicio = time.time()
            self.ids.input_mensaje.hint_text = "Grabando audio..."
        except Exception as e:
            self._grabando_audio = False
            self._recorder = None
            self._audio_path = ""
            self.mostrar_error(f"No se pudo grabar audio: {e}")

    def finalizar_audio(self):
        if not self._grabando_audio:
            return

        recorder = self._recorder
        audio_path = self._audio_path
        duracion = time.time() - self._audio_inicio

        self._grabando_audio = False
        self._recorder = None
        self._audio_path = ""
        self.ids.input_mensaje.hint_text = "Preparando audio..."
        self.ids.input_mensaje.disabled = True

        def _cerrar_audio():
            try:
                if recorder:
                    try:
                        recorder.stop()
                    except Exception:
                        pass
                    recorder.release()
            except Exception as e:
                Clock.schedule_once(lambda dt, err=str(e): self._archivo_enviado_error(f"No se pudo finalizar audio: {err}"), 0)
                return

            if duracion < 0.7:
                try:
                    if audio_path and os.path.exists(audio_path):
                        os.remove(audio_path)
                except Exception:
                    pass
                Clock.schedule_once(lambda dt: self._archivo_enviado_ok(), 0)
                return

            Clock.schedule_once(
                lambda dt, path=audio_path: self._confirmar_envio_audio(path),
                0
            )

        threading.Thread(target=_cerrar_audio, daemon=True).start()

    def _confirmar_envio_audio(self, audio_path):
        self.ids.input_mensaje.disabled = False
        self.ids.input_mensaje.hint_text = "Audio grabado"
        nombre = os.path.basename(audio_path or "") or "audio.m4a"

        layout = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        layout.add_widget(Label(
            text="Audio listo para enviar",
            size_hint_y=None,
            height=dp(26),
            font_size="15sp",
            bold=True,
            color=(0.18, 0.12, 0.40, 1),
        ))
        layout.add_widget(Label(
            text=nombre,
            size_hint_y=None,
            height=dp(22),
            font_size="12sp",
            color=(0.35, 0.35, 0.45, 1),
        ))

        botones = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        btn_cancelar = Button(
            text="Descartar",
            background_normal="",
            background_color=(0.88, 0.24, 0.24, 1),
            color=(1, 1, 1, 1),
            bold=True,
        )
        btn_enviar = Button(
            text="Enviar",
            background_normal="",
            background_color=(0.30, 0.23, 0.67, 1),
            color=(1, 1, 1, 1),
            bold=True,
        )
        botones.add_widget(btn_cancelar)
        botones.add_widget(btn_enviar)
        layout.add_widget(botones)

        popup = Popup(
            title="Audio",
            content=layout,
            size_hint=(0.88, None),
            height=dp(220),
            auto_dismiss=False,
        )

        def descartar(_):
            try:
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception:
                pass
            self.ids.input_mensaje.hint_text = "Escribe un mensaje..."
            self._audio_preview_popup = None
            popup.dismiss()

        def enviar_audio(_):
            self.ids.input_mensaje.hint_text = "Subiendo audio..."
            self.ids.input_mensaje.disabled = True
            self._audio_preview_popup = None
            popup.dismiss()
            self._enviar_archivo_local(audio_path, nombre, "Audio")

        btn_cancelar.bind(on_release=descartar)
        btn_enviar.bind(on_release=enviar_audio)
        popup.bind(on_dismiss=lambda *_: setattr(self, "_audio_preview_popup", None))
        self._audio_preview_popup = popup
        popup.open()

    def _enviar_archivo_local(self, path_local, nombre, etiqueta="Archivo"):
        mi_uid = session.get_uid()
        consulta_id = session.current_consulta_id
        if not mi_uid or not consulta_id:
            self.mostrar_error("No hay consulta activa")
            return

        if self._enviando_mensaje:
            return

        self._enviando_mensaje = True
        self.ids.input_mensaje.disabled = True

        def _procesar():
            try:
                ok, url = fb.subir_archivo_chat(consulta_id, path_local, nombre)

                if not ok:
                    raise Exception(str(url or "No se pudo cargar el archivo"))

                enviado = fb.enviar_mensaje(
                    consulta_id,
                    mi_uid,
                    f"{etiqueta}: {nombre}",
                    archivo=url
                )

                if not enviado:
                    raise Exception("El archivo subio, pero no se pudo enviar el mensaje")

                Clock.schedule_once(lambda dt: self._archivo_enviado_ok(), 0)

            except Exception as e:
                Clock.schedule_once(lambda dt, err=str(e): self._archivo_enviado_error(err), 0)

        threading.Thread(target=_procesar, daemon=True).start()

    def confirmar_borrado_mensaje(self, mensaje_id, archivo=None):
        if not mensaje_id:
            return

        layout = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        layout.add_widget(Label(
            text="Se borrara este mensaje para ambos lados.",
            font_size="14sp",
            color=(0.18, 0.12, 0.40, 1),
        ))

        botones = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        btn_cancelar = Button(
            text="Cancelar",
            background_normal="",
            background_color=(0.90, 0.88, 0.96, 1),
            color=(0.30, 0.23, 0.67, 1),
            bold=True,
        )
        btn_borrar = Button(
            text="Borrar",
            background_normal="",
            background_color=(0.86, 0.20, 0.20, 1),
            color=(1, 1, 1, 1),
            bold=True,
        )
        botones.add_widget(btn_cancelar)
        botones.add_widget(btn_borrar)
        layout.add_widget(botones)

        popup = Popup(
            title="Borrar mensaje",
            content=layout,
            size_hint=(0.86, None),
            height=dp(200),
            auto_dismiss=False,
        )

        btn_cancelar.bind(on_release=lambda *_: popup.dismiss())
        btn_borrar.bind(on_release=lambda *_: self._borrar_mensaje_chat(mensaje_id, archivo, popup))
        popup.open()

    def _borrar_mensaje_chat(self, mensaje_id, archivo, popup=None):
        mi_uid = session.get_uid()
        if popup:
            popup.dismiss()
        if not mi_uid:
            return

        self.ids.input_mensaje.disabled = True
        self.ids.input_mensaje.hint_text = "Borrando mensaje..."

        def _procesar():
            ok = fb.eliminar_mensaje_chat(mensaje_id, mi_uid, archivo)
            if ok:
                Clock.schedule_once(lambda dt, mid=mensaje_id: self._mensaje_borrado_ok(mid), 0)
            else:
                Clock.schedule_once(lambda dt: self._archivo_enviado_error("No se pudo borrar el mensaje"), 0)

        threading.Thread(target=_procesar, daemon=True).start()

    def _mensaje_borrado_ok(self, mensaje_id):
        self._restaurar_input_chat()
        self._ocultar_error_chat()
        self._quitar_mensaje_local(mensaje_id)
        Clock.schedule_once(lambda dt: self.cargar_mensajes(scroll_final=False), 0.2)

    def _quitar_mensaje_local(self, mensaje_id):
        actuales = list(self._mensajes_cache or [])
        if not actuales:
            return

        filtrados = [msg for msg in actuales if str(msg.get("id")) != str(mensaje_id)]
        if len(filtrados) == len(actuales):
            return

        self._mensajes_cache = list(filtrados)
        self.ultimo_total_mensajes = len(filtrados)
        self._pendiente_scroll_final = False
        self._aplicar_mensajes(filtrados)

    def abrir_archivo(self, path):
        nombre = _nombre_desde_url(path)
        es_url_remota = str(path).startswith(("http://", "https://"))

        if _es_imagen(nombre) and es_url_remota:
            self._mostrar_imagen(path, nombre)
            return

        if _es_audio(nombre) and es_url_remota:
            self._mostrar_audio(path, nombre)
            return

        if es_url_remota:
            try:
                import webbrowser
                webbrowser.open(path)
                return
            except Exception as e:
                self.mostrar_error(f"No se pudo abrir archivo: {e}")
            return

        if not os.path.exists(path):
            return
        try:
            os.startfile(path)
        except Exception as e:
            print("No se pudo abrir:", e)

    def _mostrar_imagen(self, url, nombre):
        layout = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        imagen = AsyncImage(
            source=url,
            allow_stretch=True,
            keep_ratio=True,
        )
        layout.add_widget(imagen)

        btn = Button(
            text="Cerrar",
            size_hint_y=None,
            height=dp(46),
            bold=True,
            background_normal="",
            background_color=(0.30, 0.23, 0.67, 1),
            color=(1, 1, 1, 1),
        )

        popup = Popup(
            title=nombre,
            content=layout,
            size_hint=(0.96, 0.86),
        )
        btn.bind(on_release=popup.dismiss)
        layout.add_widget(btn)
        popup.open()

    def _mostrar_audio(self, url, nombre):
        self._cerrar_audio_interno()

        layout = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        info = Label(
            text=f"Audio\n{nombre}",
            font_size="14sp",
            color=(0.12, 0.14, 0.22, 1),
            halign="center",
            valign="middle",
        )
        info.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
        layout.add_widget(info)

        estado = Label(
            text="Listo para reproducir",
            font_size="12sp",
            color=(0.45, 0.50, 0.58, 1),
            halign="center",
            valign="middle",
            size_hint_y=None,
            height=dp(24),
        )
        estado.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
        layout.add_widget(estado)

        controles = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(46),
            spacing=dp(8),
        )

        btn_play = Button(
            text="Reproducir",
            size_hint_y=None,
            height=dp(46),
            bold=True,
            background_normal="",
            background_color=(0.30, 0.23, 0.67, 1),
            color=(1, 1, 1, 1),
        )
        btn_pause = Button(
            text="Pausar",
            size_hint_y=None,
            height=dp(46),
            bold=True,
            background_normal="",
            background_color=(0.18, 0.55, 0.85, 1),
            color=(1, 1, 1, 1),
        )
        btn_restart = Button(
            text="Reiniciar",
            size_hint_y=None,
            height=dp(46),
            bold=True,
            background_normal="",
            background_color=(0.18, 0.80, 0.44, 1),
            color=(1, 1, 1, 1),
        )
        btn_cerrar = Button(
            text="Cerrar",
            size_hint_y=None,
            height=dp(42),
            background_normal="",
            background_color=(0.92, 0.89, 0.98, 1),
            color=(0.30, 0.23, 0.67, 1),
        )

        popup = Popup(
            title="Audio",
            content=layout,
            size_hint=(0.90, 0.38),
        )
        self._audio_popup = popup

        def _crear_player():
            if platform != "android":
                return None
            try:
                from jnius import autoclass
                MediaPlayer = autoclass("android.media.MediaPlayer")
                Uri = autoclass("android.net.Uri")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                return MediaPlayer.create(PythonActivity.mActivity, Uri.parse(url))
            except Exception:
                return None

        def reproducir(_):
            try:
                if platform == "android":
                    if self._audio_player is None:
                        self._audio_player = _crear_player()
                    if not self._audio_player:
                        raise Exception("No se pudo preparar el audio")
                    self._audio_player.start()
                    estado.text = "Reproduciendo..."
                    return

                import webbrowser
                webbrowser.open(url)
                estado.text = "Abierto en el reproductor del sistema"
            except Exception as e:
                self.mostrar_error(f"No se pudo abrir audio: {e}")

        def pausar(_):
            try:
                if self._audio_player and self._audio_player.isPlaying():
                    self._audio_player.pause()
                    estado.text = "Audio en pausa"
            except Exception:
                pass

        def reiniciar(_):
            try:
                if self._audio_player:
                    self._audio_player.seekTo(0)
                    self._audio_player.start()
                    estado.text = "Reproduciendo desde el inicio"
                else:
                    reproducir(None)
            except Exception as e:
                self.mostrar_error(f"No se pudo reiniciar audio: {e}")

        def cerrar(_):
            self._cerrar_audio_interno()
            popup.dismiss()

        btn_play.bind(on_release=reproducir)
        btn_pause.bind(on_release=pausar)
        btn_restart.bind(on_release=reiniciar)
        btn_cerrar.bind(on_release=cerrar)
        controles.add_widget(btn_play)
        controles.add_widget(btn_pause)
        controles.add_widget(btn_restart)
        layout.add_widget(controles)
        layout.add_widget(btn_cerrar)
        popup.bind(on_dismiss=lambda *_: self._cerrar_audio_interno())
        popup.open()

    def _cerrar_audio_interno(self):
        try:
            if self._audio_player:
                try:
                    if self._audio_player.isPlaying():
                        self._audio_player.stop()
                except Exception:
                    pass
                try:
                    self._audio_player.release()
                except Exception:
                    pass
        finally:
            self._audio_player = None
            self._audio_popup = None

    def finalizar_consulta(self):
        if not session.current_consulta_id:
            return
        if not session.es_abogado():
            return

        fb.actualizar_estado_consulta(session.current_consulta_id, 'finalizado')

        # Notificar al cliente que la consulta fue finalizada
        consulta = fb.obtener_consulta(session.current_consulta_id)
        if consulta:
            cliente_uid = consulta.get('cliente_uid')
            if cliente_uid:
                fb.notificar_consulta_finalizada(cliente_uid)

        mi_uid = session.get_uid()
        if mi_uid:
            fb.enviar_mensaje(session.current_consulta_id, mi_uid,
                            "El abogado finalizo esta consulta.")

        self._setup_ui()
        self.cargar_mensajes(scroll_final=True)

        if not session.es_abogado() and not fb.tiene_resena(session.current_consulta_id):
            Clock.schedule_once(lambda dt: setattr(self.manager, "current", "resena"), 0.5)

    def invitar_videollamada(self):
        if not session.current_consulta_id:
            return

        if not session.es_abogado():
            return

        consulta = fb.obtener_consulta(session.current_consulta_id)
        if not consulta:
            return

        if consulta.get('tipo_servicio') != "video" or consulta.get('estado') != "en_curso":
            self._setup_ui()
            return

        fb.actualizar_estado_consulta(session.current_consulta_id, 'videollamada')

        # Notificar al cliente que el abogado inicio videollamada
        consulta = fb.obtener_consulta(session.current_consulta_id)
        if consulta:
            cliente_uid = consulta.get('cliente_uid')
            if cliente_uid:
                fb.notificar_videollamada(cliente_uid, session.current_consulta_id)

        mi_uid = session.get_uid()
        if mi_uid:
            fb.enviar_mensaje(session.current_consulta_id, mi_uid,
                            "El abogado inicio una videollamada.")

        self._setup_ui()
        self.cargar_mensajes(scroll_final=True)
        self.manager.current = "videollamada"

    def ir_video(self):
        consulta = fb.obtener_consulta(session.current_consulta_id)
        if not consulta:
            return

        estado = str(consulta.get('estado') or "")
        tipo = consulta.get('tipo_servicio', 'chat') or 'chat'
        video_iniciado = (
            tipo == "video"
            and estado in ["en_curso", "videollamada"]
            and fb.consulta_tiene_videollamada_iniciada(session.current_consulta_id)
        )

        if estado == "videollamada" or video_iniciado:
            self.manager.current = "videollamada"

    def _normalizar_texto_error(self, mensaje):
        texto = str(mensaje or "Ocurrio un inconveniente")
        texto_l = texto.lower()

        if "permission" in texto_l or "permiso" in texto_l:
            return "Acepta el permiso del celular y volve a intentarlo."
        if "selector nativo" in texto_l:
            return "No se pudo abrir el selector de archivos."
        if "selector de archivos no disponible" in texto_l:
            return "No se pudo abrir el selector de archivos."
        if "no se recibio archivo" in texto_l:
            return "No se pudo leer el archivo seleccionado."
        if "no se pudo leer archivo" in texto_l:
            return "No se pudo leer el archivo seleccionado."
        if "invalid instance of 'android/net/uri'" in texto_l:
            return "No se pudo abrir la camara. Intenta de nuevo."
        if "jvm exception occurred" in texto_l or "runtimeexception" in texto_l:
            return "El celular rechazo la accion. Proba nuevamente en unos segundos."
        if "contentresolver.insert" in texto_l or "invalid column null" in texto_l:
            return "No se pudo procesar el archivo seleccionado."
        if "no hay consulta activa" in texto_l:
            return "No hay una consulta activa en este momento."
        if "no se pudo abrir camara" in texto_l:
            return "No se pudo abrir la camara."
        if "error al procesar foto" in texto_l:
            return "No se pudo preparar la foto para enviarla."
        if "no se pudo grabar audio" in texto_l:
            return "No se pudo iniciar el audio."
        if "no se pudo finalizar audio" in texto_l:
            return "No se pudo terminar de grabar el audio."
        if "no se pudo cargar el archivo" in texto_l:
            return "No se pudo subir el archivo."
        if "no se pudo abrir audio" in texto_l:
            return "No se pudo abrir el audio."
        if len(texto) > 120:
            return "Ocurrio un inconveniente. Proba nuevamente."
        return texto

    def _ocultar_error_chat(self, *_args):
        if not hasattr(self, "ids"):
            return
        banner = self.ids.get("banner_error_chat")
        label = self.ids.get("lbl_banner_error_chat")
        if not banner or not label:
            return
        banner.height = 0
        banner.opacity = 0
        label.text = ""
        self._aviso_error_event = None

    def mostrar_error(self, mensaje):
        texto = self._normalizar_texto_error(mensaje)
        banner = self.ids.get("banner_error_chat")
        label = self.ids.get("lbl_banner_error_chat")
        if not banner or not label:
            return

        label.text = texto
        banner.height = dp(38)
        banner.opacity = 1

        if self._aviso_error_event is not None:
            try:
                self._aviso_error_event.cancel()
            except Exception:
                pass
            self._aviso_error_event = None

        self._aviso_error_event = Clock.schedule_once(self._ocultar_error_chat, 3.5)

    def volver(self):
        if session.es_abogado():
            self.manager.current = "abogado_panel"
        else:
            self.manager.current = "historial"

