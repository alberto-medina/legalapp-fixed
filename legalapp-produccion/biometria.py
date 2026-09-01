"""Login con huella digital + cifrado de la contrasena guardada.

Usa la API de huella digital que ya viene incluida en Android (API 28+,
Android 9 en adelante) -- no agrega ninguna dependencia nueva de Gradle.

Todo el manejo de Android Keystore/Cipher/BiometricPrompt vive en
java_src/org/legalapp/biometria/BiometricBridge.java, no aca. Dos razones:
pyjnius no puede extender BiometricPrompt.AuthenticationCallback (es una
clase abstracta, pyjnius solo implementa interfaces), y ademas se confirmo
en dispositivo real que pyjnius arma mal un array String[] que hace falta
para configurar la clave (bug conocido de pyjnius con metodos varargs) --
haciendo esa parte en Java se evita el problema de raiz.

Cualquier error en cualquier punto de este modulo cae a "huella no
disponible" -- nunca debe bloquear el login normal escrito a mano.
"""
from kivy.clock import Clock
from kivy.utils import platform


def _en_android():
    return platform == "android"


def huella_disponible():
    """True si el dispositivo tiene biometria fuerte (huella, etc.)
    configurada y lista para usar ahora mismo."""
    if not _en_android():
        return False
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        bm = activity.getSystemService("biometric")
        if bm is None:
            return False
        # BIOMETRIC_STRONG = 15 (android.hardware.biometrics.BiometricManager.Authenticators)
        resultado = bm.canAuthenticate(15)
        return resultado == 0  # BIOMETRIC_SUCCESS
    except Exception as e:
        print(f"DEBUG HUELLA: huella_disponible error: {e}")
        return False


def cifrar(texto):
    """String "iv:datos" (ver BiometricBridge.cifrar), o None si algo falla
    (el caller cae a guardar en texto plano en ese caso)."""
    if not _en_android():
        return None
    try:
        from jnius import autoclass
        BiometricBridge = autoclass('org.legalapp.biometria.BiometricBridge')
        resultado = BiometricBridge.cifrar(texto)
        return str(resultado) if resultado else None
    except Exception as e:
        print(f"DEBUG HUELLA: error cifrando: {e}")
        return None


def descifrar_con_huella(texto_cifrado, on_resultado):
    """Muestra el prompt de huella; si el usuario se autentica, descifra y
    llama on_resultado(password). Si cancela, falla, o cualquier error,
    llama on_resultado(None) -- nunca deja al caller esperando."""
    try:
        from jnius import autoclass, PythonJavaClass, java_method

        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity = PythonActivity.mActivity
        BiometricBridge = autoclass('org.legalapp.biometria.BiometricBridge')

        class _Callback(PythonJavaClass):
            __javainterfaces__ = ['org/legalapp/biometria/BiometricBridge$Callback']
            __javacontext__ = 'app'

            @java_method('(Ljava/lang/String;)V')
            def onSuccess(self, password):
                Clock.schedule_once(lambda dt: on_resultado(str(password)), 0)

            @java_method('(Ljava/lang/String;)V')
            def onError(self, mensaje):
                print(f"DEBUG HUELLA: error de autenticacion: {mensaje}")
                Clock.schedule_once(lambda dt: on_resultado(None), 0)

            @java_method('()V')
            def onCancel(self):
                Clock.schedule_once(lambda dt: on_resultado(None), 0)

        # La referencia al callback se guarda en el modulo para que no la
        # recoja el garbage collector de Python antes de que Android
        # responda (el prompt de huella no es instantaneo).
        global _callback_activo
        _callback_activo = _Callback()

        BiometricBridge.autenticarYDescifrar(activity, texto_cifrado, _callback_activo)
    except Exception as e:
        print(f"DEBUG HUELLA: error mostrando prompt: {e}")
        Clock.schedule_once(lambda dt: on_resultado(None), 0)


_callback_activo = None
