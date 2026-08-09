import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const MP_ACCESS_TOKEN = Deno.env.get("MP_ACCESS_TOKEN")!;
const MP_API_URL = "https://api.mercadopago.com/checkout/preferences";
const MP_PAYMENTS_URL = "https://api.mercadopago.com/v1/payments/search";
const MP_MERCHANT_ORDERS_URL = "https://api.mercadopago.com/merchant_orders/search";

const corsHeaders = {
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const body = await req.json();
    const action = String(body?.action || "").trim();

    if (!MP_ACCESS_TOKEN) {
      throw new Error("Falta MP_ACCESS_TOKEN en secrets");
    }

    if (action === "create_preference") {
      const title = String(body?.title || "Legal App").trim();
      const amount = Number(body?.amount || 0);
      const payerEmail = String(body?.payer_email || "").trim();
      const externalReference = String(body?.external_reference || "").trim();

      if (!amount || amount <= 0 || !externalReference) {
        return new Response(JSON.stringify({ ok: false, error: "Datos invalidos para create_preference" }), {
          status: 400,
          headers: corsHeaders,
        });
      }

      const mpRes = await fetch(MP_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${MP_ACCESS_TOKEN}`,
        },
        body: JSON.stringify({
          items: [{
            title,
            quantity: 1,
            unit_price: amount,
            currency_id: "ARS",
          }],
          payer: {
            email: payerEmail,
            name: payerEmail.includes("@") ? payerEmail.split("@")[0] : "Usuario",
          },
          external_reference: externalReference,
          back_urls: {
            success: "https://www.mercadopago.com.ar/",
            failure: "https://www.mercadopago.com.ar/",
            pending: "https://www.mercadopago.com.ar/",
          },
        }),
      });

      const data = await mpRes.json();
      if (!mpRes.ok) {
        return new Response(JSON.stringify({ ok: false, error: data }), {
          status: mpRes.status,
          headers: corsHeaders,
        });
      }

      return new Response(JSON.stringify({
        ok: true,
        init_point: data?.init_point || null,
        id: data?.id || null,
      }), { status: 200, headers: corsHeaders });
    }

    if (action === "verify_payment") {
      const externalReference = String(body?.external_reference || "").trim();
      const preferenceId = String(body?.preference_id || "").trim();

      if (!externalReference) {
        return new Response(JSON.stringify({ ok: false, error: "Falta external_reference" }), {
          status: 400,
          headers: corsHeaders,
        });
      }

      const paymentRes = await fetch(`${MP_PAYMENTS_URL}?external_reference=${encodeURIComponent(externalReference)}`, {
        headers: { "Authorization": `Bearer ${MP_ACCESS_TOKEN}` },
      });
      const paymentData = await paymentRes.json();

      if (paymentRes.ok) {
        const pagos = paymentData?.results || [];
        for (const pago of pagos) {
          if (pago?.status === "approved") {
            return new Response(JSON.stringify({
              ok: true,
              approved: true,
              payment_id: String(pago?.id || ""),
            }), { status: 200, headers: corsHeaders });
          }
        }
      }

      if (preferenceId) {
        const orderRes = await fetch(`${MP_MERCHANT_ORDERS_URL}?preference_id=${encodeURIComponent(preferenceId)}`, {
          headers: { "Authorization": `Bearer ${MP_ACCESS_TOKEN}` },
        });
        const orderData = await orderRes.json();

        if (orderRes.ok) {
          for (const order of orderData?.elements || []) {
            for (const pago of order?.payments || []) {
              if (pago?.status === "approved") {
                return new Response(JSON.stringify({
                  ok: true,
                  approved: true,
                  payment_id: String(pago?.id || ""),
                }), { status: 200, headers: corsHeaders });
              }
            }
          }
        }
      }

      return new Response(JSON.stringify({ ok: true, approved: false, payment_id: null }), {
        status: 200,
        headers: corsHeaders,
      });
    }

    return new Response(JSON.stringify({ ok: false, error: "Accion no soportada" }), {
      status: 400,
      headers: corsHeaders,
    });
  } catch (err) {
    return new Response(JSON.stringify({ ok: false, error: String(err) }), {
      status: 500,
      headers: corsHeaders,
    });
  }
});
