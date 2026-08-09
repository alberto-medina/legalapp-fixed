# Firebase — checklist de endurecimiento (sin rotar ninguna clave)

Proyecto: `legalapp-pro` (project_number `511934443513`)
Paquete Android: `com.legalapp.app`

Ninguno de estos pasos rota ni invalida la `serviceAccountKey.json` ni el
`FIREBASE_API_KEY`. Son controles adicionales alrededor de esas claves.

## 1. Restringir el Android API Key (`AIzaSyBmBKc5MkGmWBjeEa2YPOqCKa9Ve3fxWbE`)

Hoy esa key funciona desde cualquier lugar de internet, no solo desde tu
APK. Restringirla a tu paquete + firma hace que, aunque alguien la copie del
APK o de `config.py`/`google-services.json` (que ya estan en el repo
publico), no pueda usarla desde su propia app o un script.

Sacar el SHA-1 y SHA-256 del keystore de release (el mismo que usa
`buildozer.spec` -> `android.release_keystore`):

```bash
keytool -list -v -keystore legalapp-release.keystore -alias legalapp
```

(te va a pedir la contraseña del keystore; copiá las lineas `SHA1:` y `SHA256:`)

Restringir la key (requiere `gcloud` autenticado como owner/editor del
proyecto `legalapp-pro`):

```bash
gcloud config set project legalapp-pro

gcloud services api-keys list --filter="displayName~Android"

# reemplazar KEY_ID por el que devuelva el list de arriba
gcloud services api-keys update KEY_ID \
  --api-target=service=firebase.googleapis.com \
  --api-target=service=identitytoolkit.googleapis.com \
  --api-target=service=firebaseinstallations.googleapis.com \
  --allowed-application=sha1_fingerprint=TU_SHA1,package_name=com.legalapp.app
```

Si preferis hacerlo sin gcloud: Google Cloud Console → APIs & Services →
Credentials → esa API key → "Application restrictions" → Android apps →
agregar paquete + SHA-1.

No lo hagas si todavia no probaste bien un build de release contra esa
restriccion: si el SHA-1 no coincide (por ejemplo si Google Play App
Signing usa una firma distinta a tu keystore local), la app deja de poder
loguearse. Verificá primero en Play Console → Configuración → Integridad
de la app cuál es el SHA-1 real que firma los APK que llegan a los
usuarios (puede no ser el de tu keystore local si usás Play App Signing).

## 2. Firebase App Check (Play Integrity)

Bloquea que alguien llame a tus endpoints de Firebase Auth (o a
Supabase/tus Edge Functions, si despues integras App Check ahi tambien)
desde algo que no sea tu app real, aunque tenga la API key correcta.

Firebase Console → App Check → registrar la app Android → proveedor
"Play Integrity". Sin cambios de codigo obligatorios para empezar en modo
"monitoreo" (no bloquea, solo reporta); recien despues de ver los reportes
pasarlo a "enforced".

## 3. Auth: protecciones que ya trae el proyecto y conviene revisar

Firebase Console → Authentication → Settings:

- **Email enumeration protection**: activarla si no esta (evita que alguien
  pueda usar `accounts:signUp` / `accounts:signInWithPassword` para
  averiguar que emails estan registrados, probando uno por uno).
- **Password policy**: subir el minimo de 6 a al menos 8 caracteres y
  exigir mayusculas/minusculas/numeros si la UI de registro lo permite
  (ahora mismo `firebase_auth.py` no valida fuerza de password del lado del
  cliente).
- Revisar en Authentication → Users que no haya cuentas de prueba con
  privilegios (`rol` en Supabase) que no deberian existir en produccion.

## 4. Reducir el radio de exposicion de la service account sin rotarla

Ya que se decidio no rotar `serviceAccountKey.json` por ahora: en Google
Cloud Console → IAM & Admin → IAM, buscar la cuenta de servicio (termina en
`@legalapp-pro.iam.gserviceaccount.com`) y confirmar que **no** tenga el rol
`Editor` o `Owner` del proyecto completo. Las cuentas de servicio default de
Firebase suelen venir con `Editor` de fabrica, que es mucho mas de lo que
esta app necesita (con las Cloud Messaging API alcanza, que es lo unico que
usa `notificaciones-push`). Bajarle el rol a algo como
`Firebase Cloud Messaging API Admin` reduce el dano posible si esa clave se
usa, sin invalidarla.

`security_scan.py`/`production_check.py` confirman que nada del codigo activo
carga `serviceAccountKey.json` hoy (era de un enfoque viejo con
`firebase-admin` que ya no se usa) — por eso se puede borrar del disco local
sin romper nada, si en algun momento se decide hacerlo, aunque eso no
revoca los permisos que ya tiene esa clave mientras siga viva.

## 5. google-services.json en el repo publico

`google-services.json` (raiz del repo) ya esta en `.gitignore`, pero quedo
una copia tracked de antes de que se agregara esa regla. Contiene el mismo
API key que `config.py` (no un secreto nuevo), asi que no urge por si solo,
pero conviene sacarlo del tracking para no confundir auditorias futuras:

```bash
git rm --cached google-services.json
```

(esto no borra el archivo del disco, solo deja de versionarlo; hacerlo solo
si querés, no es indispensable dado que ya está `google-services.json` en
`.gitignore` para los proximos commits).
