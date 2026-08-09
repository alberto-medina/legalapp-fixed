"""
fcm_service.py
FCM Android estable para Kivy
"""

import json
import os
from kivy.utils import platform

if platform == 'android':

    try:
        import time
        from jnius import autoclass
        from android.runnable import run_on_ui_thread
        from android.permissions import request_permissions, Permission

        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        FirebaseApp = autoclass('com.google.firebase.FirebaseApp')
        FirebaseOptionsBuilder = autoclass('com.google.firebase.FirebaseOptions$Builder')
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
        ULTIMO_TOKEN = None

    except Exception as e:
        print(f"❌ Error cargando FCM: {e}")
        FCM_OK = False
        ULTIMO_TOKEN = None

    def _cargar_google_services():
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "google-services.json")
            if not os.path.exists(path):
                print(f"❌ No se encontró google-services.json en {path}")
                return None
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            clients = data.get("client") or []
            package_objetivo = "com.legalapp.app.legalapp"
            client = None
            for item in clients:
                package_name = (((item.get("client_info") or {}).get("android_client_info") or {}).get("package_name")) or ""
                if package_name == package_objetivo:
                    client = item
                    break
            if client is None and clients:
                client = clients[0]
            if client is None:
                print("❌ google-services.json no contiene clientes Firebase válidos")
                return None
            return {
                "application_id": (((client.get("client_info") or {}).get("mobilesdk_app_id")) or ""),
                "api_key": ((((client.get("api_key") or [{}])[0]).get("current_key")) or ""),
                "project_id": ((data.get("project_info") or {}).get("project_id")) or "",
                "project_number": ((data.get("project_info") or {}).get("project_number")) or "",
                "storage_bucket": ((data.get("project_info") or {}).get("storage_bucket")) or "",
            }
        except Exception as e:
            print(f"❌ Error leyendo google-services.json: {e}")
            return None

    def _inicializar_firebase():
        if not FCM_OK:
            return False

        try:
            FirebaseApp.getInstance()
            print("✅ FirebaseApp ya estaba inicializado")
            return True
        except Exception:
            pass

        try:
            config = _cargar_google_services()
            if not config:
                return False

            activity = PythonActivity.mActivity
            context = activity.getApplicationContext()

            builder = FirebaseOptionsBuilder()
            builder.setApplicationId(config["application_id"])
            builder.setApiKey(config["api_key"])
            builder.setProjectId(config["project_id"])
            builder.setGcmSenderId(config["project_number"])
            if config.get("storage_bucket"):
                builder.setStorageBucket(config["storage_bucket"])

            FirebaseApp.initializeApp(context, builder.build())
            print("✅ FirebaseApp inicializado manualmente")
            return True
        except Exception as e:
            print(f"❌ Error inicializando FirebaseApp: {e}")
            return False

    def guardar_token_en_supabase():
        global ULTIMO_TOKEN
        if not FCM_OK or not ULTIMO_TOKEN or not session.current_user:
            return False
        try:
            uid = session.current_user.get('uid')
            if not uid:
                print("⚠️ No hay uid para guardar token FCM")
                return False
            ok = fb.actualizar_usuario(uid, {'fcm_token': ULTIMO_TOKEN})
            if ok:
                session.current_user['fcm_token'] = ULTIMO_TOKEN
                session.guardar()
                print("✅ Token FCM sincronizado en Supabase")
                return True
            print("❌ Supabase no confirmó guardado de token FCM")
            return False
        except Exception as e:
            print(f"❌ Error guardando token FCM en Supabase: {e}")
            return False

    @run_on_ui_thread
    def crear_canal_notificaciones():
        if not FCM_OK:
            return

        try:
            try:
                request_permissions([Permission.POST_NOTIFICATIONS])
            except Exception as e_perm:
                print(f"⚠️ No se pudo pedir permiso de notificaciones: {e_perm}")

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
        global ULTIMO_TOKEN

        if not FCM_OK:
            print("❌ FCM no disponible en Android")
            return None

        try:
            print("ℹ️ Solicitando token FCM...")
            if not _inicializar_firebase():
                print("❌ FirebaseApp no pudo inicializarse")
                return None
            firebase_messaging = FirebaseMessaging.getInstance()
            task = firebase_messaging.getToken()
            timeout = time.time() + 12

            while not task.isComplete() and time.time() < timeout:
                time.sleep(0.2)

            if not task.isComplete():
                print("❌ FCM token timeout")
                return None

            if not task.isSuccessful():
                try:
                    err = task.getException()
                except Exception:
                    err = "error desconocido"
                print(f"❌ Error token FCM task: {err}")
                return None

            token = task.getResult()

            if token:
                ULTIMO_TOKEN = token

                print(f"✅ Token FCM: {token[:25]}...")

                if session.current_user:
                    guardar_token_en_supabase()
                else:
                    print("ℹ️ Token FCM obtenido sin sesión activa; se sincronizará luego")

                if callback:
                    callback(token)

                return token
            print("❌ Firebase devolvió token vacío")

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
            try:
                builder.setSubText("Legal App")
            except Exception:
                pass

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

    def guardar_token_en_supabase():
        return False

    def mostrar_notificacion_local(
            titulo,
            mensaje,
            canal_id="chat_channel"
    ):
        print(f"[NOTIFICACION] {titulo}: {mensaje}")
