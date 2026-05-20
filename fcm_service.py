"""
fcm_service.py - Manejo de Firebase Cloud Messaging en Android
"""

from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass, cast
    from android.runnable import run_on_ui_thread

    # Clases de Android
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    FirebaseMessaging = autoclass('com.google.firebase.messaging.FirebaseMessaging')
    NotificationManager = autoclass('android.app.NotificationManager')
    NotificationChannel = autoclass('android.app.NotificationChannel')
    NotificationBuilder = autoclass('android.app.Notification$Builder')
    PendingIntent = autoclass('android.app.PendingIntent')
    Intent = autoclass('android.content.Intent')
    Context = autoclass('android.content.Context')
    Uri = autoclass('android.net.Uri')
    RingtoneManager = autoclass('android.media.RingtoneManager')

    import firebase_config as fb
    import session

    def crear_canal_notificaciones():
        """Crea canal de notificación para Android 8+"""
        activity = PythonActivity.mActivity
        notification_manager = activity.getSystemService(Context.NOTIFICATION_SERVICE)

        # Canal para notificaciones de chat
        canal_chat = NotificationChannel(
            "chat_channel",
            "Mensajes de Chat",
            NotificationManager.IMPORTANCE_HIGH
        )
        canal_chat.setDescription("Notificaciones de nuevos mensajes en consultas")
        canal_chat.enableVibration(True)
        canal_chat.setVibrationPattern([0, 500, 200, 500])

        # Canal para notificaciones de consultas
        canal_consulta = NotificationChannel(
            "consulta_channel",
            "Nuevas Consultas",
            NotificationManager.IMPORTANCE_HIGH
        )
        canal_consulta.setDescription("Notificaciones de nuevas consultas asignadas")
        canal_consulta.enableVibration(True)

        notification_manager.createNotificationChannel(canal_chat)
        notification_manager.createNotificationChannel(canal_consulta)
        print("✅ Canales de notificación creados")

    def obtener_fcm_token(callback=None):
        """Obtiene el token FCM del dispositivo"""
        def _get_token():
            try:
                firebase_messaging = FirebaseMessaging.getInstance()
                task = firebase_messaging.getToken()

                # Esperar resultado (sincrónico para simplificar)
                token = task.getResult()

                print(f"📱 FCM Token obtenido: {token[:20]}...")

                # Guardar en Firestore
                if session.current_user and token:
                    uid = session.current_user.get('uid')
                    if uid:
                        fb.actualizar_usuario(uid, {'fcm_token': token})
                        print(f"✅ FCM token guardado en Firestore")

                if callback:
                    callback(token)

                return token

            except Exception as e:
                print(f"❌ Error obteniendo FCM token: {e}")
                return None

        return _get_token()

    def mostrar_notificacion_local(titulo, mensaje, canal_id="chat_channel"):
        """Muestra notificación local cuando la app está en foreground"""
        try:
            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()

            # Intent para abrir la app al tocar la notificación
            intent = Intent(context, PythonActivity)
            intent.setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP)

            pending_intent = PendingIntent.getActivity(
                context, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
            )

            # Sonido por defecto
            sonido = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION)

            # Construir notificación
            builder = NotificationBuilder(context, canal_id)
            builder.setContentTitle(titulo)
            builder.setContentText(mensaje)
            builder.setSmallIcon(context.getApplicationInfo().icon)
            builder.setAutoCancel(True)
            builder.setSound(sonido)
            builder.setVibrate([0, 500, 200, 500])
            builder.setContentIntent(pending_intent)

            notification_manager = activity.getSystemService(Context.NOTIFICATION_SERVICE)
            notification_manager.notify(hash(titulo + mensaje), builder.build())

            print(f"🔔 Notificación local mostrada: {titulo}")

        except Exception as e:
            print(f"❌ Error mostrando notificación: {e}")

else:
    # En desktop, funciones vacías
    def crear_canal_notificaciones():
        pass

    def obtener_fcm_token(callback=None):
        print("ℹ️ FCM solo disponible en Android")
        return None

    def mostrar_notificacion_local(titulo, mensaje, canal_id="chat_channel"):
        print(f"🔔 [DESKTOP] Notificación: {titulo} - {mensaje}")