from kivy.uix.screenmanager import Screen


class PrivacyScreen(Screen):

    pantalla_anterior = "register"

    def on_pre_enter(self):
        # Detectar desde donde se abrio
        if hasattr(self, 'manager'):
            prev = self.manager.current
            if prev in ("register", "register_abogado"):
                self.pantalla_anterior = prev

        self.ids.privacy_label.text = """LEGALAPP - POLITICA DE PRIVACIDAD

1. QUE DATOS RECOPILAMOS
Podemos recopilar los siguientes datos segun el tipo de cuenta y el uso de la app:
- nombre completo, email y telefono
- provincia y ciudad cuando se cargan
- datos profesionales del abogado, matricula, experiencia, biografia y especialidades
- foto de perfil
- historial de consultas, mensajes, audios, imagenes, PDF y archivos enviados en el chat
- datos de suscripciones, pagos, retiros y estados de cobro
- token tecnico de notificaciones push

2. PARA QUE USAMOS LOS DATOS
Usamos los datos para:
- crear y administrar cuentas
- validar email e identidad operativa
- conectar clientes con abogados segun especialidad, ubicacion y estado
- procesar pagos, suscripciones, honorarios y retiros
- enviar notificaciones, avisos y mensajes del servicio
- habilitar chat, videollamadas, envio de archivos y soporte
- prevenir fraude, abuso o accesos indebidos
- mejorar rendimiento, estabilidad y experiencia de uso

3. PROVEEDORES Y HERRAMIENTAS UTILIZADAS
Para operar Legal App podemos usar servicios de terceros como:
- Firebase Authentication y Firebase Cloud Messaging
- Supabase Database, Storage y Edge Functions
- MercadoPago para cobros y validacion de pagos
- servicios de videollamada integrados desde la plataforma
Estos proveedores solo acceden a la informacion necesaria para cumplir su funcion tecnica u operativa.

4. ARCHIVOS, AUDIOS E IMAGENES
Los archivos, audios, imagenes y documentos enviados dentro del chat pueden almacenarse para permitir la consulta entre las partes, el historial y el funcionamiento normal del servicio.

5. BASE LEGAL Y CONSENTIMIENTO
Al registrarte y usar Legal App aceptas esta politica y autorizas el tratamiento de tus datos para la operacion del servicio, cumplimiento contractual, seguridad y mejora de la plataforma.

6. COMPARTICION DE DATOS
No vendemos datos personales. Solo podemos compartir informacion con proveedores esenciales del servicio, con la contraparte de una consulta o cuando exista obligacion legal, regulatoria o judicial.

7. CONSERVACION
Conservamos los datos mientras la cuenta este activa o mientras resulten necesarios para prestar el servicio, resolver disputas, cumplir obligaciones legales o resguardar la seguridad operativa.

8. SEGURIDAD
Aplicamos medidas razonables de seguridad tecnica y operativa. Sin embargo, ninguna plataforma puede garantizar seguridad absoluta frente a incidentes externos o usos indebidos de terceros.

9. DERECHOS DEL USUARIO
Podes solicitar acceso, rectificacion, actualizacion o eliminacion de tus datos. Tambien podes pedir la baja de la cuenta desde las opciones disponibles o por contacto administrativo.

10. MENORES Y USO INDEBIDO
La app no esta pensada para uso no supervisado por menores de edad ni para actividades ilicitas, fraudulentas o contrarias a derecho.

11. CAMBIOS EN ESTA POLITICA
Podemos actualizar esta politica para reflejar cambios funcionales, tecnicos, legales o comerciales. La version vigente sera la publicada dentro de la app.

12. CONTACTO
Para consultas sobre privacidad o datos personales: https://www.cumbrelabs.com.ar/

Version 1.1 - 2026"""

    def volver(self):
        self.manager.current = self.pantalla_anterior
