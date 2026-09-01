package org.legalapp.googlesignin;

// Puente entre Python (pyjnius) y Google Sign-In (Play Services Auth).
//
// Mismo motivo que java_src/org/legalapp/biometria/BiometricBridge.java: el
// resultado de Google Sign-In viene envuelto en un Task<GoogleSignInAccount>
// y una ApiException con codigos de error tipados -- generics y excepciones
// especificas de Java son fragiles de manejar bien desde pyjnius. Se resuelve
// todo aca en Java real; Python solo llama metodos simples (crear un Intent,
// y procesar el resultado via una interfaz de callback propia con
// String/void, igual que con la huella).

import android.app.Activity;
import android.content.Intent;

import com.google.android.gms.auth.api.signin.GoogleSignIn;
import com.google.android.gms.auth.api.signin.GoogleSignInAccount;
import com.google.android.gms.auth.api.signin.GoogleSignInClient;
import com.google.android.gms.auth.api.signin.GoogleSignInOptions;
import com.google.android.gms.common.api.ApiException;
import com.google.android.gms.tasks.Task;

public class GoogleSignInBridge {

    // GoogleSignInStatusCodes.SIGN_IN_CANCELLED -- el usuario cerro el
    // selector de cuenta sin elegir ninguna.
    private static final int SIGN_IN_CANCELLED = 12501;

    public interface Callback {
        void onSuccess(String idToken, String email, String nombre);
        void onError(String mensaje);
        void onCancel();
    }

    /** Intent para lanzar con startActivityForResult -- el selector de
     * cuenta de Google. */
    public static Intent crearIntentLogin(Activity activity, String webClientId) {
        GoogleSignInOptions gso = new GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
                .requestIdToken(webClientId)
                .requestEmail()
                .build();
        GoogleSignInClient client = GoogleSignIn.getClient(activity, gso);
        return client.getSignInIntent();
    }

    /** Procesa el Intent devuelto en onActivityResult. El Task ya esta
     * resuelto en ese punto (getResult no bloquea). */
    public static void procesarResultado(Intent data, Callback callback) {
        try {
            Task<GoogleSignInAccount> task = GoogleSignIn.getSignedInAccountFromIntent(data);
            GoogleSignInAccount cuenta = task.getResult(ApiException.class);

            String idToken = cuenta.getIdToken();
            if (idToken == null) {
                callback.onError("Google no devolvio id_token");
                return;
            }

            String email = cuenta.getEmail();
            String nombre = cuenta.getDisplayName();
            callback.onSuccess(idToken, email != null ? email : "", nombre != null ? nombre : "");
        } catch (ApiException e) {
            if (e.getStatusCode() == SIGN_IN_CANCELLED) {
                callback.onCancel();
            } else {
                callback.onError("Error de Google Sign-In (codigo " + e.getStatusCode() + ")");
            }
        } catch (Exception e) {
            callback.onError("Error inesperado: " + e.getMessage());
        }
    }
}
