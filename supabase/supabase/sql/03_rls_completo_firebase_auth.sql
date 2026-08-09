-- 03_rls_completo_firebase_auth.sql
--
-- BORRADOR / PUNTO DE PARTIDA. No correr en produccion sin probar antes en
-- un proyecto de Supabase de prueba con una copia de la app. Este script
-- asume cosas que TODAVIA no son ciertas en la app instalada hoy y, si se
-- corre antes de tiempo, deja a todos los usuarios (incluidos los que ya
-- tienen la app instalada) sin poder leer ni escribir nada.
--
-- Por que hace falta esto y no alcanza con el 02_lockdown_admin_columns.sql:
-- Ese script bloquea columnas puntuales (rol, aprobado, retiros,
-- configuracion, codigos_verificacion), pero usuarios, consultas, mensajes
-- y resenas siguen siendo legibles ENTERAS por cualquiera con la anon key
-- (que viaja dentro del APK). Eso incluye los mensajes de chat privados
-- entre cliente y abogado, telefonos, cuentas bancarias, etc. La unica
-- forma de arreglar esto sin romper la app es que Postgres pueda saber
-- REALMENTE quien esta pidiendo cada fila, y hoy no puede: todo el mundo
-- usa la misma anon key porque el login es con Firebase, no con Supabase
-- Auth.
--
-- La solucion (soportada oficialmente por Supabase, "Third-Party Auth"):
-- decirle a Supabase que confie en los tokens que ya emite Firebase Auth.
-- Con eso, cuando el cliente mande el id_token de Firebase como
-- Authorization: Bearer, Postgres puede leer auth.jwt()->>'sub' (el uid de
-- Firebase) y compararlo contra las filas.
--
-- PASOS EN ORDEN (los 3 primeros son requisito, no opcional):
--   1) Dashboard de Supabase > Authentication > Sign In / Providers >
--      Third Party Auth > agregar Firebase Auth, con el Project ID
--      "legalapp-pro" (ver supabase/supabase/config.toml,
--      [auth.third_party.firebase]).
--   2) Actualizar supabase_config.py para que cada llamada autenticada
--      mande Authorization: Bearer <id_token de Firebase> en vez del anon
--      key (el header apikey se queda igual, siempre con el anon key).
--      session.id_token ya existe en session.py; falta usarlo en los
--      headers de _rest_get/_rest_post/_rest_patch/_rest_delete.
--   3) Compilar, firmar y publicar una nueva version en Google Play, y
--      esperar a que la mayoria de usuarios activos la tengan instalada
--      (mientras tanto, la version vieja va a fallar en todo lo que este
--      script proteja, porque sigue mandando la anon key como Bearer).
--   4) Recien ahi correr este script completo, tabla por tabla, revisando
--      cada pantalla de la app despues de cada tabla.
--
-- Nota sobre auth.uid(): con third-party auth se recomienda usar
-- auth.jwt()->>'sub' en vez de auth.uid() para evitar ambiguedad con
-- versiones viejas de Postgres/GoTrue. Esta guia usa auth.jwt()->>'sub' en
-- todos lados por eso.

-- =========================================================
-- 0) VISTA PUBLICA PARA EL DIRECTORIO DE ABOGADOS
-- =========================================================
-- Una vista sin "security_invoker" corre con los permisos de quien la creo,
-- no con los del que la consulta, asi que puede exponer columnas puntuales
-- de una tabla que por otro lado va a quedar con RLS estricta.
create or replace view public.abogados_publico as
select
  uid,
  nombre,
  foto_url,
  especialidad,
  especialidades,
  descripcion,
  experiencia,
  provincia,
  ciudad,
  estado_abogado
from public.usuarios
where rol = 'abogado'
  and aprobado = true
  and suscripcion_activa = true;

grant select on public.abogados_publico to anon, authenticated;

-- La app deberia pasar a usar esta vista para listar_abogados() en vez de
-- pedir la tabla usuarios entera con filtros.

-- =========================================================
-- 1) USUARIOS
-- =========================================================
alter table public.usuarios enable row level security;

drop policy if exists usuarios_select_propio on public.usuarios;
create policy usuarios_select_propio
  on public.usuarios for select
  to authenticated
  using ((auth.jwt() ->> 'sub') = uid);

drop policy if exists usuarios_insert_propio on public.usuarios;
create policy usuarios_insert_propio
  on public.usuarios for insert
  to authenticated
  with check ((auth.jwt() ->> 'sub') = uid);

drop policy if exists usuarios_update_propio on public.usuarios;
create policy usuarios_update_propio
  on public.usuarios for update
  to authenticated
  using ((auth.jwt() ->> 'sub') = uid)
  with check ((auth.jwt() ->> 'sub') = uid);
-- Las columnas rol/aprobado siguen bloqueadas por el REVOKE del script 02,
-- que se sigue aplicando ademas de esta policy.

-- OJO: revisar antes de aplicar. Al menos un caso conocido va a quedar roto
-- y necesita ajuste: recuperar_consultas_pagadas_cliente() en
-- supabase_config.py lee obtener_usuario(abogado_uid) para sacar el email
-- del abogado al recrear una consulta pagada; con esta policy esa lectura
-- va a devolver vacio si el que llama no es ese abogado. Alternativa:
-- resolver ese dato desde abogados_publico, o agregar una policy adicional
-- que permita leer nombre/email de la contraparte de una consulta propia.

-- =========================================================
-- 2) CONSULTAS
-- =========================================================
alter table public.consultas enable row level security;

drop policy if exists consultas_select_participante on public.consultas;
create policy consultas_select_participante
  on public.consultas for select
  to authenticated
  using (
    (auth.jwt() ->> 'sub') = cliente_uid
    or (auth.jwt() ->> 'sub') = abogado_uid
  );

drop policy if exists consultas_insert_propio on public.consultas;
create policy consultas_insert_propio
  on public.consultas for insert
  to authenticated
  with check ((auth.jwt() ->> 'sub') = cliente_uid);

drop policy if exists consultas_update_participante on public.consultas;
create policy consultas_update_participante
  on public.consultas for update
  to authenticated
  using (
    (auth.jwt() ->> 'sub') = cliente_uid
    or (auth.jwt() ->> 'sub') = abogado_uid
  );

-- =========================================================
-- 3) MENSAJES (chat privado)
-- =========================================================
alter table public.mensajes enable row level security;

drop policy if exists mensajes_select_participante on public.mensajes;
create policy mensajes_select_participante
  on public.mensajes for select
  to authenticated
  using (
    exists (
      select 1 from public.consultas c
      where c.id = mensajes.consulta_id
        and (
          (auth.jwt() ->> 'sub') = c.cliente_uid
          or (auth.jwt() ->> 'sub') = c.abogado_uid
        )
    )
  );

drop policy if exists mensajes_insert_participante on public.mensajes;
create policy mensajes_insert_participante
  on public.mensajes for insert
  to authenticated
  with check (
    (auth.jwt() ->> 'sub') = emisor_uid
    and exists (
      select 1 from public.consultas c
      where c.id = mensajes.consulta_id
        and (
          (auth.jwt() ->> 'sub') = c.cliente_uid
          or (auth.jwt() ->> 'sub') = c.abogado_uid
        )
    )
  );

-- eliminar_mensaje_chat() hace un UPDATE (deja el texto en un marcador de
-- "eliminado"); agregar policy de UPDATE analoga si se quiere permitir
-- borrar solo los mensajes propios:
drop policy if exists mensajes_update_propio on public.mensajes;
create policy mensajes_update_propio
  on public.mensajes for update
  to authenticated
  using ((auth.jwt() ->> 'sub') = emisor_uid);

-- =========================================================
-- 4) RESENAS
-- =========================================================
-- Las calificaciones son publicas a proposito (se muestran a clientes
-- potenciales antes de elegir abogado), asi que se deja SELECT abierto.
-- Igual queda con RLS habilitada para poder controlar el INSERT.
alter table public.resenas enable row level security;

drop policy if exists resenas_select_publico on public.resenas;
create policy resenas_select_publico
  on public.resenas for select
  to anon, authenticated
  using (true);

drop policy if exists resenas_insert_participante on public.resenas;
create policy resenas_insert_participante
  on public.resenas for insert
  to authenticated
  with check (
    exists (
      select 1 from public.consultas c
      where c.id = resenas.consulta_id
        and (auth.jwt() ->> 'sub') = c.cliente_uid
    )
  );

-- =========================================================
-- 5) RETIROS
-- =========================================================
alter table public.retiros enable row level security;

drop policy if exists retiros_select_propio on public.retiros;
create policy retiros_select_propio
  on public.retiros for select
  to authenticated
  using ((auth.jwt() ->> 'sub') = abogado_uid);

drop policy if exists retiros_insert_propio on public.retiros;
create policy retiros_insert_propio
  on public.retiros for insert
  to authenticated
  with check ((auth.jwt() ->> 'sub') = abogado_uid);
-- UPDATE sigue sin ninguna policy (bloqueado desde el script 02): solo
-- admin-actions con service_role puede marcar un retiro como pagado.

-- =========================================================
-- 6) CONFIGURACION (precios)
-- =========================================================
-- Sigue siendo publica para lectura (la app necesita mostrar precios antes
-- de loguearse); UPDATE sigue bloqueado desde el script 02.
alter table public.configuracion enable row level security;

drop policy if exists configuracion_select_publico on public.configuracion;
create policy configuracion_select_publico
  on public.configuracion for select
  to anon, authenticated
  using (true);

-- =========================================================
-- 7) PAGOS_PROCESADOS
-- =========================================================
-- El external_reference sigue el formato
-- "consulta|<cliente_uid>|<abogado_uid>|<tipo>|..." (ver supabase_config.py
-- crear_consulta / buscar_pago_procesado_disponible). Esta policy es un
-- best-effort basado en ese formato; si el formato cambia, hay que
-- actualizarla.
alter table public.pagos_procesados enable row level security;

drop policy if exists pagos_select_propio on public.pagos_procesados;
create policy pagos_select_propio
  on public.pagos_procesados for select
  to authenticated
  using (
    external_reference like '%' || (auth.jwt() ->> 'sub') || '%'
  );

-- =========================================================
-- codigos_verificacion: sigue bloqueada del script 02, no se toca aca.
-- =========================================================
