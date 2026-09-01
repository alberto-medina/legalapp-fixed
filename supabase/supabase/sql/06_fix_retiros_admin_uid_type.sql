-- Fix: la columna retiros.admin_uid estaba tipada como uuid, pero
-- admin-actions (accion procesar_retiro) siempre guarda ahi el UID de
-- Firebase del admin (ej. "LPJd7WDCBqYIe0nciwXGYquNHfP2"), que no tiene
-- formato de uuid valido. Mismo patron exacto que el bug ya arreglado en
-- retiros.abogado_uid (ver 04_fix_retiros_abogado_uid_type.sql) -- esta
-- columna quedo afuera en esa pasada. Resultado: marcar un retiro como
-- pagado fallaba siempre, para cualquier admin, con
-- "invalid input syntax for type uuid".

alter table public.retiros drop constraint if exists retiros_admin_uid_fkey;

alter table public.retiros
  alter column admin_uid type text using admin_uid::text;
