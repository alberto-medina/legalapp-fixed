import os
import time
import shutil

from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.utils import platform

import firebase_config as fb
import session

try:
    from plyer import filechooser
    PLYER_OK = True
except Exception:
    PLYER_OK = False

UPLOAD_DIR = "assets/uploads"

BUBBLE_W_DESKTOP = 420
BUBBLE_W_MOBILE = 260

# Limite de tamano para archivos: 2MB
MAX_FILE_SIZE_MB = 2


def _make_bubble(texto, es_mio, ancho_max):
    cor_fondo = (0.30, 0.23, 0.67, 1) if es_mio else (1, 1, 1, 1)
    cor_texto = (1, 1, 1, 1) if es_mio else (0.10, 0.12, 0.18, 1)

    wrapper = BoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        padding=[dp(8), dp(4)],
        spacing=dp(6),
    )

    if es_mio:
        wrapper.add_widget(BoxLayout())

    bubble = BoxLayout(
        orientation="vertical",
        size_hint=(None, None),
        width=ancho_max,
        padding=[dp(14), dp(10)],
    )

    with bubble.canvas.before:
        Color(rgba=cor_fondo)
        bubble.bg = RoundedRectangle(pos=bubble.pos, size=bubble.size, radius=[dp(18)])

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

    texto_lbl.bind(width=lambda s, *_: setattr(s, "text_size", (s.width, None)))

    def ajustar(*args):
        texto_lbl.texture_update()
        altura = max(dp(34), texto_lbl.texture_size[1])
        texto_lbl.height = altura
        bubble.height = altura + dp(24)
        wrapper.height = bubble.height + dp(8)

    texto_lbl.bind(texture_size=ajustar, width=ajustar)
    texto_lbl.width = ancho_max - dp(28)
    bubble.add_widget(texto_lbl)
    wrapper.add_widget(bubble)

    if not es_mio:
        wrapper.add_widget(BoxLayout())

    Clock.schedule_once(lambda dt: ajustar(), 0)
    return wrapper


class ChatScreen(Screen):

    listener = None
    consulta_listener = None
    ultimo_total_mensajes = -1

    def on_enter(self):
        self._setup_ui()
        self.cargar_mensajes(scroll_final=True)

        # Listener de mensajes en tiempo real (eficiente)
        if session.current_consulta_id and not self.listener:
            self.listener = fb.escuchar_mensajes(
                session.current_consulta_id,
                self.on_new_message
            )

        # Listener de consulta para detectar cambio de estado (videollamada, finalizado)
        if session.current_consulta_id and not self.consulta_listener:
            self.consulta_listener = fb.escuchar_consulta(
                session.current_consulta_id,
                self.on_consulta_changed
            )

    def on_leave(self):
        if self.listener:
            self.listener.unsubscribe()
            self.listener = None
        if self.consulta_listener:
            self.consulta_listener.unsubscribe()
            self.consulta_listener = None

    def on_new_message(self, msg_data):
        # Solo mostrar notificacion local si NO estoy en primer plano
        # (evitar duplicado con FCM)
        emisor_uid = msg_data.get('emisor_uid', '')
        mi_uid = session.get_uid()
        if emisor_uid != mi_uid and platform == 'android':
            from fcm_service import mostrar_notificacion_local
            emisor = msg_data.get('emisor_email', 'Alguien')
            texto = msg_data.get('texto', '')[:50]
            mostrar_notificacion_local(f"Nuevo mensaje de {emisor}", texto, "chat_channel")

        Clock.schedule_once(lambda dt: self.cargar_mensajes(scroll_final=True), 0)

    def on_consulta_changed(self, consulta_data):
        """Se llama cuando cambia el estado de la consulta (videollamada, finalizado, etc)"""
        Clock.schedule_once(lambda dt: self._setup_ui(), 0)

    def _setup_ui(self):
        consulta = fb.obtener_consulta(session.current_consulta_id)
        if not consulta:
            return

        estado = consulta.get('estado', '')
        abogado_email = consulta.get('abogado_email', '')
        cliente_email = consulta.get('cliente_email', '')
        tipo = consulta.get('tipo_servicio', '')

        es_abogado = session.es_abogado()
        finalizado = estado == "finalizado"
        interlocutor = cliente_email if es_abogado else abogado_email
        nombre_corto = interlocutor[:18] + "..." if len(interlocutor) > 18 else interlocutor

        self.ids.lbl_chat_titulo.text = nombre_corto
        self.ids.lbl_chat_tipo.text = f"Consulta {tipo}"

        if es_abogado:
            self.ids.lbl_estado_linea.text = "Cliente conectado"
            self.ids.lbl_estado_linea.color = (0.90, 0.70, 0.10, 1)
        else:
            abogado_data = fb.obtener_usuario_por_email(abogado_email)
            estado_abogado = abogado_data.get('estado_abogado', 'disponible') if abogado_data else 'disponible'

            if estado_abogado == "disponible":
                self.ids.lbl_estado_linea.text = "En linea"
                self.ids.lbl_estado_linea.color = (0.18, 0.80, 0.44, 1)
            elif estado_abogado == "guardia":
                self.ids.lbl_estado_linea.text = "En guardia"
                self.ids.lbl_estado_linea.color = (0.95, 0.65, 0.10, 1)
            else:
                self.ids.lbl_estado_linea.text = "Ocupado"
                self.ids.lbl_estado_linea.color = (0.90, 0.25, 0.25, 1)

        mostrar_video = estado == "videollamada"
        self.ids.btn_unirse_video.opacity = 1 if mostrar_video else 0
        self.ids.btn_unirse_video.disabled = not mostrar_video

        # Botones segun estado y rol
        if es_abogado and not finalizado:
            self.ids.btn_finalizar.opacity = 1
            self.ids.btn_finalizar.disabled = False
            if tipo == "video":
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

        # Bloquear chat si no esta en_curso o videollamada
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

            if not es_abogado and not fb.tiene_resena(session.current_consulta_id):
                Clock.schedule_once(lambda dt: setattr(self.manager, "current", "resena"), 1)
        else:
            self.ids.banner_finalizado.height = 0
            self.ids.lbl_banner_fin.text = ""
            self.ids.input_area.disabled = False
            self.ids.input_area.opacity = 1

    def cargar_mensajes(self, scroll_final=False):
        self.ids.chat_box.clear_widgets()

        if not session.current_consulta_id:
            return

        mensajes = fb.obtener_mensajes(session.current_consulta_id)

        self.ultimo_total_mensajes = len(mensajes)
        mi_email = session.get_email() or ""
        mi_uid = session.get_uid() or ""

        ancho_ventana = self.width
        bubble_w = BUBBLE_W_DESKTOP if ancho_ventana > 700 else BUBBLE_W_MOBILE

        for msg_data in mensajes:
            emisor_uid = msg_data.get('emisor_uid', '')
            emisor_email = msg_data.get('emisor_email', '')
            texto = msg_data.get('texto', '') or msg_data.get('mensaje', '')
            archivo = msg_data.get('archivo', '')

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
                continue

            es_mio = (emisor_uid == mi_uid) or (emisor_email == mi_email)

            if texto:
                self.ids.chat_box.add_widget(_make_bubble(texto, es_mio, bubble_w))

            if archivo:
                btn = Button(
                    text=f"📎 {os.path.basename(archivo)}",
                    size_hint_y=None,
                    height=dp(44),
                    background_normal="",
                    background_color=(0.92, 0.93, 0.96, 1),
                    color=(0.12, 0.14, 0.22, 1),
                    font_size="12sp",
                )
                btn.bind(on_release=lambda x, p=archivo: self.abrir_archivo(p))
                self.ids.chat_box.add_widget(btn)

        if scroll_final:
            Clock.schedule_once(lambda dt: self.scroll_abajo(), 0.1)

    def scroll_abajo(self):
        self.ids.scroll_chat.scroll_y = 0

    def enviar(self):
        texto = self.ids.input_mensaje.text.strip()
        if not texto:
            return

        mi_uid = session.get_uid()
        if not mi_uid or not session.current_consulta_id:
            return

        fb.enviar_mensaje(session.current_consulta_id, mi_uid, texto)
        fb.notificar_nuevo_mensaje(session.current_consulta_id, mi_uid, texto)

        self.ids.input_mensaje.text = ""
        self.ids.input_mensaje.focus = True
        self.cargar_mensajes(scroll_final=True)

    def adjuntar(self):
        if PLYER_OK:
            try:
                filechooser.open_file(on_selection=self.seleccionar_archivo)
                return
            except Exception:
                pass

    def seleccionar_archivo(self, selection):
        if not selection:
            return

        origen = selection[0]

        # Validar tamano del archivo
        tamano_mb = os.path.getsize(origen) / (1024 * 1024)
        if tamano_mb > MAX_FILE_SIZE_MB:
            self.mostrar_error(f"Archivo muy grande. Maximo {MAX_FILE_SIZE_MB}MB")
            return

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        nombre = f"{int(time.time())}_{os.path.basename(origen)}"
        destino = os.path.join(UPLOAD_DIR, nombre)
        shutil.copy(origen, destino)

        mi_uid = session.get_uid()
        if mi_uid and session.current_consulta_id:
            ok, url = fb.subir_archivo_chat(session.current_consulta_id, destino, nombre)
            if ok:
                fb.enviar_mensaje(session.current_consulta_id, mi_uid, f"📎 Archivo: {nombre}")

        self.cargar_mensajes(scroll_final=True)

    def abrir_archivo(self, path):
        if not os.path.exists(path):
            return
        try:
            os.startfile(path)
        except Exception as e:
            print("No se pudo abrir:", e)

    def finalizar_consulta(self):
        if not session.current_consulta_id:
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

        self.manager.current = "videollamada"

    def ir_video(self):
        consulta = fb.obtener_consulta(session.current_consulta_id)
        if consulta and consulta.get('estado') == "videollamada":
            self.manager.current = "videollamada"

    def mostrar_error(self, mensaje):
        """Mostrar error temporal"""
        popup = Popup(
            title='Error',
            content=Label(text=mensaje, color=(0.9, 0.2, 0.2, 1)),
            size_hint=(0.8, 0.3)
        )
        popup.open()

    def volver(self):
        if session.es_abogado():
            self.manager.current = "abogado_panel"
        else:
            self.manager.current = "historial"