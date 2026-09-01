-- Campanita de avisos (cliente + abogado): reemplaza el boton "Avisos" por
-- un icono con badge de cantidad de notificaciones nuevas.
--
-- 1. usuarios.ultimo_visto_avisos: timestamp de la ultima vez que el usuario
--    abrio el popup de avisos. NULL = nunca lo abrio (todo cuenta como
--    nuevo).
-- 2. consultas.estado_actualizado_at: timestamp de la ultima vez que cambio
--    el campo "estado" de esa consulta. Se mantiene con un trigger (no a
--    mano desde la app) para que sea correcto sin importar que funcion del
--    lado del cliente haga el update.

alter table public.usuarios
  add column if not exists ultimo_visto_avisos timestamptz;

alter table public.consultas
  add column if not exists estado_actualizado_at timestamptz not null default now();

create or replace function public.trg_actualizar_estado_timestamp()
returns trigger as $$
begin
  if new.estado is distinct from old.estado then
    new.estado_actualizado_at = now();
  end if;
  return new;
end;
$$ language plpgsql;

drop trigger if exists set_estado_actualizado_at on public.consultas;

create trigger set_estado_actualizado_at
before update on public.consultas
for each row
execute function public.trg_actualizar_estado_timestamp();
