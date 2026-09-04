import os
import shutil
import threading
import time

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.core.window import Window

import supabase_config as fb
import session
from views.form_keyboard import FormKeyboardMixin
from views.utils_avatar import set_avatar_image

FOTO_DIR = "assets/fotos"
MAX_FOTO_MB = 5
EXTENSIONES_PERMITIDAS = ['.png', '.jpg', '.jpeg', '.webp']


def _copiar_foto(origen):
    os.makedirs(FOTO_DIR, exist_ok=True)
    ext = os.path.splitext(origen)[1].lower()
    safe = session.get_email().replace("@", "_").replace(".", "_") if session.get_email() else "user"
    version = int(time.time())
    dest = os.path.join(FOTO_DIR, f"perfil_{safe}_{version}{ext}")
    shutil.copy2(origen, dest)
    return dest


class PerfilBaseMixin(FormKeyboardMixin):
    """Logica compartida entre PerfilClienteScreen y PerfilAbogadoScreen: carga/guardado
    genericos, foto de perfil (incluye el fix de foco/scroll al volver del selector,
    ver elegir_foto/_limpiar_foco_inputs mas abajo), y borrado de cuenta.
    Cada subclase implementa _aplicar_datos_rol()/_datos_extra_guardar()/volver()."""

    _chooser_abierto = False
    _cargando_datos = False
    _scroll_event = None

    def on_enter(self):
        Window.bind(on_key_down=self.on_key_down)
        self._setup_form_keyboard("perfil_scroll")

        if not session.current_user:
            return
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
        self._teardown_form_keyboard()

    def on_key_down(self, window, key, scancode, codepoint, modifier):
        """Back button Android: no salir si filechooser abierto."""
        if key == 27 and self._chooser_abierto:
            self._chooser_abierto = False
            return True
        return False

    def _aplicar_datos_usuario(self, user_data):
        self._cargando_datos = False
        if not user_data:
            return

        session.current_user = user_data
        session.guardar()

        self.ids.nombre.text = user_data.get('username', '') or user_data.get('nombre', '') or ""
        self.ids.telefono.text = user_data.get('telefono', '') or ""
        self.ids.foto.text = user_data.get('foto_url', '') or ""

        foto_local = self._obtener_foto_local()
        if foto_local and os.path.exists(foto_local):
            self._cargar_imagen(foto_local)
        else:
            self._cargar_imagen(user_data.get('foto_url', ''), user_data.get('email', ''))

        self._aplicar_datos_rol(user_data)

    def _aplicar_datos_rol(self, user_data):
        raise NotImplementedError

    def _cargar_imagen(self, source, email=None, force=False):
        img = self.ids.img_avatar
        Clock.schedule_once(lambda dt, src=source, mail=email, f=force: self._set_source(img, src, mail, f), 0)

    def _set_source(self, img, source, email=None, force=False):
        set_avatar_image(img, source, email or session.get_email(), force=force)

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
        # Confirmado por el usuario: el freeze al volver del selector pasaba
        # en CLIENTE pero no en ABOGADO, con el mismo boton/campo (compartidos
        # por los dos roles en la pantalla unica de antes) — asi que no era un
        # tema de memoria/CPU del telefono en si. Causa real:
        # perfil_scroll.scroll_y es una fraccion del contenido total; con
        # poco contenido (como el perfil de cliente) una sacudida de layout
        # es una fraccion grande y se nota como "se mueve todo". Si ademas
        # queda _active_input con foco viejo, cada parpadeo de altura de
        # teclado durante la transicion dispara otro scroll_to() de mas. Se
        # limpia el foco activo antes de abrir el selector para no arrastrar
        # ese estado (ver project_legalapp_cambiar_foto_root_cause en memoria).
        self._limpiar_foco_inputs()
        if "perfil_scroll" in self.ids:
            self.ids.perfil_scroll.disabled = True
        try:
            from android import activity
            from jnius import autoclass
            from android import mActivity

            Intent = autoclass('android.content.Intent')
            # pyjnius no expone clases Java anidadas como atributos
            # encadenados (MediaStore.Images.Media no existe asi) — hay que
            # pedir la clase anidada completa con "$". Sin esto, esta linea
            # tiraba AttributeError SIEMPRE y el flujo caia de una al
            # fallback de plyer (confirmado con logcat: "type object
            # 'android.provider.MediaStore' has no attribute 'Images'").
            MediaStoreImagesMedia = autoclass('android.provider.MediaStore$Images$Media')

            intent = Intent(Intent.ACTION_PICK, MediaStoreImagesMedia.EXTERNAL_CONTENT_URI)
            intent.setType("image/*")

            def on_activity_result(request_code, result_code, data):
                # Cada llamada a elegir_foto() registra un listener nuevo sin
                # sacar el anterior — si se toco "Cambiar foto" mas de una vez
                # en la misma sesion de la app, se acumulan y todos disparan
                # juntos cuando vuelve un resultado (confirmado con logcat:
                # FOTO seleccionada/copiada duplicado para una sola eleccion).
                # Se desregistra este mismo listener apenas se usa, para que
                # cada uno dispare como maximo una vez.
                activity.unbind(on_activity_result=on_activity_result)
                self._chooser_abierto = False
                # Con logcat se vio que al volver el foco salta solo por
                # varios TextInput distintos en cadena (hasta 7 campos en
                # ~6s) sin que nadie los toque — se corta esa cadena apenas
                # se recupera el control, ademas de al abrir el selector.
                self._limpiar_foco_inputs()
                self._reactivar_perfil_scroll()
                if result_code == -1 and data:
                    uri = data.getData()
                    if uri:
                        try:
                            # Antes se intentaba primero leer la ruta cruda
                            # via la columna "_data" del ContentResolver y
                            # copiarla con I/O de archivo normal — confirmado
                            # con logcat que en Android moderno (scoped
                            # storage) esa ruta cruda da PermissionError aunque
                            # la query la devuelva. openInputStream(uri) usa
                            # el permiso temporal que el selector le otorga a
                            # la app sobre esa URI puntual, sin depender de
                            # READ_MEDIA_IMAGES/READ_EXTERNAL_STORAGE en
                            # runtime (que la app nunca pide).
                            import tempfile
                            os.makedirs(FOTO_DIR, exist_ok=True)
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
            # plyer puede disparar este callback fuera del hilo principal de
            # Kivy (confirmado con logcat: "Cannot create graphics
            # instruction outside the main Kivy thread" al intentar abrir un
            # popup de error desde aca) — se despacha via Clock para que
            # _foto_seleccionada (y todo lo que llama, como _mostrar_error)
            # corra siempre en el hilo principal.
            filechooser.open_file(
                on_selection=lambda selection: Clock.schedule_once(lambda dt: self._foto_seleccionada(selection), 0),
                filters=["*.png", "*.jpg", "*.jpeg", "*.webp"],
            )
        except Exception:
            self._reactivar_perfil_scroll()
            self._fallback_tkinter()

    def _limpiar_foco_inputs(self):
        # Con logcat se confirmo que al volver del selector el foco puede
        # saltar solo por varios TextInput distintos en cadena (hasta 7
        # campos en ~6s, cada uno disparando su propio scroll_to()) sin que
        # el usuario toque nada. Se corta la cadena sacando el foco de TODOS
        # los campos (no solo el activo) y cancelando cualquier scroll
        # pendiente, tanto al abrir el selector como al volver de el.
        if self._scroll_event is not None:
            self._scroll_event.cancel()
            self._scroll_event = None
        self._active_input = None
        for widget in self._iter_text_inputs():
            if widget.focus:
                widget.focus = False

    def _reactivar_perfil_scroll(self, dt=None):
        # Delay para dar tiempo a que la superficie SDL/el listener de
        # teclado se estabilicen tras volver de la Activity del selector
        # (ver comentario en elegir_foto).
        if "perfil_scroll" in self.ids:
            Clock.schedule_once(lambda dt: setattr(self.ids.perfil_scroll, "disabled", False), 0.3)

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
        self._reactivar_perfil_scroll()
        if not selection or not selection[0]:
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
                self._subir_foto_async(uid, dest)

        except Exception as e:
            print("ERROR foto:", e)
            self._mostrar_error("Error al cargar la foto")

    def _subir_foto_async(self, uid, dest):
        def _worker():
            try:
                ok, url = fb.subir_foto_perfil(uid, dest)
            except Exception as e:
                print("ERROR subir_foto_async:", e)
                ok, url = False, None
            Clock.schedule_once(lambda dt, r=ok, u=url: self._post_subir_foto(r, u), 0)

        threading.Thread(target=_worker, daemon=True).start()

    def _post_subir_foto(self, ok, url):
        if ok and url:
            self.ids.foto.text = url
            self._cargar_imagen(url, force=True)
            if session.current_user:
                session.current_user['foto_url'] = url
                session.guardar()
            print(f"FOTO subida url={url}")
        else:
            self._mostrar_error("La foto se guardó en el celular, pero no se pudo publicar en la nube todavía.")

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
            height=dp(380),
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

        datos.update(self._datos_extra_guardar())

        fb.actualizar_usuario(uid, datos)

        if session.current_user:
            session.current_user['username'] = datos['username']
            if 'foto_url' in datos:
                session.current_user['foto_url'] = datos['foto_url']
            session.guardar()

        self.volver()

    def _datos_extra_guardar(self):
        return {}
