-- Fix: la columna retiros.abogado_uid estaba tipada como uuid, pero la app
-- siempre guarda ahi el UID de Firebase (ej. "EH6q1mmcjAaHczvcN3oFBwibgIm2"),
-- que no tiene formato de uuid valido. Resultado: TODO pedido de retiro de
-- CUALQUIER abogado fallaba con error 22P02 "invalid input syntax for type
-- uuid" (confirmado en vivo el 2026-08-23 reproduciendo la consulta real de
-- solicitar_retiro() contra la base de produccion).
--
-- Este cambio solo amplia el tipo de la columna (uuid -> text), no borra ni
-- transforma datos existentes -- cualquier uuid ya guardado se convierte
-- limpio a su representacion en texto.
--
-- Se encontro ademas una foreign key ("retiros_abogado_uid_fkey") que
-- apuntaba abogado_uid a la columna "id" (uuid) de otra tabla -- muy
-- probablemente el id interno autogenerado de Supabase, no el UID de
-- Firebase que la app realmente usa. Como TODO insert fallaba antes por el
-- error de tipo, esa FK nunca se pudo cumplir ni una sola vez en produccion
-- -- no hay filas reales que dependan de ella, es seguro sacarla.

alter table public.retiros drop constraint if exists retiros_abogado_uid_fkey;

alter table public.retiros
  alter column abogado_uid type text using abogado_uid::text;
