-- Legal App - Blindaje de aprobacion de abogados
-- Objetivo:
-- 1) Detectar abogados aprobados sin email verificado o sin suscripcion paga valida.
-- 2) Corregir los ya existentes si hiciera falta.
-- 3) Evitar que vuelva a pasar con un trigger en la tabla usuarios.

-- =========================================================
-- AUDITORIA
-- =========================================================
-- Ejecutar primero este SELECT para ver si hoy hay abogados mal aprobados.
select
  uid,
  nombre,
  email,
  rol,
  aprobado,
  email_verified,
  suscripcion_activa,
  suscripcion_fecha,
  suscripcion_monto
from public.usuarios
where rol = 'abogado'
  and aprobado = true
  and (
    coalesce(email_verified, false) = false
    or coalesce(suscripcion_activa, false) = false
    or suscripcion_fecha is null
    or coalesce(suscripcion_monto, 0) <= 0
  );

-- =========================================================
-- CORRECCION DE DATOS ACTUALES
-- =========================================================
-- Si el SELECT anterior devuelve filas, este UPDATE las vuelve a pendiente.
update public.usuarios
set aprobado = false
where rol = 'abogado'
  and aprobado = true
  and (
    coalesce(email_verified, false) = false
    or coalesce(suscripcion_activa, false) = false
    or suscripcion_fecha is null
    or coalesce(suscripcion_monto, 0) <= 0
  );

-- =========================================================
-- TRIGGER DE PROTECCION
-- =========================================================
create or replace function public.fn_validar_aprobacion_abogado()
returns trigger
language plpgsql
as $$
begin
  if new.rol = 'abogado' then
    if coalesce(new.suscripcion_activa, false) = true then
      if new.suscripcion_fecha is null or coalesce(new.suscripcion_monto, 0) <= 0 then
        raise exception 'No se puede activar la suscripcion del abogado sin fecha y monto valido';
      end if;
    end if;

    if coalesce(new.aprobado, false) = true then
      if coalesce(new.email_verified, false) = false then
        raise exception 'No se puede aprobar un abogado sin email verificado';
      end if;

      if coalesce(new.suscripcion_activa, false) = false
         or new.suscripcion_fecha is null
         or coalesce(new.suscripcion_monto, 0) <= 0 then
        raise exception 'No se puede aprobar un abogado sin suscripcion paga valida';
      end if;
    end if;
  end if;

  return new;
end;
$$;

drop trigger if exists trg_validar_aprobacion_abogado on public.usuarios;

create trigger trg_validar_aprobacion_abogado
before insert or update on public.usuarios
for each row
execute function public.fn_validar_aprobacion_abogado();

-- =========================================================
-- VERIFICACION FINAL
-- =========================================================
select
  uid,
  nombre,
  email,
  rol,
  aprobado,
  email_verified,
  suscripcion_activa,
  suscripcion_fecha,
  suscripcion_monto
from public.usuarios
where rol = 'abogado'
order by id desc nulls last;
