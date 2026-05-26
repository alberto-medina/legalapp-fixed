"""
fcm_service.py
FCM Android estable para Kivy
"""

from kivy.utils import platform

if platform == 'android':

    try:
        from jnius import autoclass
        from android.runnable import run_on_ui_thread

        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        FirebaseMessaging = autoclass('com.google.firebase.messaging.FirebaseMessaging')

        NotificationManager = autoclass('android.app.NotificationManager')
        NotificationChannel = autoclass('android.app.NotificationChannel')
        NotificationBuilder = autoclass('android.app.Notification$Builder')

        PendingIntent = autoclass('android.app.PendingIntent')
        Intent = autoclass('android.content.Intent')
        Context = autoclass('android.content.Context')

        RingtoneManager = autoclass('android.media.RingtoneManager')

        import supabase_config as fb
        import session

        FCM_OK = True

    except Exception as e:
        print(f"❌ Error cargando FCM: {e}")
        FCM_OK = False

    @run_on_ui_thread
    def crear_canal_notificaciones():
        if not FCM_OK:
            return

        try:
            activity = PythonActivity.mActivity

            notification_manager = activity.getSystemService(
                Context.NOTIFICATION_SERVICE
            )

            canal_chat = NotificationChannel(
                "chat_channel",
                "Mensajes",
                NotificationManager.IMPORTANCE_HIGH
            )

            canal_chat.enableVibration(True)

            canal_consulta = NotificationChannel(
                "consulta_channel",
                "Consultas",
                NotificationManager.IMPORTANCE_HIGH
            )

            canal_consulta.enableVibration(True)

            notification_manager.createNotificationChannel(canal_chat)
            notification_manager.createNotificationChannel(canal_consulta)

            print("✅ Canales FCM creados")

        except Exception as e:
            print(f"❌ Error canales: {e}")

    def obtener_fcm_token(callback=None):

        if not FCM_OK:
            return None

        try:
            firebase_messaging = FirebaseMessaging.getInstance()

            task = firebase_messaging.getToken()

            token = task.getResult()

            if token:

                print(f"✅ Token FCM: {token[:25]}...")

                if session.current_user:

                    uid = session.current_user.get('uid')

                    if uid:
                        fb.actualizar_usuario(uid, {
                            'fcm_token': token
                        })

                        print("✅ Token guardado en Supabase")

                if callback:
                    callback(token)

                return token

        except Exception as e:
            print(f"❌ Error token FCM: {e}")

        return None

    @run_on_ui_thread
    def mostrar_notificacion_local(
            titulo,
            mensaje,
            canal_id="chat_channel"
    ):

        if not FCM_OK:
            return

        try:
            activity = PythonActivity.mActivity

            context = activity.getApplicationContext()

            intent = Intent(
                context,
                PythonActivity
            )

            intent.setFlags(
                Intent.FLAG_ACTIVITY_CLEAR_TOP |
                Intent.FLAG_ACTIVITY_SINGLE_TOP
            )

            pending_intent = PendingIntent.getActivity(
                context,
                0,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT |
                PendingIntent.FLAG_IMMUTABLE
            )

            sonido = RingtoneManager.getDefaultUri(
                RingtoneManager.TYPE_NOTIFICATION
            )

            builder = NotificationBuilder(
                context,
                canal_id
            )

            builder.setContentTitle(titulo)
            builder.setContentText(mensaje)
            builder.setSmallIcon(
                context.getApplicationInfo().icon
            )

            builder.setAutoCancel(True)
            builder.setSound(sonido)
            builder.setContentIntent(pending_intent)

            notification_manager = activity.getSystemService(
                Context.NOTIFICATION_SERVICE
            )

            notification_manager.notify(
                hash(titulo + mensaje),
                builder.build()
            )

            print(f"🔔 Notificación: {titulo}")

        except Exception as e:
            print(f"❌ Error notificación: {e}")

else:

    def crear_canal_notificaciones():
        print("ℹ️ FCM solo Android")

    def obtener_fcm_token(callback=None):
        return None

    def mostrar_notificacion_local(
            titulo,
            mensaje,
            canal_id="chat_channel"
    ):
        print(f"[NOTIFICACION] {titulo}: {mensaje}")