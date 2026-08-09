// admin-actions
//
// Centraliza las escrituras que hoy hace el cliente directo contra Postgres
// con la anon key: aprobar abogado, activar/desactivar suscripcion, procesar
// retiros y editar precios. Ninguna de esas operaciones puede depender de
// RLS por fila porque toda la app comparte la misma anon key (no hay
// Supabase Auth), asi que la verificacion de "es admin" se hace aca, en el
// unico lugar que tiene la service_role key.
//
// Verificacion: se recibe el id_token de Firebase del usuario logueado, se
// valida contra Firebase (accounts:lookup) para obtener el uid real, y se
// confirma que ese uid tiene rol='admin' en la tabla usuarios. Recien ahi se
// ejecuta la accion con la service_role key.

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_ROLE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const FIREBASE_API_KEY = Deno.env.get("FIREBASE_API_KEY")!;

const corsHeaders = {
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

function json(obj: unknown, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: corsHeaders });
}

async function verificarAdmin(
  idToken: string | undefined,
  supabase: ReturnType<typeof createClient>,
): Promise<{ ok: true; uid: string } | { ok: false; error: string }> {
  if (!idToken) return { ok: false, error: "Falta id_token del administrador" };
  if (!FIREBASE_API_KEY) return { ok: false, error: "Falta FIREBASE_API_KEY en secrets" };

  const res = await fetch(
    `https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=${FIREBASE_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idToken }),
    },
  );
  const data = await res.json();
  const users = data?.users || [];
  if (!res.ok || users.length === 0) {
    return { ok: false, error: "Token de Firebase invalido o expirado" };
  }
  const uid = String(users[0].localId);

  const { data: userRow, error } = await supabase
    .from("usuarios")
    .select("rol")
    .eq("uid", uid)
    .single();

  if (error || !userRow || userRow.rol !== "admin") {
    return { ok: false, error: "El usuario no tiene permisos de administrador" };
  }
  return { ok: true, uid };
}

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const body = await req.json();
    const action = String(body?.action || "");

    const supabase = createClient(SUPABASE_URL, SERVICE_ROLE_KEY);

    const admin = await verificarAdmin(body?.id_token, supabase);
    if (!admin.ok) {
      return json({ ok: false, error: admin.error }, 403);
    }

    switch (action) {
      case "aprobar_abogado": {
        const uid = String(body?.uid || "");
        if (!uid) return json({ ok: false, error: "Falta uid" }, 400);

        const { data: user } = await supabase
          .from("usuarios")
          .select("email_verified,suscripcion_activa,suscripcion_fecha,suscripcion_monto")
          .eq("uid", uid)
          .single();

        if (!user) return json({ ok: false, error: "No se encontro el abogado" });
        if (!user.email_verified) {
          return json({ ok: false, error: "No se puede aprobar: el email no esta verificado" });
        }
        const suscripcionValida = Boolean(user.suscripcion_activa) &&
          Boolean(user.suscripcion_fecha) &&
          Number(user.suscripcion_monto || 0) > 0;
        if (!suscripcionValida) {
          return json({ ok: false, error: "No se puede aprobar: falta una suscripcion paga valida" });
        }

        const { error } = await supabase.from("usuarios").update({ aprobado: true }).eq("uid", uid);
        if (error) return json({ ok: false, error: error.message });
        return json({ ok: true, mensaje: "Abogado aprobado" });
      }

      case "desactivar_suscripcion": {
        const uid = String(body?.uid || "");
        if (!uid) return json({ ok: false, error: "Falta uid" }, 400);

        const { error } = await supabase
          .from("usuarios")
          .update({ suscripcion_activa: false, estado_abogado: "ocupado" })
          .eq("uid", uid);
        if (error) return json({ ok: false, error: error.message });
        return json({ ok: true });
      }

      case "reactivar_abogado": {
        const uid = String(body?.uid || "");
        if (!uid) return json({ ok: false, error: "Falta uid" }, 400);

        const { data: user } = await supabase
          .from("usuarios")
          .select("suscripcion_fecha,suscripcion_monto")
          .eq("uid", uid)
          .single();

        if (!user) return json({ ok: false, error: "No se encontro el abogado" });
        const suscripcionValida = Boolean(user.suscripcion_fecha) &&
          Number(user.suscripcion_monto || 0) > 0;
        if (!suscripcionValida) {
          return json({ ok: false, error: "No se puede reactivar: no hay una suscripcion paga valida" });
        }

        const { error } = await supabase
          .from("usuarios")
          .update({ suscripcion_activa: true, estado_abogado: "disponible" })
          .eq("uid", uid);
        if (error) return json({ ok: false, error: error.message });
        return json({ ok: true, mensaje: "Abogado reactivado" });
      }

      case "procesar_retiro": {
        const retiroId = body?.retiro_id;
        if (!retiroId) return json({ ok: false, error: "Falta retiro_id" }, 400);

        const { data: retiro } = await supabase
          .from("retiros")
          .select("*")
          .eq("id", retiroId)
          .single();

        if (!retiro) return json({ ok: false, error: "Retiro no encontrado" });
        if (retiro.estado !== "pendiente") return json({ ok: false, error: "Ya procesado" });

        const { error } = await supabase
          .from("retiros")
          .update({
            estado: "pagado",
            pagado_at: new Date().toISOString(),
            admin_uid: admin.uid,
          })
          .eq("id", retiroId);
        if (error) return json({ ok: false, error: error.message });

        return json({
          ok: true,
          mensaje: `Retiro $${retiro.monto_neto} pagado`,
          abogado_uid: retiro.abogado_uid,
          monto_neto: retiro.monto_neto,
        });
      }

      case "actualizar_configuracion": {
        const clave = String(body?.clave || "");
        const valor = String(body?.valor ?? "");
        if (!clave) return json({ ok: false, error: "Falta clave" }, 400);

        const { error } = await supabase
          .from("configuracion")
          .update({ valor })
          .eq("clave", clave);
        if (error) return json({ ok: false, error: error.message });
        return json({ ok: true });
      }

      case "listar_retiros_pendientes": {
        const { data, error } = await supabase
          .from("retiros")
          .select("*")
          .eq("estado", "pendiente")
          .order("fecha", { ascending: true });
        if (error) return json({ ok: false, error: error.message });
        return json({ ok: true, retiros: data || [] });
      }

      default:
        return json({ ok: false, error: "Accion no soportada" }, 400);
    }
  } catch (err) {
    console.error("admin-actions error:", err);
    return json({ ok: false, error: String(err) }, 500);
  }
});
