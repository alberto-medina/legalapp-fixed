from kivy.uix.screenmanager import Screen


class PrivacyScreen(Screen):

    def on_pre_enter(self):

        self.ids.privacy_label.text = """
POLÍTICA DE PRIVACIDAD

• Recopilamos nombre, email, ubicación y datos de uso.

• Usamos los datos para conectar clientes con abogados.

• Los pagos se procesan de forma segura.

• No vendemos datos personales.

• Los datos se almacenan en Firebase y Supabase.

• El usuario puede solicitar eliminación de datos.

Al usar la app aceptás esta política.
"""