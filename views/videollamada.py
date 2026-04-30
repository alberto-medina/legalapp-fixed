"""
videollamada.py  --  Videollamada con Jitsi Meet
-------------------------------------------------
Genera una sala unica por consulta y la abre en el navegador
(o webview en Android con android.webview).

URL de sala: https://meet.jit.si/legalapp-consulta-{consulta_id}

El abogado y el cliente ven el mismo ID de sala porque ambos
acceden desde la misma consulta_id guardada en session.
"""

import session
from database import get_connection
from kivy.uix.screenmanager import Screen


def _get_sala_url(consulta_id):
    sala = f"legalapp-consulta-{consulta_id}"
    return f"https://meet.jit.si/{sala}"


def _abrir_url(url):
    """Intenta abrir en webview Android, sino usa navegador del sistema."""
    # Android
    try:
        from jnius import autoclass
        Intent   = autoclass("android.content.Intent")
        Uri      = autoclass("android.net.Uri")
        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        intent   = Intent(Intent.ACTION_VIEW, Uri.parse(url))
        activity.startActivity(intent)
        return
    except Exception:
        pass
    # Desktop fallback
    try:
        import webbrowser
        webbrowser.open(url)
    except Exception as e:
        print("No se pudo abrir video:", e)


class VideollamadaScreen(Screen):

    def on_enter(self):
        cid = session.current_consulta_id
        if not cid:
            self.ids.lbl_sala.text = "Error: consulta no encontrada"
            return

        url = _get_sala_url(cid)
        self.ids.lbl_sala.text   = f"Sala: legalapp-consulta-{cid}"
        self.ids.lbl_url.text    = url
        self._url = url

        # Obtener nombre del interlocutor
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT abogado, user_email, tipo_servicio FROM consultas WHERE id=?",
                  (cid,))
        row = c.fetchone()
        conn.close()

        if row:
            abogado, cliente, tipo = row
            es_abogado = session.current_user and session.current_user[4] == "abogado"
            otro = cliente if es_abogado else abogado
            self.ids.lbl_con_quien.text = f"Videollamada con: {otro}"

    def unirse(self):
        """Abre la sala Jitsi."""
        _abrir_url(self._url)

    def volver(self):
        if session.current_user and session.current_user[4] == "abogado":
            self.manager.current = "chat"
        else:
            self.manager.current = "chat"
