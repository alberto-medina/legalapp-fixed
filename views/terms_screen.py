from kivy.uix.screenmanager import Screen


class TermsScreen(Screen):

    def on_pre_enter(self):

        self.ids.terms_label.text = """
LEGALAPP - TÉRMINOS Y CONDICIONES

1. Servicio
LegalApp conecta clientes con abogados independientes.

2. Responsabilidad
Los abogados son responsables de sus servicios profesionales.

3. Pagos
Los pagos pueden incluir comisiones de la plataforma.

4. Datos
El usuario acepta el tratamiento de datos personales.

5. Conducta
Está prohibido el uso fraudulento o ilegal de la app.

6. Modificaciones
LegalApp puede modificar estos términos en cualquier momento.
"""

    def aceptar_terminos(self):

        if self.ids.aceptar_check.active:
            self.manager.current = "register"
        else:
            print("Debe aceptar los términos")


class PrivacyScreen(Screen):

    def on_pre_enter(self):

        self.ids.privacy_label.text = """
POLÍTICA DE PRIVACIDAD

- Recopilamos nombre, email y ubicación.

- Los datos se usan para conectar clientes con abogados.

- No vendemos datos personales.

- Los pagos son procesados mediante plataformas seguras.

- Los datos pueden almacenarse en Firebase y Supabase.
"""