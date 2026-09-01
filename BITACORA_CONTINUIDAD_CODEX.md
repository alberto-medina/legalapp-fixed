# Legal App - Bitacora de continuidad

Ultima actualizacion: 2026-08-22

Esta nota queda como reemplazo practico de las memorias de Claude para poder seguir el trabajo desde Codex sin perder contexto.

## Regla importante de trabajo

- Antes de cambiar codigo, primero diagnosticar y avisar.
- Si Beto dice "mirar", "verificar" o "vemos", no tocar codigo hasta que lo confirme.
- La app tiene codigo duplicado en varias copias. Si se corrige algo real de app, hay que sincronizarlo en las 4 copias:
  - `C:\legalapp-fixed`
  - `C:\legalapp-fixed\legalapp-produccion`
  - `C:\legalapp-fixed\legalapp-produccion\publicacion_googleplay\AAB_SEPARADO\fuente_googleplay`
  - `C:\legalapp-fixed\legalapp-escritorio`

## Version 125 / 1.1.13 - Google Play

Esto estaba guardado en la memoria de Claude `project-legalapp-16kb-page-size`, no como release 125.

Estado confirmado:

- Se subio a Play Console como `versionCode 125 / version 1.1.13`.
- El problema grave era el aviso de Google Play sobre soporte de paginas de memoria de 16 KB.
- La causa real fue que WSL tenia cacheado el build nativo viejo (`build-arm64-v8a_armeabi-v7a`) con `.so` anteriores al cambio de NDK.
- Se borro esa carpeta de build cacheada.
- Se recompilo desde cero con `android.ndk = 28c`.
- Se verifico con `readelf -lW` que las librerias nativas quedaron alineadas a `0x4000` / 16 KB.
- Se verifico tanto en carpeta intermedia como extrayendo directo del AAB final.
- Play Console confirmo que el paquete 125 ahora dice `Admite 16 KB`.
- Quedo cerrado con doble confirmacion: local + Google Play.

Pendiente relacionado:

- Google tambien marcaba `androidx.activity:activity` desactualizado.
- Se intento subir a `androidx.activity:activity:1.9.3`, pero rompio el build por conflicto de Kotlin (`Duplicate class kotlin.collections.jdk8...`).
- Ese cambio fue revertido.
- Queda pendiente para una sesion futura buscar una version compatible o resolver dependencias de Gradle.
- No es el aviso grave; el grave de 16 KB ya quedo resuelto.

## Version 124 / 1.1.12 - Changelog guardado

Memoria encontrada: `project-legalapp-release-124-changelog`.

Cambios principales frente a 123:

- Se saco el backdoor admin hardcodeado `LegalAdmin2024`.
- Admin ahora depende de una cuenta real con `rol='admin'` en Supabase.
- Aprobar abogados, bloquear/reactivar, retiros y precios pasan por Edge Function `admin-actions`.
- Se corrigio teclado tapando login, que antes no habia llegado a Play por falta de sincronizacion entre copias.
- Se corrigio `Mi Perfil` cuando a veces no respondia al primer toque.
- Busqueda de abogados por provincia/ciudad ahora funciona sin importar mayusculas/minusculas.
- Avatar por defecto corregido.
- Mejoras visuales: sombras, skeleton de carga, avatar en chat, separador `Hoy`/`Ayer`.
- Cambios Play: NDK 28c, orientacion corregida via manifest, fragment 1.2.1.

## Pendientes visuales anotados

Memoria encontrada: `project-legalapp-ui-polish-pending`.

Implementados:

- Skeleton de carga en lista de abogados.
- Sombras parejas en cards.
- Avatar chico junto a mensajes del otro en chat.
- Separador de fecha `Hoy` / `Ayer` en chat.

Pendiente:

- Campanita de notificaciones con numerito en vez del boton de texto `Avisos`.
- Requiere cambio de esquema en Supabase para contar no leidos / ultimo visto, por eso no se hizo todavia.

## Pruebas en celular real

Memoria encontrada: `project-legalapp-realdevice-findings`.

Confirmado:

- Login con teclado funcionando en celular real.
- Separador `Hoy` / `Ayer` funcionando en chat.
- Popup de recuperar contrasena funcionando.

Notas tecnicas:

- `Window.keyboard_height` de Kivy no era confiable en Android.
- Se uso detector nativo con `pyjnius` y debounce.
- No tocar login por el tema teclado salvo que haya bug nuevo real.

## Notificaciones push - revision 2026-08-22

Se reviso porque no llegaban notificaciones a celulares.

Hallazgos:

- Los tokens FCM se guardaban en Supabase.
- La Edge Function `notificaciones-push` estaba activa.
- El problema probable fue la clave privada de Firebase rotada.
- La key vieja daba `invalid_grant: Invalid JWT Signature`.
- Beto descargo un nuevo JSON de Firebase Admin SDK.
- Se actualizo `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL` y `FIREBASE_PRIVATE_KEY` en Supabase secrets.
- Luego una notificacion directa FCM respondio OK.
- Beto confirmo que la notificacion llego y Legal App aparecio en notificaciones recientes de Android.

Conclusion:

- FCM quedo funcionando del lado servidor.
- Si la app esta abierta en primer plano, Android puede no mostrar notificacion del sistema porque no hay servicio nativo dedicado para foreground.

## Caso pago / nueva consulta / crash - revision 2026-08-22

Beto reporto que al pagar hubo crash o cartel `Legal App no responde`, y que no llegaba la notificacion de nueva consulta.

Supabase:

- Se verifico `javichac87@gmail.com`.
- Usuario existe como abogado.
- Tiene token FCM guardado.
- Beto despues confirmo que ya estaba chateando, asi que la consulta puntual no quedo perdida.

Diagnostico de codigo:

- `views/pago_mp.py` hacia muchas llamadas de red en el hilo principal al tocar `Verificar pago` o `Continuar`.
- Eso puede producir ANR en Android: `Legal App no responde`.
- Tambien habia un riesgo: si la app marcaba una consulta como `pagado` y crasheaba antes de mandar push, al reintentar podia saltear la notificacion porque veia el estado ya pagado.

Cambios locales hechos antes de que Beto pidiera no tocar mas:

- `verificar_pago` y `confirmar_pago` fueron movidos a thread en segundo plano.
- La UI se actualiza despues con `Clock.schedule_once`.
- Se agregaron flags para evitar doble toque: `_verificando_pago` y `_confirmando_pago`.
- Se separo `debe_notificar` de `debe_acreditar`, para no duplicar honorarios pero permitir reintento de push si el pago activo quedo a medio camino.
- Se aplico en las 4 copias de `views/pago_mp.py`.
- Se valido sintaxis con `python -m py_compile`.

Importante:

- Estos cambios estan en codigo local, pero no llegan a Google Play hasta compilar/subir un AAB nuevo.

## Chat / teclado - revision 2026-08-22

Beto mostro que el chat tenia un espacio blanco enorme sobre el teclado.

Causa:

- `chat.kv` sumaba `app.keyboard_height` al alto del input y tambien al padding.
- Android ya estaba redimensionando la ventana, entonces se compensaba dos veces.

Cambio local hecho antes de que Beto pidiera no tocar mas:

- En las 4 copias de `chat.kv`:
  - `height: dp(72) + app.keyboard_height` paso a `height: dp(72)`.
  - padding inferior dejo de sumar `app.keyboard_height`.

Importante:

- Esto tambien es local; no cambia la app instalada desde Play hasta nuevo build.

## Play Console / produccion

Dato confirmado por captura de Beto:

- La app aparece bajo cuenta/empresa Cumbrelabs.
- El boton de solicitar produccion decia que solo el propietario de la cuenta puede pedir acceso.
- La cuenta fue creada por un amigo.

Conclusion:

- Para pedir produccion, debe entrar el propietario real de la cuenta Play Console, no solo un usuario agregado.

## Archivos/memorias de Claude utiles encontradas

Indice principal:

- `C:\Users\Beto_\.claude\file-history\32668bcf-106e-4bb8-8cde-460cf26a5da3\4793c98bc08ed959@v23`

Release 124:

- `C:\Users\Beto_\.claude\file-history\32668bcf-106e-4bb8-8cde-460cf26a5da3\01c8e8cabf25c589@v4`

Version 125 / 16KB:

- `C:\Users\Beto_\.claude\file-history\32668bcf-106e-4bb8-8cde-460cf26a5da3\7d017b2ccfae87fe@v13`

Visuales pendientes:

- `C:\Users\Beto_\.claude\file-history\32668bcf-106e-4bb8-8cde-460cf26a5da3\9fb325b99ec04b38@v8`

Pruebas reales:

- `C:\Users\Beto_\.claude\file-history\32668bcf-106e-4bb8-8cde-460cf26a5da3\ea0152e9005aa272@v3`

Build/API:

- `C:\Users\Beto_\.claude\file-history\32668bcf-106e-4bb8-8cde-460cf26a5da3\528fddfb44ec5c75@v5`


## Pendiente de publicar en proximo AAB

Estos fixes ya fueron aplicados localmente el 2026-08-22, pero todavia NO estan en la version instalada desde Google Play hasta compilar y subir un AAB nuevo.

### Fix pago / crash despues de pagar

Archivos modificados:

- `views/pago_mp.py`
- `legalapp-produccion/views/pago_mp.py`
- `legalapp-produccion/publicacion_googleplay/AAB_SEPARADO/fuente_googleplay/views/pago_mp.py`
- `legalapp-escritorio/views/pago_mp.py`

Que se cambio:

- `verificar_pago()` dejo de hacer llamadas de red en el hilo principal.
- `confirmar_pago()` dejo de hacer llamadas de red en el hilo principal.
- Ambas operaciones ahora corren en `threading.Thread(..., daemon=True)`.
- La interfaz se actualiza luego en el hilo de Kivy con `Clock.schedule_once(...)`.
- Se agregaron flags anti doble toque:
  - `_verificando_pago`
  - `_confirmando_pago`
- Se separo la logica de notificacion y acreditacion:
  - `debe_acreditar`: evita acreditar honorarios dos veces.
  - `debe_notificar`: permite reintentar la push de nueva consulta si el pago activo habia quedado a medio camino.

Objetivo:

- Evitar ANR / cartel `Legal App no responde` despues de pagar.
- Evitar que una consulta pagada quede sin notificacion al abogado si la app se cayo despues de marcar el pago.

Verificacion local:

- `python -m py_compile` paso OK en las 4 copias de `pago_mp.py`.

Riesgo / pendiente:

- Falta probarlo en celular real antes de subirlo a Play.
- Falta compilar AAB nuevo y subirlo a Play Console para que llegue a usuarios/testers.

### Fix chat / espacio blanco sobre teclado

Archivos modificados:

- `views/chat.kv`
- `legalapp-produccion/views/chat.kv`
- `legalapp-produccion/publicacion_googleplay/AAB_SEPARADO/fuente_googleplay/views/chat.kv`
- `legalapp-escritorio/views/chat.kv`

Que se cambio:

- El input del chat dejo de sumar `app.keyboard_height` al alto.
- El padding inferior del input dejo de sumar `app.keyboard_height`.
- Antes se compensaba dos veces porque Android ya redimensionaba la ventana.

Cambio concreto:

- `height: dp(72) + app.keyboard_height` paso a `height: dp(72)`.
- `padding: [dp(10), dp(8), dp(10), dp(8) + app.keyboard_height]` paso a `padding: [dp(10), dp(8), dp(10), dp(8)]`.

Objetivo:

- Sacar el espacio blanco grande entre la barra de escribir mensaje y el teclado.

Verificacion de alcance y sincronizacion 2026-08-22:

- El fix esta en la barra comun `input_area` de `ChatScreen`, no en una variante separada.
- Por eso aplica a consultas tipo `chat`, `urgente` y `video/videollamada`.
- `chat.py` maneja `tipo_servicio` y estados `en_curso` / `videollamada` en la misma pantalla.
- Se verifico que las 4 copias vivas de `chat.kv` tienen el mismo SHA256.
- Se verifico que las 4 copias vivas de `chat.py` tienen el mismo SHA256.
- No existe fuente separada en `publicacion_uptodown`; Uptodown usa una de las copias fuente, no una carpeta propia con `views/chat.kv`.

Riesgo / pendiente:

- Falta probarlo en celular real con teclado abierto en consulta normal, urgente y video/videollamada.
- Falta compilar AAB nuevo y subirlo a Play Console para que llegue a usuarios/testers.

## Revision de Claude sobre los fixes de Codex - 2026-08-25

Beto pidio revisar los 3 fixes locales de Codex (chat, pago, avatar) antes de compilar. Se
encontraron 2 problemas reales, ya corregidos:

### Avatar (utils_avatar.py): sin problemas
Bien implementado. Fallback a assets/avatar_default.png en on_error, con guard para no
duplicar el bind. Compila OK, listo para probar.

### Pago (pago_mp.py): flujo de especialidad extra se habia quedado afuera
El fix de threading cubria el pago de consulta normal, pero `_confirmar_especialidad_extra()`
(comprar especialidad adicional) seguia llamando a `fb.obtener_usuario`/`fb.actualizar_usuario`
directo en el hilo principal -- ese camino especifico podia seguir generando "Legal App no
responde". Se dividio en `_confirmar_especialidad_extra_background()` (hilo aparte, red) +
`_aplicar_resultado_especialidad_extra()` (hilo principal, UI), mismo patron que el resto del
archivo. Aplicado en las 4 copias, compila OK.

### Chat (chat.kv + chat.py): el diagnostico estaba bien, la solucion incompleta
Era cierto que `app.keyboard_height` se sumaba dos veces (altura Y padding de input_area),
pero sacarlo del todo dejaba el campo de escribir sin NINGUNA compensacion contra el teclado,
porque `ChatScreen` nunca activaba `Window.softinput_mode = "resize"` (a diferencia de
login/perfil, que si lo hacen via `FormKeyboardMixin`). Sin resize real de Android y sin la
compensacion manual, probablemente eso explicaba el "salto" que reporto Beto despues del fix.

Se agrego a `chat.py` (`on_enter`/`on_leave`) el mismo cambio de `Window.softinput_mode` a
`"resize"` mientras el chat esta activo (revertido a `"below_target"` al salir, para no
pisarle el modo a otras pantallas) -- el kv de Codex (sin `app.keyboard_height`) queda
correcto una vez que Android hace el resize real, sin necesitar ningun calculo manual.
Aplicado en las 4 copias, compila OK.

**Import nuevo**: `from kivy.core.window import Window` agregado a `chat.py`.

**Pendiente**: probar en dispositivo real los 3 fixes (avatar, pago, y el chat con el ajuste
nuevo) antes de compilar el AAB definitivo.

## Memoria: proceso muerto en segundo plano (lowmemorykiller) - investigado y arreglado 2026-08-25

Beto reporto que al volver del segundo plano la app arranca de cero (presplash -> login ->
pantalla anterior) en vez de resumir, y que "antes no pasaba en ningun telefono" -- sospecha
regresion. Confirmado con logcat en vivo:

```
lowmemorykiller: Kill 'com.legalapp.app.legalapp' (25741), oom_score_adj 900 to free 443640kB
rss, 134288kB swap; reason: low watermark is breached
Process com.legalapp.app.legalapp (pid 25741) has died
```

`adb shell dumpsys meminfo com.legalapp.app.legalapp` con la app recien abierta y navegando
un poco ya mostraba **~400MB de RSS total**, con **~97MB en Graphics (EGL+GL mtrack)**.

**Causa encontrada**: ningun avatar/foto de perfil en toda la app se redimensiona antes de
mostrarse -- todos pasan por `get_avatar_source()`/`set_avatar_image()` en
`views/utils_avatar.py`, que siempre usaba la URL/archivo original a resolucion completa,
aunque se muestre en un circulo de 72-96dp. El peor caso es `views/abogados.py` (la lista de
busqueda): cada card carga la foto completa del abogado, asi que una busqueda con 15-20
resultados carga 15-20 fotos completas de golpe.

**Fix aplicado**: `set_avatar_image()` ahora descarga (si es URL remota) o lee (si es archivo
local) la imagen en un hilo aparte, la redimensiona con Pillow a maximo 240px de lado
(`AVATAR_MAX_PX`), la guarda en una cache en disco (`assets/avatar_cache/`, nombre = hash de
la fuente) y recien ahi actualiza el widget -- nunca se carga el archivo original de
resolucion completa como textura. Se guarda un `_legalapp_avatar_logical_source` en el widget
para no reprocesar si no cambio, y para no pisar el resultado si el widget ya paso a mostrar
otra foto (ej. reciclado en una lista) mientras el hilo corria. Pillow ya estaba en
`requirements` de `buildozer.spec`, no hizo falta agregar nada ahi.

Aplicado y sincronizado en las 4 copias de `views/utils_avatar.py`, compila OK.

**Pendiente**: probar en dispositivo real que la memoria baja de verdad (repetir
`dumpsys meminfo` despues de navegar lo mismo) y que los avatares se siguen viendo bien.

## Nota para seguir desde aca

Si hay que preparar algo para Google Play, partir de:

1. Version actual relevante: `125 / 1.1.13`.
2. 16 KB ya confirmado como resuelto en Play Console.
3. Pendiente tecnico no grave: `androidx.activity` desactualizado.
4. Pendiente funcional/visual: campanita con contador.
5. Cambios locales nuevos no publicados: fixes de pago ANR/notificacion y chat con teclado.



## Segundo plano / vuelve a presplash / posible crash - investigacion 2026-08-22

Beto reporto que al poner la app en segundo plano y volver, aparece otra vez la pantalla de presplash, cosa que antes no hacia.

Hallazgos sin tocar codigo:

- `main.py` mantiene `Window.clearcolor` con el mismo azul del presplash (`#0052CA`). Esto se habia hecho para evitar salto negro en arranque. Si la UI se congela o tarda en redibujar al volver, puede verse como presplash aunque no sea un arranque real.
- El flujo `on_resume` reanuda sesion en background y luego refresca algunas pantallas.
- Chat: `on_app_resume` solo reanuda listeners/polling, no parece ser el bloqueo principal.
- Dashboard, abogados y videollamada ya usan threads para consultar Supabase.
- `pago_suscripcion.py` todavia verifica Mercado Pago en el hilo principal en las copias revisadas; si la app vuelve desde esa pantalla, puede producir ANR / `Legal App no responde`.
- Las 4 copias de `pago_suscripcion.py` no estan sincronizadas por hash. Produccion y fuente_googleplay coinciden entre si, pero raiz y escritorio difieren.
- `buildozer.spec` actual tiene `orientation = portrait` y `android.manifest.orientation = unspecified`.
- Logcat viejo (`logcat_prueba.txt`, 2026-08-18) muestra muchos `ANR Warning` de `PythonActivity` y luego `Force removing ActivityRecord ... app died, no saved state`, con `Process ... exited due to signal 9 (Killed)` y eventos de `lowmemorykiller`. Eso indica al menos un caso real donde Android mato el proceso estando la app pausada.

Conclusion provisoria:

- Si Android mata el proceso en segundo plano, al volver es normal que aparezca presplash porque la app arranca de cero.
- Si no muere el proceso, el azul de `Window.clearcolor` puede hacer que cualquier congelamiento al reanudar parezca presplash.
- Para confirmar la causa actual hace falta capturar un logcat nuevo justo cuando Beto manda la app a segundo plano y vuelve.

Pendiente:

- Capturar logcat nuevo con `C:\adb\tools\platform-tools\adb.exe` mientras se reproduce el problema.
- Si se confirma ANR desde `pago_suscripcion`, mover `verificar_pago()` y `_activar_suscripcion()` a thread como se hizo con `pago_mp.py`, y sincronizar las 4 copias.
- Si se confirma muerte por memoria/proceso sin excepcion, revisar consumo al abrir camara/galeria/video y reducir trabajo en resume.
- Evaluar si conviene cambiar `Window.clearcolor` despues del primer render para que los freezes no parezcan presplash, sin deshacer la mejora de arranque.

## Mejoras Google Play pendientes - anotado 2026-08-22

Beto mostro en Play Console que la version `125 (1.1.13)` todavia aparece con avisos en `Para tu proxima version`.

Importante:

- Esto NO es el aviso grave de 16 KB. El soporte 16 KB ya habia quedado corregido y confirmado para version 125.
- Son avisos/mejoras pendientes para un proximo AAB.

Avisos pendientes vistos en Google Play:

1. `Tu app usa una version desactualizada del SDK androidx.activity:activity`
   - Google recomienda actualizar `androidx.activity:activity` desde `1.1.0` a version mas reciente.
   - Ya se habia intentado subir a `androidx.activity:activity:1.9.3`, pero rompio build por conflicto de Kotlin / clases duplicadas.
   - Queda como mejora pendiente: buscar version compatible o resolver dependencias Gradle/Kotlin sin romper Buildozer.

2. `Quita las restricciones de cambio de tamano y orientacion en tu app para que sea compatible con dispositivos con pantalla grande`
   - Play Console detecta restriccion en `org.kivy.android.PythonActivity$UnpackFilesTask.onPostExecute`.
   - Revision local: los `buildozer.spec` todavia tienen:
     - `orientation = portrait`
     - `android.manifest.orientation = unspecified`
   - Aunque se puso `android.manifest.orientation = unspecified`, Buildozer/Kivy sigue teniendo `orientation = portrait`, por eso Google puede seguir detectando restriccion.
   - Queda como mejora pendiente: probar sacar la restriccion real de orientacion/redimensionado en las 4 copias y verificar UI en celular/tablet antes de subir.

Estado:

- Pendiente para proximo build/AAB.
- No tocar apurado sin testear porque puede afectar layout en pantallas grandes, tablets o rotacion.

### Fix avatar dashboard/perfil - 2026-08-22

Beto reporto que en dashboard la imagen de perfil aparece con una `X`.

Diagnostico:

- `assets/avatar_default.png` existe y es un PNG valido en las 4 copias.
- El problema probable no era el asset default, sino que `AsyncImage` quedaba mostrando la X interna de Kivy si fallaba la carga de la foto remota (`foto_url`).
- `utils_avatar.py` estaba desincronizado: la copia de `fuente_googleplay` tenia cache-buster para URLs remotas y las otras tres no.

Cambio local aplicado en las 4 copias de `views/utils_avatar.py`:

- Se agrego cache-buster uniforme para URLs remotas de avatar, para evitar foto vieja cacheada.
- Se agrego binding al evento `on_error` de `AsyncImage`.
- Si falla la foto remota, el avatar vuelve automaticamente a `assets/avatar_default.png` en vez de quedar con X.
- Se sincronizaron las 4 copias y quedaron con el mismo hash.

Verificacion local:

- `python -m py_compile` paso OK en las 4 copias de `utils_avatar.py`.
- Hash igual en las 4 copias: `BA0BF71F809BEFEEC1D095ECCDC93942C250E8EFBB4336591C3F29C25B337874`.

Pendiente:

- Probar en celular real luego de instalar nuevo build.
- Este cambio no llega a Google Play hasta compilar/subir un AAB nuevo.

## Plan APK de prueba fuera de Google - anotado 2026-08-22

Beto quiere armar luego un APK de prueba directo, fuera de Google Play, para instalar en el celular y validar todos los fixes locales antes de subir un AAB nuevo.

Aclaracion sobre avatar / Firebase JSON:

- El cambio del JSON de Firebase Admin SDK no deberia afectar imagenes de perfil.
- Ese JSON afecta notificaciones push / FCM desde Supabase Edge Function.
- Las imagenes de perfil dependen de `foto_url` en Supabase, Supabase Storage y `AsyncImage` de Kivy.
- La X del avatar probablemente venia de fallo de carga remota/cache/red sin fallback visual.
- Ya quedo fix local en `utils_avatar.py` para volver a `assets/avatar_default.png` si falla la imagen remota.

Objetivo del proximo APK de prueba:

- Instalar directo en celular antes de Google Play.
- Probar panel abogado: avatar sin X.
- Probar dashboard cliente: avatar sin X.
- Probar chat normal, urgente y video con teclado abierto.
- Probar pago / nueva consulta sin `Legal App no responde`.
- Probar notificacion push de nueva consulta.
- Probar segundo plano / volver a app para observar presplash-login-restauracion.

Pendiente antes de compilar:

- Confirmar desde que carpeta conviene generar APK de prueba.
- Verificar version interna para no confundir con la instalada desde Play.
- Si se compila APK local, recordar que no es para subir a Play; para Play se usa AAB.

## Prueba APK 126 en celular real - logcat 2026-08-25

Contexto:

- APK probado: `legalapp-126-prueba-instalable.apk` / `versionCode 126` / `versionName 1.1.14`.
- Celular conectado por ADB: moto g06 (`ZY32MDQSF2`).
- Se dejo logcat corriendo mientras Beto probaba login, dashboard, historial/chat, teclado y segundo plano.

Hallazgos del log:

- Proceso de Legal App se mantuvo vivo durante las pruebas observadas: PID `24780`.
- No aparecio `FATAL EXCEPTION` ni crash Java/Python de Legal App en el tramo monitoreado.
- Al enviar la app a segundo plano y volver, se vio `APP PAUSED` -> `APP RESUMED` con `Sesion cargada`, sin reinicio frio en ese tramo.
- El monitor del sistema mostro muchas muertes por `lowmemorykiller`, pero fueron de otras apps (`Photos`, `Play Store`, `Files`, `Facebook`, etc.), no de Legal App durante esta captura.
- El telefono estuvo en presion de memoria constante. Esto puede explicar por que en otras pruebas Android mata Legal App al quedar en segundo plano y luego vuelve con presplash/login/restauracion.

Memoria observada:

- Medicion inicial luego de abrir/probar: RSS aprox. 272 MB, luego 295 MB y 319 MB.
- Durante navegacion chat/dashboard/segundo plano subio mucho:
  - `TOTAL RSS` aprox. 523 MB en una medicion.
  - `Graphics / GL mtrack` aprox. 221 MB.
  - Luego `TOTAL RSS` bajo a aprox. 345 MB, pero `Graphics` siguio alto, aprox. 209 MB, con mucho swap.

Sospecha principal:

- El avatar remoto del usuario se descarga repetidamente al volver al dashboard/resume.
- URL vista en log: avatar de Supabase de aprox. 3.8 MB (`GET ...avatars/Hke6jEywjwaoJWMadgLp0iosvtj2_1787625673.jpg?v=...`).
- `utils_avatar.py` ya redimensiona a cache, pero `_cargar_remoto_redimensionado()` hace `requests.get()` siempre aunque el cache redimensionado ya exista.
- Como `get_avatar_source()` agrega `?v=` cada 30 segundos, el widget considera fuente logica nueva y vuelve a disparar carga/descarga al navegar o reanudar.

Mejora puntual recomendada para proximo APK:

1. En `views/utils_avatar.py`, si el cache redimensionado remoto ya existe, aplicar ese archivo local inmediatamente sin volver a bajar la foto grande.
2. Usar una clave logica estable para avatar remoto (base URL sin `?v=`) o evitar que el `?v=` cambiante fuerce recargas innecesarias.
3. Descargar/redimensionar solo cuando no existe cache, cuando cambia realmente la foto, o cuando se fuerce desde perfil despues de actualizar imagen.
4. Mantener fallback a `assets/avatar_default.png` si falla carga.
5. Sincronizar el mismo cambio en las 4 carpetas antes de armar APK/AAB.

Otros puntos observados para optimizar, no tocar apurado:

- Dashboard/resume dispara varias consultas a Supabase cada pocos segundos (`consultas`, `usuarios`, `pagos_procesados`, `resenas`). Funciona, pero puede optimizarse luego para bajar red y trabajo al volver de segundo plano.
- El APK parece incluir carpetas de publicacion/capturas en assets; revisar `source.exclude_patterns` para no empaquetar material que no usa la app.
- Seguir probando chat normal/urgente/video, notificacion, pago/nueva consulta y segundo plano prolongado.

Estado:

- APK 126 se ve mas estable que el caso anterior de muerte inmediata: no hubo crash fatal observado.
- Queda como prioridad tecnica reducir memoria grafica/avatares antes de considerar que el problema de presplash por kill esta completamente cerrado.

### Actualizacion de la misma prueba: kill confirmado por memoria

A las `14:08:55` el monitor del sistema confirmo muerte real de Legal App:

- `lowmemorykiller` mato `com.legalapp.app.legalapp` PID `24780`.
- Motivo: `device is not responding`.
- Memoria liberada informada por Android: aprox. `314804 kB RSS` y `252404 kB swap`.
- Luego `ActivityManager` registro: `Process com.legalapp.app.legalapp (pid 24780) has died: cch LAST`.
- Despues del kill, `pidof com.legalapp.app.legalapp` no devolvio proceso activo.

Conclusion confirmada:

- El presplash/login al volver no es un simple bug visual en este caso: Android efectivamente mata el proceso por presion de memoria.
- El foco del proximo fix debe ser bajar memoria grafica/texturas y evitar recargas grandes al navegar/resumir.
- Prioridad 1: avatar remoto/cache para no bajar/reprocesar foto de 3.8 MB varias veces.
- Prioridad 2: revisar pantallas que recrean widgets/texturas al volver de chat/dashboard y liberar recursos o evitar recargas.
- Prioridad 3: optimizar polling/requests en dashboard/resume despues de estabilizar memoria.

Plan siguiente recomendado:

1. Aplicar fix minimo en `utils_avatar.py`: usar cache local existente inmediatamente y no hacer `requests.get()` si ya hay cache redimensionado.
2. Quitar o estabilizar el `?v=` para que no fuerce fuente nueva cada 30 segundos; dejar refresh solo cuando el usuario cambie foto.
3. Sincronizar el cambio en las 4 carpetas.
4. Compilar APK 127 de prueba local.
5. Repetir prueba ADB: dashboard -> chat -> volver -> segundo plano 30s -> volver, midiendo `Graphics / GL mtrack` y verificando que no haya kill.
