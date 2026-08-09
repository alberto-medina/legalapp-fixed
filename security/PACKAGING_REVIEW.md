# Revision: que claves viajan dentro del APK/AAB publicado

Pregunta original: si algo se puede filtrar al descompilar o inspeccionar
el paquete que sube a Google Play.

## Que SI viaja dentro del APK/AAB (y es esperable que viaje)

- `config.py`: `SUPABASE_URL`, `SUPABASE_KEY` (anon key de Supabase) y
  `FIREBASE_API_KEY`. Las tres son claves publicas por diseño — Google y
  Supabase asumen que van a estar en el cliente. Su seguridad depende de
  los controles del lado del servidor (RLS en Supabase, restriccion de la
  API key + App Check en Firebase), no de esconderlas. Ver
  `security/firebase_hardening.md` y `supabase/supabase/sql/`.
- `google-services.json` (dentro de `fuente_googleplay/` y en la raiz):
  mismo `FIREBASE_API_KEY`, mas `project_number`/`project_id`/`app_id`. Sin
  `oauth_client` ni secretos adicionales. Tambien esperable que sea
  publico.

## Que NO viaja (confirmado revisando `buildozer.spec`)

`source.exclude_patterns` en `buildozer.spec` (raiz y
`legalapp-produccion/publicacion_googleplay/AAB_SEPARADO/fuente_googleplay/buildozer.spec`,
que es el que arma el AAB que se sube a Play) excluye explicitamente:

```
serviceAccountKey.json, .env, .env.example, legalapp-release.keystore,
supabase/*, scripts/*, backups/*, functions/*, *.bak, *.log
```

Se confirmo con `find`/`grep` que ninguno de esos archivos existe
fisicamente dentro de `publicacion_googleplay/` — no hay `.env` real (solo
`.env.example`), no hay `serviceAccountKey.json`, no hay `.keystore`, y no
se encontraron contraseñas de keystore en texto plano en
`AAB_SEPARADO/comandos_aab_googleplay.txt` ni en `estado_aab.txt` (que si
estan siendo versionados, pero solo tienen comandos, no secretos).

`firebase_auth.py` (el que se empaqueta) solo usa el `FIREBASE_API_KEY`
publico via REST — no importa ni usa `firebase-admin` ni la service
account, asi que esa clave nunca estuvo en riesgo de terminar en el APK.

## Lo que si esta mal, pero no es del empaquetado sino del repo de Git

Esto ya se reporto aparte: `serviceAccountKey.json` (con la private key
completa de Firebase Admin) quedo comiteado en el historial de git
(commit `cb159b1`), y ese commit esta en las ramas `main` y
`legalapp-secure` ya subidas a `github.com/alberto-medina/legalapp-fixed`,
que es un **repositorio publico**. No se filtro por el empaquetado de la
app — se filtro por el historial de Git. Se decidio no rotar esa clave por
ahora; ver `security/firebase_hardening.md` seccion 4 para reducir el
riesgo sin rotarla.

## Higiene menor (no es una fuga, pero conviene saberlo)

- Existen dos copias de la carpeta `supabase/` (`supabase/` y
  `supabase/supabase/`, esta ultima con el proyecto realmente linkeado y
  las funciones/SQL mas actualizadas — ahi se agregaron los archivos de
  esta revision). Da para prolijidad, no para seguridad, pero puede
  confundir a futuro sobre cual carpeta se despliega de verdad.
- `legalapp-produccion/.gitignore` parece estar guardado en un encoding
  raro (UTF-16), lo que puede hacer que git no lo interprete bien. No es
  grave porque el `.gitignore` de la raiz ya cubre los mismos patrones para
  todo el repo (incluida esa subcarpeta), pero conviene resguardarlo en
  UTF-8 en algun momento.
