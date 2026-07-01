from kivy.uix.screenmanager import Screen


class TermsScreen(Screen):

    pantalla_anterior = "register"

    def on_pre_enter(self):
        # Detectar desde donde se abrio
        if hasattr(self, 'manager'):
            prev = self.manager.current
            if prev in ("register", "register_abogado"):
                self.pantalla_anterior = prev

        self.ids.terms_label.text = """LEGALAPP - TERMINOS, CONDICIONES Y BASES DEL SERVICIO

1. OBJETO DEL SERVICIO
Legal App es una plataforma digital que conecta clientes con abogados independientes matriculados para consultas por chat, videollamada o modalidad urgente. Legal App no reemplaza el criterio profesional del abogado ni actua como estudio juridico.

2. REGISTRO Y CUENTAS
Cada usuario debe registrarse con datos reales, completos y actualizados. El usuario es responsable de la confidencialidad de su cuenta, su contrasena y el uso que se haga desde ella.

3. VALIDACION Y APROBACION DE ABOGADOS
Los abogados deben verificar su email, completar sus datos profesionales y, cuando corresponda, abonar la suscripcion aplicable. La aprobacion final puede quedar sujeta a control administrativo de matricula, identidad o documentacion.

4. SUSCRIPCIONES Y ESPECIALIDADES
La suscripcion profesional habilita el uso de la plataforma bajo las condiciones vigentes al momento del alta. La primera especialidad puede estar incluida segun el plan y las adicionales pueden generar cargos extra. Las suscripciones abonadas no son reembolsables salvo obligacion legal aplicable.

5. CONSULTAS Y PAGOS
Los pagos de consultas y suscripciones se procesan mediante MercadoPago u otros medios habilitados. Una consulta se considera activa cuando el pago queda validado en la plataforma. Los importes, comisiones y reglas de retiro pueden actualizarse y mostrarse dentro de la app.

6. HONORARIOS Y RETIROS
Los abogados pueden solicitar retiro de honorarios sujetos a validacion administrativa. Legal App puede retener, pausar o rechazar retiros ante sospecha de fraude, contracargo, incumplimiento o datos bancarios inconsistentes.

7. MENSAJERIA, ARCHIVOS Y VIDEOLLAMADAS
La plataforma permite intercambio de mensajes, audios, imagenes, PDF, documentos y enlaces de videollamada. El usuario es responsable del contenido que sube, comparte o envia. Esta prohibido cargar contenido ilicito, ofensivo, fraudulento o que vulnere derechos de terceros.

8. RESPONSABILIDAD PROFESIONAL
Cada abogado actua por cuenta propia y es exclusivo responsable por sus opiniones, respuestas, estrategia, trato con clientes y cumplimiento normativo de su actividad profesional. Legal App no garantiza resultados juridicos ni reemplaza asesoramiento presencial cuando sea necesario.

9. DISPONIBILIDAD Y SOPORTE
Aunque buscamos continuidad operativa, Legal App no garantiza disponibilidad absoluta, ausencia de demoras, caidas, errores externos o interrupciones de terceros proveedores.

10. SUSPENSION O BAJA
Legal App puede suspender, limitar o cerrar cuentas por incumplimientos, fraude, uso abusivo, suplantacion, falta de pago o riesgo operativo. El usuario tambien puede pedir la eliminacion de su cuenta desde los canales habilitados.

11. PRIVACIDAD
El uso de la plataforma implica la aceptacion de la Politica de Privacidad vigente. Determinados datos se comparten con proveedores tecnicos necesarios para operar la app.

12. CAMBIOS EN LOS TERMINOS
Legal App puede actualizar estos terminos, condiciones y bases para reflejar mejoras, nuevas funciones, cambios regulatorios o ajustes operativos. La version vigente sera la publicada en la app.

13. LEY APLICABLE
Estos terminos se interpretan conforme a las leyes de la Republica Argentina, sin perjuicio de los derechos del consumidor que resulten aplicables.

Version 1.1 - 2026"""

    def volver(self):
        self.manager.current = self.pantalla_anterior
