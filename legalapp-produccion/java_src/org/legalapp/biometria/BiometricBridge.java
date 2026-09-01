package org.legalapp.biometria;

// Puente entre Python (pyjnius) y la huella digital + cifrado de Android.
//
// Dos razones para que esto sea Java y no Python:
//
// 1. pyjnius solo puede implementar INTERFACES de Java desde Python
//    (PythonJavaClass), no puede extender clases abstractas -- y
//    BiometricPrompt.AuthenticationCallback es una clase abstracta.
//
// 2. KeyGenParameterSpec.Builder.setBlockModes(String...)/
//    setEncryptionPaddings(String...) son metodos varargs -- confirmado en
//    dispositivo real que pyjnius arma mal el array al llamarlos desde
//    Python ("ArrayStoreException: java.lang.String[] cannot be stored in
//    an array of type java.lang.String[]", un bug conocido de pyjnius con
//    varargs). Haciendo todo el manejo de la clave/cifrado en Java se evita
//    el problema de raiz -- Python nunca tiene que armar ese array.
//
// No agrega ninguna dependencia nueva de Gradle -- todo esto es API
// incluida en el SDK de Android (BiometricPrompt desde la API 28,
// AndroidKeyStore desde mucho antes).

import android.app.Activity;
import android.content.DialogInterface;
import android.hardware.biometrics.BiometricPrompt;
import android.os.CancellationSignal;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.security.KeyStore;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.IvParameterSpec;

public class BiometricBridge {

    private static final String ALIAS = "legalapp_credenciales_key";
    private static final String TRANSFORMATION = "AES/CBC/PKCS7Padding";

    public interface Callback {
        void onSuccess(String password);
        void onError(String mensaje);
        void onCancel();
    }

    private static SecretKey obtenerOCrearClave() throws Exception {
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);

        if (!ks.containsAlias(ALIAS)) {
            KeyGenParameterSpec spec = new KeyGenParameterSpec.Builder(
                    ALIAS,
                    KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                    .setBlockModes(KeyProperties.BLOCK_MODE_CBC)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_PKCS7)
                    .build();

            KeyGenerator kg = KeyGenerator.getInstance(
                    KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
            kg.init(spec);
            kg.generateKey();
        }

        return (SecretKey) ks.getKey(ALIAS, null);
    }

    /** "iv_base64:datos_base64", o null si algo falla. */
    public static String cifrar(String texto) {
        try {
            SecretKey clave = obtenerOCrearClave();
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, clave);
            byte[] iv = cipher.getIV();
            byte[] datos = cipher.doFinal(texto.getBytes("UTF-8"));
            String ivB64 = Base64.encodeToString(iv, Base64.NO_WRAP);
            String datosB64 = Base64.encodeToString(datos, Base64.NO_WRAP);
            return ivB64 + ":" + datosB64;
        } catch (Exception e) {
            return null;
        }
    }

    /** Muestra el prompt de huella; si el usuario se autentica, descifra y
     * llama callback.onSuccess(password). Si cancela/falla/hay error,
     * llama a onCancel()/onError() -- nunca deja al caller esperando. */
    public static void autenticarYDescifrar(
            Activity activity, String textoCifrado, final Callback callback) {
        try {
            String[] partes = textoCifrado.split(":", 2);
            byte[] iv = Base64.decode(partes[0], Base64.NO_WRAP);
            final byte[] datos = Base64.decode(partes[1], Base64.NO_WRAP);

            SecretKey clave = obtenerOCrearClave();
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, clave, new IvParameterSpec(iv));

            BiometricPrompt.Builder builder = new BiometricPrompt.Builder(activity);
            builder.setTitle("Ingresar con huella");
            builder.setSubtitle("Confirma tu identidad para completar el login");
            builder.setNegativeButton(
                "Usar contrasena",
                activity.getMainExecutor(),
                new DialogInterface.OnClickListener() {
                    @Override
                    public void onClick(DialogInterface dialog, int which) {
                        callback.onCancel();
                    }
                }
            );
            BiometricPrompt prompt = builder.build();

            BiometricPrompt.AuthenticationCallback authCallback =
                    new BiometricPrompt.AuthenticationCallback() {
                @Override
                public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult result) {
                    try {
                        // El cipher que vuelve autenticado en el resultado
                        // es el mismo que se paso al CryptoObject -- usarlo
                        // a el (no uno nuevo) es lo que prueba que la
                        // operacion realmente paso por la huella.
                        Cipher cipherAutenticado = result.getCryptoObject().getCipher();
                        byte[] plano = cipherAutenticado.doFinal(datos);
                        callback.onSuccess(new String(plano, "UTF-8"));
                    } catch (Exception e) {
                        callback.onError("Error descifrando: " + e.getMessage());
                    }
                }

                @Override
                public void onAuthenticationError(int errorCode, CharSequence errString) {
                    // errorCode 10 = ERROR_USER_CANCELED, 13 = ERROR_NEGATIVE_BUTTON.
                    // Los dos son "el usuario eligio no usar la huella", no
                    // una falla real -- se tratan igual que cancelar.
                    if (errorCode == 10 || errorCode == 13) {
                        callback.onCancel();
                    } else {
                        callback.onError(errString != null ? errString.toString() : "Error de autenticacion");
                    }
                }

                @Override
                public void onAuthenticationFailed() {
                    // Huella no reconocida en un intento puntual -- el
                    // prompt sigue abierto solo para reintentar.
                }
            };

            CancellationSignal cancelSignal = new CancellationSignal();
            BiometricPrompt.CryptoObject cryptoObject = new BiometricPrompt.CryptoObject(cipher);
            prompt.authenticate(cryptoObject, cancelSignal, activity.getMainExecutor(), authCallback);
        } catch (Exception e) {
            callback.onError("Error preparando huella: " + e.getMessage());
        }
    }
}
