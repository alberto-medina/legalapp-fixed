import os
import shutil
import time
import threading
import json

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.core.window import Window
from kivy.uix.textinput import TextInput
from kivy.resources import resource_find

import supabase_config as fb
import session
from views.form_keyboard import FormKeyboardMixin
from views.utils_avatar import get_avatar_source, set_avatar_image

FOTO_DIR = "assets/fotos"
MAX_FOTO_MB = 5
EXTENSIONES_PERMITIDAS = ['.png', '.jpg', '.jpeg', '.webp']
RATING_FONT = resource_find("data/fonts/DejaVuSans.ttf") or "data/fonts/DejaVuSans.ttf"


def _copiar_foto(origen):
    os.makedirs(FOTO_DIR, exist_ok=True)
    ext = os.path.splitext(origen)[1].lower()
    safe = session.get_email().replace("@", "_").replace(".", "_") if session.get_email() else "user"
    version = int(time.time())
    dest = os.path.join(FOTO_DIR, f"perfil_{safe}_{version}{ext}")
    shutil.copy2(origen, dest)
    return dest

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


class PerfilScreen(FormKeyboardMixin, Screen):

    _chooser_abierto = False
    _cargando_datos = False
    _precio_especialidad_extra = 10000

    def on_enter(self):
        """UN SOLO on_enter: carga datos + bindea key handler."""
        Window.bind(on_key_down=self.on_key_down)
        self._setup_form_keyboard("perfil_scroll")

        if not session.current_user:
            return
        if "perfil_scroll" in self.ids:
            self.ids.perfil_scroll.opacity = 0
        self._ocultar_seccion_abogado()

        if self._cargando_datos:
            return
        self._cargando_datos = True

        uid = session.get_uid()

        def _fetch():
            user_data = fb.obtener_usuario(uid)
            Clock.schedule_once(lambda dt, data=user_data: self._aplicar_datos_usuario(data), 0)

        threading.Thread(target=_fetch, daemon=True).start()

    def on_leave(self):
        Window.unbind(on_key_down=self.on_key_down)
        self._chooser_abierto = False
        self._cargando_datos = False

    def on_key_down(self, window, key, scancode, codepoint, modifier):
        """Back button Android: no salir si filechooser abierto."""
        if key == 27 and self._chooser_abierto:
            self._chooser_abierto = False
            return True
        return False

    def _mostrar_seccion(self):
        """Muestra la seccion abogado y mantiene su altura sincronizada."""
        sec = self.ids.seccion_abogado
        if not getattr(sec, "_perfil_height_bound", False):
            sec.bind(minimum_height=lambda widget, value: self._sync_seccion_abogado_height())
            sec._perfil_height_bound = True
        self._sync_seccion_abogado_height()

    def _sync_seccion_abogado_height(self):
        sec = self.ids.seccion_abogado
        sec.height = sec.minimum_height if sec.opacity else 0

    def _ocultar_seccion_abogado(self):
        self.ids.seccion_abogado.opacity = 0
        self.ids.seccion_abogado.disabled = True
        self.ids.seccion_abogado.height = 0

    def _aplicar_datos_usuario(self, user_data):
        self._cargando_datos = False
        if not user_data:
            if "perfil_scroll" in self.ids:
                self.ids.perfil_scroll.opacity = 1
            return

        session.current_user = user_data
        session.guardar()

        nombre = user_data.get('username', '') or user_data.get('nombre', '')
        telefono = user_data.get('telefono', '')
        foto = user_data.get('foto_url', '')
        rol = user_data.get('rol', 'cliente')

        self.ids.nombre.text = nombre or ""
        self.ids.telefono.text = telefono or ""
        self.ids.foto.text = foto or ""

        foto_local = self._obtener_foto_local()
        if foto_local and os.path.exists(foto_local):
            self._cargar_imagen(foto_local)
        else:
            self._cargar_imagen(foto, user_data.get('email', ''))

        if rol == "abogado":
            self.ids.lbl_rol_badge.text = "ABOGADO / A"
            self.ids.lbl_rol_badge.color = (1, 1, 1, 1)
            self.ids.seccion_abogado.opacity = 1
            self.ids.seccion_abogado.disabled = False
            Clock.schedule_once(lambda dt: self._mostrar_seccion(), 0.05)

            self.ids.matricula.text = user_data.get('matricula', '') or ""
            self.ids.experiencia.text = user_data.get('experiencia', '') or ""
            self.ids.descripcion.text = user_data.get('descripcion', '') or ""
            self.ids.cuenta_bancaria.text = user_data.get('cuenta_bancaria', '') or ""
            self.ids.provincia.text = user_data.get('provincia', '') or ""
            self.ids.ciudad.text = user_data.get('ciudad', '') or ""

            import json
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
        else:
            self.ids.lbl_rol_badge.text = "CLIENTE"
            self.ids.lbl_rol_badge.color = (0.60, 0.85, 1.00, 1)
            self._ocultar_seccion_abogado()
            self.ids.matricula.text = ""
            self.ids.experiencia.text = ""
            self.ids.descripcion.text = ""
            self.ids.cuenta_bancaria.text = ""
            self.ids.provincia.text = ""
            self.ids.ciudad.text = ""
            self.ids.lbl_especialidades.text = "-"
            self.ids.lbl_suscripcion.text = "-"
            self.ids.lbl_promedio.text = "-"
            self.ids.resenas_box.clear_widgets()

        if "perfil_scroll" in self.ids:
            self.ids.perfil_scroll.opacity = 1

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

    def _cargar_imagen(self, source, email=None):
        img = self.ids.img_avatar
        Clock.schedule_once(lambda dt, src=source, mail=email: self._set_source(img, src, mail), 0)

    def _set_source(self, img, source, email=None):
        set_avatar_image(img, source, email or session.get_email())

    def _obtener_foto_local(self):
        email = session.get_email()
        if not email:
            return None
        safe = email.replace("@", "_").replace(".", "_")
        candidatos = []
        if not os.path.isdir(FOTO_DIR):
            return None

        for nombre in os.listdir(FOTO_DIR):
            nombre_lower = nombre.lower()
            if not nombre_lower.startswith(f"perfil_{safe}".lower()):
                continue
            if not any(nombre_lower.endswith(ext) for ext in EXTENSIONES_PERMITIDAS):
                continue
            path = os.path.join(FOTO_DIR, nombre)
            if os.path.isfile(path):
                candidatos.append(path)

        if not candidatos:
            return None

        candidatos.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return candidatos[0]

    def elegir_foto(self):
        self._chooser_abierto = True
        try:
            from android import activity
            from jnius import autoclass
            from android import mActivity

            Intent = autoclass('android.content.Intent')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')

            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.setType("image/*")
            intent.addCategory(Intent.CATEGORY_OPENABLE)

            def on_activity_result(request_code, result_code, data):
                self._chooser_abierto = False
                if result_code == -1 and data:
                    uri = data.getData()
                    if uri:
                        try:
                            ContentResolver = autoclass('android.content.ContentResolver')
                            cursor = mActivity.getContentResolver().query(uri, None, None, None, None)
                            if cursor and cursor.moveToFirst():
                                idx = cursor.getColumnIndex("_data")
                                if idx >= 0:
                                    path = cursor.getString(idx)
                                    if path:
                                        Clock.schedule_once(lambda dt, p=path: self._foto_seleccionada([p]), 0)
                                        return
                            import tempfile
                            inp = mActivity.getContentResolver().openInputStream(uri)
                            fd, tmp_path = tempfile.mkstemp(suffix='.jpg', dir=FOTO_DIR)
                            with os.fdopen(fd, 'wb') as f:
                                buf = bytearray(4096)
                                while True:
                                    n = inp.read(buf)
                                    if n <= 0:
                                        break
                                    f.write(buf[:n])
                            inp.close()
                            Clock.schedule_once(lambda dt, p=tmp_path: self._foto_seleccionada([p]), 0)
                        except Exception as e:
                            print("ERROR uri to path:", e)

            activity.bind(on_activity_result=on_activity_result)
            mActivity.startActivityForResult(intent, 42)
            return
        except Exception as e:
            print("Android intent falló, usando plyer:", e)

        try:
            from plyer import filechooser
            filechooser.open_file(
                on_selection=self._foto_seleccionada,
                filters=["*.png", "*.jpg", "*.jpeg", "*.webp"],
            )
        except Exception:
            self._fallback_tkinter()

    def _fallback_tkinter(self):
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            path = filedialog.askopenfilename(
                title="Elegir foto de perfil",
                filetypes=[("Imagenes", "*.png *.jpg *.jpeg *.webp"), ("Todos", "*.*")],
            )
            root.destroy()
            if path:
                self._foto_seleccionada([path])
        except Exception as e:
            print("foto error:", e)

    def _foto_seleccionada(self, selection):
        self._chooser_abierto = False
        if not selection:
            return
        try:
            origen = selection[0]
            print(f"FOTO seleccionada origen={origen}")
            ext = os.path.splitext(origen)[1].lower()
            if ext not in EXTENSIONES_PERMITIDAS:
                self._mostrar_error(f"Formato no permitido. Usa: {', '.join(EXTENSIONES_PERMITIDAS)}")
                return

            tamano_mb = os.path.getsize(origen) / (1024 * 1024)
            if tamano_mb > MAX_FOTO_MB:
                self._mostrar_error(f"La foto es muy grande. Maximo {MAX_FOTO_MB}MB")
                return

            dest = _copiar_foto(origen)
            print(f"FOTO copiada a local={dest}")
            self.ids.foto.text = dest
            self._cargar_imagen(dest)

            uid = session.get_uid()
            if uid:
                ok, url = fb.subir_foto_perfil(uid, dest)
                if ok and url:
                    self.ids.foto.text = url
                    self._cargar_imagen(url)
                    if session.current_user:
                        session.current_user['foto_url'] = url
                        session.guardar()
                    print(f"FOTO subida url={url}")
                else:
                    self._mostrar_error("La foto se guardó en el celular, pero no se pudo publicar en la nube todavía.")

        except Exception as e:
            print("ERROR foto:", e)
            self._mostrar_error("Error al cargar la foto")

    def agregar_especialidad(self):
        import json
        from views.register_abogado import ESPECIALIDADES

        user_data = fb.obtener_usuario(session.get_uid())
        especialidades_raw = user_data.get('especialidades', '[]') or '[]'
        try:
            actuales = json.loads(especialidades_raw) if isinstance(especialidades_raw, str) else especialidades_raw
        except:
            actuales = []

        disponibles = [e for e in ESPECIALIDADES if e not in actuales]
        if not disponibles:
            self._mostrar_error("Ya tenes todas las especialidades disponibles")
            return

        config = fb.obtener_configuracion() or {}
        try:
            precio_extra = int(config.get("precio_especialidad_extra", 10000))
        except:
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
                height=dp(82) if comentario else dp(56),
                padding=[dp(14), dp(8)],
                spacing=dp(2),
            )

            with card.canvas.before:
                Color(rgba=(0.97, 0.98, 1.0, 1))
                card._bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(10)])

            card.bind(
                pos=lambda w, v: setattr(w._bg, "pos", v),
                size=lambda w, v: setattr(w._bg, "size", v),
            )
            card.add_widget(Label(
                text=f"{_rating_text(puntaje)}  {_fecha_resena(fecha)}",
                font_name=RATING_FONT,
                font_size="13sp",
                bold=True,
                color=(0.80, 0.55, 0.05, 1),
                halign="left",
                valign="middle",
                text_size=(None, None),
            ))

            if comentario:
                card.add_widget(Label(
                    text=f'"{comentario}"',
                    font_size="12sp",
                    color=(0.35, 0.40, 0.52, 1),
                    halign="left",
                    valign="middle",
                    text_size=(None, None),
                ))

            box.add_widget(card)

    def _mostrar_error(self, mensaje):
        popup = Popup(
            title='Error',
            content=Label(text=mensaje, color=(0.9, 0.2, 0.2, 1)),
            size_hint=(0.8, 0.3)
        )
        popup.open()

    def borrar_cuenta_popup(self):
        user = session.current_user or {}
        email = user.get("email", "")

        layout = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))
        info = Label(
            text=(
                "Esta accion eliminara tu cuenta y tus datos.\n"
                "Escribe BORRAR para confirmar."
            ),
            halign='center',
            valign='middle',
            color=(0.20, 0.12, 0.18, 1),
            size_hint_y=None,
            height=dp(64),
        )
        info.bind(size=lambda s, *_: setattr(s, 'text_size', s.size))

        detalle = Label(
            text=email,
            halign='center',
            valign='middle',
            color=(0.55, 0.58, 0.65, 1),
            size_hint_y=None,
            height=dp(24),
        )
        detalle.bind(size=lambda s, *_: setattr(s, 'text_size', s.size))

        confirmacion = TextInput(
            hint_text='Escribe BORRAR',
            multiline=False,
            size_hint_y=None,
            height=dp(48),
        )

        error = Label(
            text='',
            color=(0.90, 0.25, 0.25, 1),
            size_hint_y=None,
            height=dp(22),
        )
        error.bind(size=lambda s, *_: setattr(s, 'text_size', s.size))

        botones = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        btn_cancelar = Button(
            text='Cancelar',
            background_normal='',
            background_color=(0.90, 0.90, 0.96, 1),
            color=(0.24, 0.17, 0.55, 1),
            bold=True
        )
        btn_borrar = Button(
            text='Borrar cuenta',
            background_normal='',
            background_color=(0.86, 0.20, 0.20, 1),
            color=(1, 1, 1, 1),
            bold=True
        )
        botones.add_widget(btn_cancelar)
        botones.add_widget(btn_borrar)

        layout.add_widget(info)
        layout.add_widget(detalle)
        layout.add_widget(confirmacion)
        layout.add_widget(error)
        layout.add_widget(botones)

        popup = Popup(
            title='Borrar cuenta',
            content=layout,
            size_hint=(0.88, None),
            height=dp(320),
            auto_dismiss=False
        )

        btn_cancelar.bind(on_release=popup.dismiss)

        def _confirmar(_):
            if confirmacion.text.strip().upper() != "BORRAR":
                error.text = "Debes escribir BORRAR para continuar"
                return
            btn_borrar.disabled = True
            btn_cancelar.disabled = True
            error.color = (0.45, 0.50, 0.58, 1)
            error.text = "Eliminando cuenta..."
            self._eliminar_cuenta(popup, error)

        btn_borrar.bind(on_release=_confirmar)
        popup.open()

    def _eliminar_cuenta(self, popup, error_label):
        user = session.current_user or {}
        uid = user.get("uid")
        email = user.get("email", "")
        foto_url = user.get("foto_url", "")
        id_token = getattr(session, "id_token", None)
        refresh_token = getattr(session, "refresh_token", None)

        def _worker():
            ok, mensaje = fb.eliminar_cuenta_completa(
                uid,
                email=email,
                foto_url=foto_url,
                id_token=id_token,
                refresh_token=refresh_token,
            )
            Clock.schedule_once(lambda dt, res_ok=ok, msg=mensaje: self._post_eliminar_cuenta(res_ok, msg, popup, error_label), 0)

        threading.Thread(target=_worker, daemon=True).start()

    def _post_eliminar_cuenta(self, ok, mensaje, popup, error_label):
        if ok:
            try:
                popup.dismiss()
            except Exception:
                pass
            session.cerrar_sesion()
            self.manager.current = "login"
            return

        error_label.color = (0.90, 0.25, 0.25, 1)
        error_label.text = mensaje or "No se pudo borrar la cuenta"

    def guardar(self):
        uid = session.get_uid()
        if not uid:
            return

        datos = {
            'username': self.ids.nombre.text.strip(),
            'telefono': self.ids.telefono.text.strip(),
        }

        foto_valor = self.ids.foto.text.strip()
        if foto_valor.startswith(("http://", "https://")):
            datos['foto_url'] = foto_valor

        if not self.ids.seccion_abogado.disabled:
            datos.update({
                'matricula': self.ids.matricula.text.strip(),
                'experiencia': self.ids.experiencia.text.strip(),
                'descripcion': self.ids.descripcion.text.strip(),
                'cuenta_bancaria': self.ids.cuenta_bancaria.text.strip(),
                'provincia': self.ids.provincia.text.strip(),
                'ciudad': self.ids.ciudad.text.strip(),
            })

        fb.actualizar_usuario(uid, datos)

        if session.current_user:
            session.current_user['username'] = datos['username']
            if 'foto_url' in datos:
                session.current_user['foto_url'] = datos['foto_url']
            session.guardar()

        self.volver()

    def volver(self):
        if session.es_abogado():
            self.manager.current = "abogado_panel"
        else:
            self.manager.current = "dashboard"
