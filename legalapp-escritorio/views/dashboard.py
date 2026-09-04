from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.utils import platform
from kivy.metrics import dp, sp
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
import threading
import supabase_config as fb
import session
import time
from views.utils_avatar import set_avatar_image

VIDEO_TIMEOUT_SEGUNDOS = 600


class DashboardScreen(Screen):

    _admin_taps = 0
    _admin_last_tap = 0
    _cargando_dashboard = False
    _checking_video = False
    _video_event = None
    _avisos_event = None
    _checking_avisos = False

    def on_tap_titulo(self):
        """Easter egg: 7 taps rapidos en LEGAL APP abre el panel admin."""
        import time as _time
        ahora = _time.time()
        if ahora - self._admin_last_tap > 2:
            self._admin_taps = 0
        self._admin_last_tap = ahora
        self._admin_taps += 1
        if self._admin_taps >= 7:
            self._admin_taps = 0
            self.manager.current = "admin_panel"

    def on_enter(self):
        user = session.current_user
        if user:
            self.ids.lbl_bienvenida.text = user.get('username', '') or user.get('nombre', '') or user.get('email', '')
            set_avatar_image(
                self.ids.img_avatar_inicio,
                user.get('foto_url', ''),
                user.get('email', '')
            )

            if platform == "android":
                try:
                    from fcm_service import obtener_fcm_token
                    Clock.schedule_once(lambda dt: obtener_fcm_token(), 1)
                except Exception as e:
                    print(f"Error refrescando FCM dashboard: {e}")

            self._cargar_dashboard_async(user.get('uid'))

        if self._video_event is None:
            self._video_event = Clock.schedule_interval(self.check_videollamada, 2)
        self.check_videollamada(0)

        if self._avisos_event is None:
            self._avisos_event = Clock.schedule_interval(self._actualizar_badge_avisos, 20)
        self._actualizar_badge_avisos(0)

    def on_leave(self):
        if self._video_event is not None:
            self._video_event.cancel()
            self._video_event = None
        if self._avisos_event is not None:
            self._avisos_event.cancel()
            self._avisos_event = None

    def _actualizar_badge_avisos(self, dt):
        user = session.current_user
        if not user or self._checking_avisos:
            return

        uid = user.get('uid')
        self._checking_avisos = True

        def _check():
            total = 0
            try:
                total = fb.contar_avisos_no_leidos(uid, 'cliente')
            except Exception as e:
                print(f"ERROR contar_avisos_no_leidos: {e}")
            finally:
                Clock.schedule_once(lambda dt, n=total: self._aplicar_badge_avisos(n), 0)

        threading.Thread(target=_check, daemon=True).start()

    def _aplicar_badge_avisos(self, total):
        self._checking_avisos = False
        if "lbl_badge_avisos" in self.ids:
            self.ids.lbl_badge_avisos.text = str(total) if total > 0 else "0"

    def check_videollamada(self, dt):
        user = session.current_user
        if not user or self._checking_video:
            return

        uid = user.get('uid')
        self._checking_video = True

        def _check():
            videollamada = None
            try:
                consultas = fb.obtener_consultas_usuario(uid, 'cliente')

                for cid, cdata in consultas:
                    estado = str(cdata.get('estado') or '')
                    tipo = cdata.get('tipo_servicio', 'chat') or 'chat'
                    iniciada = (
                        tipo == "video"
                        and estado in ["en_curso", "videollamada"]
                        and fb.consulta_tiene_videollamada_iniciada(cid)
                    )

                    if estado == 'videollamada' or iniciada:
                        created_at = cdata.get('created_at')
                        if created_at:
                            try:
                                from datetime import datetime
                                if hasattr(created_at, 'timestamp'):
                                    ts = created_at
                                else:
                                    ts = datetime.strptime(str(created_at), "%Y-%m-%d %H:%M:%S")
                                ahora = datetime.now()
                                diff = (ahora - ts).total_seconds()
                                if diff > VIDEO_TIMEOUT_SEGUNDOS:
                                    continue
                            except Exception as e:
                                print("ERROR VIDEO:", e)
                        videollamada = (cid, cdata)
                        break
            except Exception as e:
                print(f"ERROR check_videollamada: {e}")
            finally:
                Clock.schedule_once(lambda dt, data=videollamada: self._aplicar_check_video(data), 0)

        threading.Thread(target=_check, daemon=True).start()

    def _cargar_dashboard_async(self, uid):
        if not uid or self._cargando_dashboard:
            return

        self._cargando_dashboard = True

        def _load():
            user_data = None
            try:
                user_data = fb.obtener_usuario(uid) or session.current_user
            except Exception as e:
                print(f"ERROR cargar_dashboard: {e}")
            finally:
                Clock.schedule_once(lambda dt, data=user_data: self._aplicar_dashboard(data), 0)

        threading.Thread(target=_load, daemon=True).start()

    def _aplicar_dashboard(self, user_data):
        self._cargando_dashboard = False
        if not user_data:
            return

        session.current_user = user_data
        session.guardar()
        self.ids.lbl_bienvenida.text = user_data.get('username', '') or user_data.get('nombre', '') or user_data.get('email', '')
        set_avatar_image(
            self.ids.img_avatar_inicio,
            user_data.get('foto_url', ''),
            user_data.get('email', '')
        )

    def _aplicar_check_video(self, videollamada):
        self._checking_video = False

        if not videollamada:
            if "btn_video" in self.ids:
                self.ids.btn_video.opacity = 0
                self.ids.btn_video.disabled = True
            return

        cid, cdata = videollamada

        if "btn_video" in self.ids:
            self.ids.btn_video.opacity = 1
            self.ids.btn_video.disabled = False
            self.ids.btn_video.consulta_id = cid

    def ir_video(self, consulta_id):
        if not consulta_id:
            consulta_id = getattr(self.ids.btn_video, 'consulta_id', 0)
        if not consulta_id:
            return
        session.current_consulta_id = consulta_id
        self.manager.current = "videollamada"

    def nueva_consulta(self):
        session.provincia_busqueda = None
        session.ciudad_busqueda = None
        session.area_legal = None
        self.manager.current = "ubicacion"

    def ver_historial(self):
        self.manager.current = "historial"

    def ir_perfil(self):
        self.manager.current = "perfil_cliente"

    def ver_notificaciones(self):
        user = session.current_user or {}
        uid = user.get("uid")
        if not uid:
            return

        if "lbl_badge_avisos" in self.ids:
            self.ids.lbl_badge_avisos.text = "0"
        threading.Thread(target=lambda: fb.marcar_avisos_vistos(uid), daemon=True).start()

        consultas = fb.obtener_consultas_usuario(uid, "cliente")
        items = []
        for cid, consulta in consultas[:8]:
            tipo = str(consulta.get("tipo_servicio", "chat") or "chat").upper()
            estado = str(consulta.get("estado", "pendiente") or "pendiente").replace("_", " ").upper()
            abogado = consulta.get("abogado_email", "Abogado")
            items.append(f"{tipo} - {estado}\n{abogado}")
            mensajes = fb.obtener_mensajes(cid)
            if mensajes:
                ultimo = mensajes[-1]
                texto = str(ultimo.get("texto") or "").strip()
                if texto:
                    preview = texto[:44] + "..." if len(texto) > 44 else texto
                    items.append(f"Mensaje reciente\n{preview}")

        layout = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        with layout.canvas.before:
            from kivy.graphics import Color, Rectangle
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

        if not items:
            msg = Label(
                text="No hay notificaciones por ahora.",
                size_hint_y=None,
                height=dp(56),
                font_size=sp(13),
                color=(0.45, 0.50, 0.58, 1),
                halign="center",
                valign="middle",
            )
            msg.bind(size=lambda s, *_: setattr(s, "text_size", s.size))
            contenido.add_widget(msg)
        else:
            for texto in items:
                lbl = Label(
                    text=texto,
                    size_hint_y=None,
                    height=dp(56),
                    font_size=sp(12),
                    color=(0.16, 0.12, 0.24, 1),
                    halign="left",
                    valign="middle",
                )
                lbl.bind(size=lambda s, *_: setattr(s, "text_size", (s.width, None)))
                contenido.add_widget(lbl)

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

    def cerrar_sesion(self):
        session.current_user = None
        try:
            ls = self.manager.get_screen("login")
            ls.ids.email.text = ""
            ls.ids.password.text = ""
            ls.ids.error.text = ""
        except Exception:
            pass
        self.manager.current = "login"
