-- 02_lockdown_admin_columns.sql
--
-- Orden de ejecucion (importante, en este orden):
--   1) supabase functions deploy admin-actions
--   2) supabase secrets set SUPABASE_SERVICE_ROLE_KEY=... FIREBASE_API_KEY=...
--   3) Confirmar que supabase_config.py y views/admin_panel.py ya llaman a
--      admin-actions (aprobar_abogado, desactivar_suscripcion_abogado,
--      reactivar_abogado, procesar_retiro, actualizar_configuracion) en vez
--      de escribir directo con la anon key.
--   4) Recien ahi correr este script.
--
-- Si lo corres ANTES de desplegar admin-actions y actualizar el codigo,
-- el panel de administrador deja de poder aprobar abogados, procesar
-- retiros y cambiar precios (porque la anon key pierde el permiso), asi
-- que segui el orden de arriba.
--
-- Que arregla:
-- Hoy CUALQUIER usuario logueado (o incluso sin loguearse, con la anon key
-- que trae el APK) puede hacer un PATCH directo a Supabase y:
--   - ponerse rol='admin' a si mismo
--   - ponerse aprobado=true sin que ningun admin lo revise
--   - marcar un retiro como pagado
--   - cambiar los precios de la app (configuracion)
--   - leer el codigo de verificacion de CUALQUIER otro usuario y tomar su cuenta
-- porque todas esas escrituras se hacian directo desde el cliente sin que
-- nadie del lado del servidor verifique quien las esta pidiendo.
--
-- Que NO arregla (queda pendiente, ver README.md):
-- saldo, suscripcion_activa, suscripcion_fecha y suscripcion_monto de
-- usuarios siguen siendo escribibles por el cliente, porque hoy se activan
-- ahi mismo despues de un pago de MercadoPago. Mover eso a una Edge
-- Function (igual que se hizo aca con aprobar_abogado) es el siguiente
-- paso: mientras tanto alguien podria simular un pago aprobado sin pagar.

-- =========================================================
-- USUARIOS: nadie puede cambiarse el rol ni auto-aprobarse
-- =========================================================
-- OJO: "revoke update (columna) ... from anon" NO alcanza aca, porque
-- Supabase le da a anon/authenticated el UPDATE de la tabla entera por
-- default, y ese permiso de tabla completa le gana al revoke de columna
-- (asi funciona Postgres: el permiso mas amplio manda). Por eso esto se
-- hace con un trigger, que compara el valor viejo contra el nuevo y
-- rechaza el UPDATE si alguien intenta tocar rol/aprobado sin ser
-- service_role (osea, sin pasar por admin-actions).
-- OJO 2 (2026-08-08): el SQL Editor de Supabase corre como rol "postgres",
-- NO como "service_role" - un chequeo que solo permitia 'service_role'
-- bloqueaba tambien las correcciones manuales a mano desde el SQL Editor
-- (justo el camino documentado en README.md para promover un admin o
-- aprobar un abogado a mano). Se permiten los dos roles.
create or replace function public.fn_bloquear_cambio_rol_aprobado()
returns trigger
language plpgsql
as $$
begin
  if current_user not in ('service_role', 'postgres') then
    if new.rol is distinct from old.rol then
      raise exception 'No autorizado para cambiar rol. Usar admin-actions.';
    end if;
    if new.aprobado is distinct from old.aprobado then
      raise exception 'No autorizado para cambiar aprobado. Usar admin-actions.';
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists trg_bloquear_cambio_rol_aprobado on public.usuarios;
create trigger trg_bloquear_cambio_rol_aprobado
before update on public.usuarios
for each row
execute function public.fn_bloquear_cambio_rol_aprobado();

-- Ademas de bloquear el UPDATE, hace falta bloquear el INSERT (alguien
-- podria registrarse de cero mandando "rol":"admin" en el alta; la app
-- manda ese campo libremente en crear_usuario_db/crear_usuario_con_auth).
-- Este trigger fuerza que ningun registro nuevo pueda entrar con rol admin;
-- la unica forma de tener un admin es promoverlo a mano desde el SQL
-- Editor (ver security/README.md, seccion "Crear la cuenta admin").
create or replace function public.fn_bloquear_alta_admin()
returns trigger
language plpgsql
as $$
begin
  if new.rol = 'admin' then
    raise exception 'No se puede crear un usuario con rol admin via la API. Usar el SQL Editor.';
  end if;
  return new;
end;
$$;

drop trigger if exists trg_bloquear_alta_admin on public.usuarios;
create trigger trg_bloquear_alta_admin
before insert on public.usuarios
for each row
execute function public.fn_bloquear_alta_admin();

-- =========================================================
-- RETIROS: se puede pedir un retiro (insert), pero aprobarlo/pagarlo
-- solo lo hace admin-actions con service_role (que no le pide permiso a
-- estos grants).
-- =========================================================
revoke update on public.retiros from anon, authenticated;

-- =========================================================
-- CONFIGURACION (precios de la app): solo admin-actions
-- =========================================================
revoke update on public.configuracion from anon, authenticated;

-- =========================================================
-- CODIGOS_VERIFICACION: hoy cualquiera con la anon key (la misma que trae
-- el APK) puede leer los codigos de 6 digitos de TODOS los usuarios y usar
-- eso para tomar el control de una cuenta. Se bloquea del todo.
--
-- Efecto colateral: esto apaga el fallback de "codigo manual" en
-- enviar_codigo_verificacion() / verificar_email_con_codigo() en
-- supabase_config.py. La verificacion por link de Firebase (el camino
-- principal, el que se usa siempre que hay id_token) NO se ve afectada.
-- Si preferis mantener el fallback, avisa antes de correr este bloque y lo
-- movemos a una Edge Function en lugar de bloquearlo.
-- =========================================================
alter table public.codigos_verificacion enable row level security;
-- Sin ninguna policy: nadie salvo service_role puede leer ni escribir.

-- =========================================================
-- VERIFICACION
-- =========================================================
-- Debe mostrar los dos triggers en usuarios:
select trigger_name, event_manipulation
from information_schema.triggers
where event_object_schema = 'public'
  and event_object_table = 'usuarios'
  and trigger_name in ('trg_bloquear_cambio_rol_aprobado', 'trg_bloquear_alta_admin');

-- No deberia devolver ninguna fila con privilege_type = 'UPDATE':
select grantee, table_name, privilege_type
from information_schema.table_privileges
where table_schema = 'public'
  and table_name in ('retiros', 'configuracion')
  and grantee in ('anon', 'authenticated')
  and privilege_type = 'UPDATE';

-- Debe mostrar rowsecurity = true:
select tablename, rowsecurity
from pg_tables
where schemaname = 'public'
  and tablename = 'codigos_verificacion';
