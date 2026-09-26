import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

// =========================================================
// Webhook de RevenueCat -- "Legal App Pro" (abogado destacado)
//
// RevenueCat manda un POST cada vez que cambia el estado de una
// suscripcion (compra inicial, renovacion, cancelacion, vencimiento).
// Esta funcion toma esos eventos y actualiza usuarios.es_pro_destacado /
// pro_destacado_hasta -- asi abogados.py puede ordenar y mostrar la
// insignia "PRO" sin tener que consultar a RevenueCat en cada busqueda.
//
// El "app_user_id" que manda RevenueCat tiene que ser el mismo uid de
// Firebase que usa el resto de la app (se configura al armar el link de
// compra, ver ir_hacerse_pro() en views/perfil_abogado.py).
// =========================================================

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const REVENUECAT_WEBHOOK_SECRET = Deno.env.get("REVENUECAT_WEBHOOK_SECRET")!;

// Eventos que significan "el Pro esta activo ahora".
const EVENTOS_ACTIVAN_PRO = new Set([
  "INITIAL_PURCHASE",
  "RENEWAL",
  "UNCANCELLATION",
  "PRODUCT_CHANGE",
]);

// OJO: "CANCELLATION" NO se trata como baja inmediata -- solo significa
// que no se va a renovar, pero el usuario sigue Pro hasta que vence de
// verdad. Solo "EXPIRATION" apaga el Pro.
const EVENTO_DESACTIVA_PRO = "EXPIRATION";

serve(async (req) => {
  try {
    // RevenueCat manda el secreto compartido (configurado igual en el
    // dashboard, "Authorization header value" del webhook) -- sin esto
    // cualquiera podria pegarle a esta URL y marcar abogados como Pro
    // gratis.
    const auth = req.headers.get("Authorization") || "";
    if (auth !== `Bearer ${REVENUECAT_WEBHOOK_SECRET}`) {
      return new Response(JSON.stringify({ ok: false, error: "unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      });
    }

    const body = await req.json();
    const event = body?.event;
    if (!event) {
      return new Response(JSON.stringify({ ok: false, error: "sin evento" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }

    const tipo = String(event.type || "");
    const uid = String(event.app_user_id || "").trim();
    const expiraMs = event.expiration_at_ms;
    const expiraEn = expiraMs ? new Date(expiraMs).toISOString() : null;

    console.log("RevenueCat webhook:", tipo, "uid=", uid, "expira=", expiraEn);

    if (!uid) {
      // No deberia pasar si el link de compra se arma bien, pero no es
      // motivo para que RevenueCat reintente el webhook.
      return new Response(JSON.stringify({ ok: true, aviso: "sin app_user_id" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

    if (EVENTOS_ACTIVAN_PRO.has(tipo)) {
      await supabase
        .from("usuarios")
        .update({ es_pro_destacado: true, pro_destacado_hasta: expiraEn })
        .eq("uid", uid);
    } else if (tipo === EVENTO_DESACTIVA_PRO) {
      await supabase
        .from("usuarios")
        .update({ es_pro_destacado: false, pro_destacado_hasta: expiraEn })
        .eq("uid", uid);
    } else {
      console.log("Evento ignorado (no cambia estado Pro):", tipo);
    }

    return new Response(JSON.stringify({ ok: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    console.error("Error webhook RevenueCat:", err);
    return new Response(JSON.stringify({ ok: false, error: String(err) }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
});
