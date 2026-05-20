import session
import firebase_config as fb
from kivy.uix.screenmanager import Screen
from kivy.utils import platform


def _get_sala_url(consulta_id):
    """
    Genera URL de Jitsi Meet optimizada para mobile.
    Configuracion:
    - startWithVideoMuted=false: camara encendida al entrar
    - startWithAudioMuted=false: microfono encendido al entrar
    - prejoinPageEnabled=false: salta la pantalla de pre-join
    - requireDisplayName=false: no pide nombre
    - disableDeepLinking=true: no redirige a app nativa de Jitsi
    """
    sala = f"legalapp-consulta-{consulta_id}"
    config = (
        "config.startWithVideoMuted=false&"
        "config.startWithAudioMuted=false&"
        "config.prejoinPageEnabled=false&"
        "config.requireDisplayName=false&"
        "config.disableDeepLinking=true&"
        "config.enableWelcomePage=false"
    )
    return f"https://meet.jit.si/{sala}?{config}"


def _abrir_url(url):
    """Abre URL en navegador externo (Android) o webbrowser (desktop)."""
    try:
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        activity.startActivity(intent)
        return
    except Exception:
        pass
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception as e:
        print("No se pudo abrir video:", e)


def _copiar_al_portapapeles(texto):
    """Copia texto al portapapeles del dispositivo."""
    try:
        if platform == 'android':
            from jnius import autoclass
            Context = autoclass('android.content.Context')
            ClipboardManager = autoclass('android.content.ClipboardManager')
            ClipData = autoclass('android.content.ClipData')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            clipboard = activity.getSystemService(Context.CLIPBOARD_SERVICE)
            clip = ClipData.newPlainText("Sala Jitsi", texto)
            clipboard.setPrimaryClip(clip)
            return True
    except Exception as e:
        print("Error copiando:", e)
    return False


class VideollamadaScreen(Screen):

    def on_enter(self):
        cid = session.current_consulta_id
        if not cid:
            self.ids.lbl_sala.text = "Consulta no encontrada"
            self.ids.btn_unirse.disabled = True
            self.ids.btn_unirse.opacity = 0.4
            self.ids.btn_copiar.disabled = True
            self.ids.btn_copiar.opacity = 0
            return

        consulta = fb.obtener_consulta(cid)
        if not consulta:
            self.ids.lbl_sala.text = "Consulta no encontrada"
            self.ids.btn_unirse.disabled = True
            self.ids.btn_unirse.opacity = 0.4
            self.ids.btn_copiar.disabled = True
            self.ids.btn_copiar.opacity = 0
            return

        abogado_email = consulta.get('abogado_email', '')
        cliente_email = consulta.get('cliente_email', '')
        tipo = consulta.get('tipo_servicio', '')
        estado = consulta.get('estado', '')

        es_abogado = session.es_abogado()
        otro = cliente_email if es_abogado else abogado_email

        self.ids.lbl_con_quien.text = f"Videollamada con: {otro}"

        if estado != "videollamada":
            self.ids.lbl_sala.text = "El abogado todavia no inicio la videollamada"
            self.ids.lbl_url.text = ""
            self.ids.btn_unirse.disabled = True
            self.ids.btn_unirse.opacity = 0.35
            self.ids.btn_copiar.disabled = True
            self.ids.btn_copiar.opacity = 0
            self._url = None
            return

        url = _get_sala_url(cid)
        self.ids.lbl_sala.text = f"Sala: legalapp-consulta-{cid}"
        self.ids.lbl_url.text = url
        self.ids.btn_unirse.disabled = False
        self.ids.btn_unirse.opacity = 1
        self.ids.btn_copiar.disabled = False
        self.ids.btn_copiar.opacity = 1
        self._url = url

    def unirse(self):
        if not self._url:
            return
        _abrir_url(self._url)

    def copiar_link(self):
        if not self._url:
            return
        if _copiar_al_portapapeles(self._url):
            self.ids.lbl_sala.text = "✓ Link copiado al portapapeles"
        else:
            self.ids.lbl_sala.text = "No se pudo copiar el link"

    def volver(self):
        self.manager.current = "chat"