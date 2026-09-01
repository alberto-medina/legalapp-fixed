"""Login con Google ("Continuar con Google") para clientes.

Usa Google Sign-In (Play Services Auth, GoogleSignInClient) -- agrega la
dependencia de Gradle com.google.android.gms:play-services-auth (ver
buildozer.spec). Todo el manejo de GoogleSignInOptions/Task/ApiException vive
en java_src/org/legalapp/googlesignin/GoogleSignInBridge.java, no aca (mismo
motivo que biometria.py: generics y excepciones tipadas de Java son fragiles
desde pyjnius).

El flujo de activity result (startActivityForResult / on_activity_result)
sigue el mismo patron ya probado en este proyecto para camara/selector de
archivos (ver views/chat.py, _abrir_camara_android).

Cualquier error en cualquier punto de este modulo llama on_resultado con
Nones -- nunca debe bloquear el login normal escrito a mano.
"""
from kivy.clock import Clock
from kivy.utils import platform

from config import GOOGLE_WEB_CLIENT_ID

_REQUEST_CODE = 9001
_callback_activo = None
_on_result_activo = None


def _en_android():
    return platform == "android"


def disponible():
    return _en_android()


def iniciar_login(on_resultado):
    """on_resultado(id_token, email, nombre) si el usuario elige una cuenta
    de Google, on_resultado(None, None, None) si cancela o hay cualquier
    error."""
    if not _en_android():
        Clock.schedule_once(lambda dt: on_resultado(None, None, None), 0)
        return

    try:
        from android import activity
        from jnius import autoclass

        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        act = PythonActivity.mActivity
        GoogleSignInBridge = autoclass('org.legalapp.googlesignin.GoogleSignInBridge')

        intent = GoogleSignInBridge.crearIntentLogin(act, GOOGLE_WEB_CLIENT_ID)

        global _on_result_activo

        def _on_result(request_code, result_code, data):
            if request_code != _REQUEST_CODE:
                return
            try:
                activity.unbind(on_activity_result=_on_result_activo)
            except Exception:
                pass

            if not data:
                Clock.schedule_once(lambda dt: on_resultado(None, None, None), 0)
                return

            _procesar_resultado(GoogleSignInBridge, data, on_resultado)

        _on_result_activo = _on_result

        try:
            activity.unbind(on_activity_result=_on_result_activo)
        except Exception:
            pass
        activity.bind(on_activity_result=_on_result_activo)

        act.startActivityForResult(intent, _REQUEST_CODE)
    except Exception as e:
        print(f"DEBUG GOOGLE: error iniciando login: {e}")
        Clock.schedule_once(lambda dt: on_resultado(None, None, None), 0)


def _procesar_resultado(GoogleSignInBridge, data, on_resultado):
    try:
        from jnius import PythonJavaClass, java_method

        class _Callback(PythonJavaClass):
            __javainterfaces__ = ['org/legalapp/googlesignin/GoogleSignInBridge$Callback']
            __javacontext__ = 'app'

            @java_method('(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)V')
            def onSuccess(self, id_token, email, nombre):
                Clock.schedule_once(
                    lambda dt: on_resultado(str(id_token), str(email) if email else "", str(nombre) if nombre else ""),
                    0
                )

            @java_method('(Ljava/lang/String;)V')
            def onError(self, mensaje):
                print(f"DEBUG GOOGLE: error de autenticacion: {mensaje}")
                Clock.schedule_once(lambda dt: on_resultado(None, None, None), 0)

            @java_method('()V')
            def onCancel(self):
                Clock.schedule_once(lambda dt: on_resultado(None, None, None), 0)

        global _callback_activo
        _callback_activo = _Callback()

        GoogleSignInBridge.procesarResultado(data, _callback_activo)
    except Exception as e:
        print(f"DEBUG GOOGLE: error procesando resultado: {e}")
        Clock.schedule_once(lambda dt: on_resultado(None, None, None), 0)
