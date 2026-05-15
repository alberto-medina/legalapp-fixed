"""
videollamada.py
"""

import session
from database import get_connection
from kivy.uix.screenmanager import Screen


def _get_sala_url(consulta_id):
    sala = f"legalapp-consulta-{consulta_id}"
    return f"https://meet.jit.si/{sala}"


def _abrir_url(url):
    try:
        from jnius import autoclass

        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        activity = autoclass(
            "org.kivy.android.PythonActivity"
        ).mActivity

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


class VideollamadaScreen(Screen):

    def on_enter(self):

        cid = session.current_consulta_id

        if not cid:
            self.ids.lbl_sala.text = "Consulta no encontrada"
            self.ids.btn_unirse.disabled = True
            self.ids.btn_unirse.opacity = 0.4
            return

        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            SELECT abogado,
                   user_email,
                   tipo_servicio,
                   estado
            FROM consultas
            WHERE id=?
        """, (cid,))

        row = c.fetchone()
        conn.close()

        if not row:
            self.ids.lbl_sala.text = "Consulta no encontrada"
            self.ids.btn_unirse.disabled = True
            self.ids.btn_unirse.opacity = 0.4
            return

        abogado, cliente, tipo, estado = row

        es_abogado = (
            session.current_user
            and session.current_user[4] == "abogado"
        )

        otro = cliente if es_abogado else abogado

        self.ids.lbl_con_quien.text = (
            f"Videollamada con: {otro}"
        )

        # -------------------------------------------------
        # SOLO habilitar si el abogado inició la llamada
        # -------------------------------------------------

        if estado != "videollamada":

            self.ids.lbl_sala.text = (
                "El abogado todavia no inicio la videollamada"
            )

            self.ids.lbl_url.text = ""

            self.ids.btn_unirse.disabled = True
            self.ids.btn_unirse.opacity = 0.35

            self._url = None
            return

        # -------------------------------------------------
        # VIDEOLLAMADA ACTIVA
        # -------------------------------------------------

        url = _get_sala_url(cid)

        self.ids.lbl_sala.text = (
            f"Sala: legalapp-consulta-{cid}"
        )

        self.ids.lbl_url.text = url

        self.ids.btn_unirse.disabled = False
        self.ids.btn_unirse.opacity = 1

        self._url = url

    def unirse(self):

        if not self._url:
            return

        _abrir_url(self._url)

    def volver(self):
        self.manager.current = "chat"