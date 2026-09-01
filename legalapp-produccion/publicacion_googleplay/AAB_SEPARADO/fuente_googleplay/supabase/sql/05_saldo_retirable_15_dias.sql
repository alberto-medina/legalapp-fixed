-- Fix: agrega la columna saldo_retirable a usuarios, usada por la nueva
-- regla de bases y condiciones: los honorarios quedan disponibles para
-- retirar recien a partir de los 15 dias de pagada la consulta (antes,
-- solicitar_retiro() validaba contra el saldo total sin ninguna espera).
--
-- saldo se sigue calculando igual que antes (total acreditado menos lo ya
-- retirado). saldo_retirable es un subconjunto de saldo: solo la parte que
-- corresponde a consultas con mas de 15 dias. Los dos los recalcula
-- sincronizar_saldo_abogado() en supabase_config.py cada vez que se entra
-- al panel del abogado o se pide un retiro.

alter table public.usuarios
  add column if not exists saldo_retirable numeric not null default 0;
