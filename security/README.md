# Plan de seguridad — Supabase + Firebase

Contexto: la app funciona con Firebase Auth para login, pero habla con
Supabase usando siempre la misma `anon key` (la que trae el APK), sin pasar
por un backend propio. Sin controles del lado del servidor, esa anon key
funciona como una llave maestra sobre toda la base. Esto es lo que dispara
los mails de Supabase sobre RLS, y ademas permite que cualquier usuario se
autopromueva a admin, se autoapruebe como abogado, o lea el chat/codigos de
verificacion de otros. Detalle completo de lo verificado en vivo (lecturas
de prueba contra la base, sin escrituras) en la conversacion original.

## Que ya esta hecho en este commit (no rompe nada, listo para desplegar)

1. **`supabase/supabase/functions/admin-actions/index.ts`** — nueva Edge
   Function. Recibe un `id_token` de Firebase, lo valida contra Firebase, y
   confirma `usuarios.rol = 'admin'` antes de: aprobar abogado, bloquear
   abogado, reactivar abogado, procesar retiro, editar precios, listar
   retiros pendientes.
2. **`supabase_config.py`** — `aprobar_abogado`, `desactivar_suscripcion_abogado`,
   `reactivar_abogado`, `procesar_retiro`, `actualizar_configuracion`,
   `listar_retiros_pendientes` ahora llaman a `admin-actions` en vez de
   escribir/leer directo con la anon key.
3. **`views/admin_panel.py`** — los llamados de arriba ahora mandan
   `session.id_token` (el id_token de Firebase del admin logueado).
4. **`supabase/supabase/sql/02_lockdown_admin_columns.sql`** — le saca a la
   anon key el permiso de escribir `usuarios.rol`, `usuarios.aprobado`,
   `retiros` (update) y `configuracion` (update), y bloquea del todo
   `codigos_verificacion`.
5. **`supabase/supabase/sql/03_rls_completo_firebase_auth.sql`** — borrador
   de RLS completo (usuarios, consultas, mensajes, retiros, resenas,
   pagos_procesados) usando Firebase como Third-Party Auth de Supabase.
   Marcado explicitamente como "no correr todavia".
6. **`security/firebase_hardening.md`** — checklist de Firebase (API key,
   App Check, IAM) sin rotar ninguna clave.
7. **`security/PACKAGING_REVIEW.md`** — que claves quedan dentro del
   APK/AAB y cuales no.

## Hallazgo extra: no existia ninguna cuenta admin real

El panel de administrador se abria con un codigo fijo escrito en
`views/login.py` (`LegalAdmin2024`), sin ningun usuario real de por medio.
Eso quedaba adentro del APK, legible por cualquiera que lo descompile. Se
saco ese atajo: `views/login.py` ahora solo deja entrar al panel si la
cuenta logueada tiene `rol = 'admin'` en Supabase (nada nuevo del lado de
Firebase, es el mismo campo `rol` que ya usan cliente/abogado). Falta un
paso manual, unico: crear esa cuenta.

## Crear la cuenta admin (una sola vez, a mano)

1. Registrate en la app como usuario normal, con el email y contraseña que
   quieras usar como admin (puede ser una cuenta nueva o una que ya
   tengas). No importa que rol te de el registro (cliente/abogado).
2. En el SQL Editor de Supabase, con TU usuario (no con la anon key, esto
   no se puede hacer desde la app a proposito):
   ```sql
   update public.usuarios
   set rol = 'admin', aprobado = true, email_verified = true
   where email = 'tu-email-elegido@ejemplo.com';
   ```
3. Deslogueate y volve a entrar con ese email/password. Al tocar 7 veces el
   titulo de la pantalla de login deberia entrar directo al panel (ya no
   pide ningun codigo).

Este paso hay que hacerlo ANTES de correr `02_lockdown_admin_columns.sql`
(ese script agrega un trigger que impide crear una cuenta con rol=admin
directamente desde la app, para que este atajo no se pueda repetir de
otra forma).

## Orden para activar esto (importante)

```
1. supabase functions deploy admin-actions                    [YA HECHO]
2. supabase secrets set FIREBASE_API_KEY=xxx                   [YA HECHO]
   (SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY los pone Supabase solo)
3. Crear la cuenta admin real (seccion de arriba).
4. Probar desde el panel de admin (compilando la app local, sin publicar
   todavia) que aprobar abogado / procesar retiro / editar precio siguen
   funcionando llamando a la funcion nueva.
5. Recien ahi correr supabase/supabase/sql/02_lockdown_admin_columns.sql
   en el SQL Editor de Supabase.
6. Publicar la nueva version de la app (con los cambios de admin_panel.py /
   supabase_config.py / login.py) en Google Play.
```

Los pasos 1-5 no necesitan que los usuarios finales actualicen la app (son
cambios de servidor + de la cuenta de administrador). El paso 6 si es una
nueva version, pero no es urgente para que 02_lockdown_admin_columns.sql
tenga efecto — lo urgente es que quien use el panel de administrador (vos)
tenga la version nueva del codigo antes de correr el SQL.

## Lo que queda pendiente (fuera del alcance de este commit)

- **`saldo`, `suscripcion_activa`, `suscripcion_fecha`, `suscripcion_monto`
  de `usuarios` siguen siendo escribibles por cualquiera con la anon key.**
  Hoy se activan client-side despues de que el propio cliente decide que
  MercadoPago aprobo el pago (`activar_suscripcion_abogado`,
  `acreditar_honorario`, `sincronizar_saldo_abogado` en
  `supabase_config.py`). En teoria alguien podria llamar a esas escrituras
  sin haber pagado. El arreglo correcto es mover la confirmacion de pago
  entera a `mercadopago-proxy` (que ya verifica el pago contra la API real
  de MercadoPago) para que sea esa Edge Function, y no el cliente, la que
  escriba `usuarios`/`consultas` despues de confirmar. No se toco en este
  commit porque es codigo de dinero real y prefiero que lo revises antes de
  que lo cambie.
- **Lectura amplia de `usuarios`, `mensajes`, `consultas`, `resenas`**
  sigue abierta con la anon key (nombre, telefono, chats privados, etc.).
  El arreglo de fondo es el Track A completo
  (`03_rls_completo_firebase_auth.sql`): activar Firebase como Third-Party
  Auth de Supabase + que la app mande el id_token de Firebase como
  `Authorization` en cada llamada (hoy manda la anon key siempre, ver
  `supabase_config.py` -> `HEADERS`). Eso requiere: activarlo en el
  Dashboard de Supabase, cambiar `_rest_get/_rest_post/_rest_patch/_rest_delete`
  en `supabase_config.py` para usar `session.id_token`, y publicar una
  nueva version — recien ahi correr el script 03. Es un cambio mas grande
  y con mas superficie para romper flujos existentes (login, registro,
  recuperacion de pagos), asi que lo dejo listo como borrador para
  revisarlo con calma en vez de aplicarlo de una.
- `codigos_verificacion` queda totalmente bloqueada por el script 02, lo
  que apaga el fallback de "codigo manual" de verificacion de email (la
  verificacion por link de Firebase sigue funcionando igual). Si ese
  fallback se usa en produccion, avisa antes de correr el script 02 para
  moverlo a una Edge Function en vez de bloquearlo.
