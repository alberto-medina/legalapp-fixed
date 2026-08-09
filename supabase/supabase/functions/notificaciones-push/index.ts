import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SUPABASE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const FIREBASE_PROJECT_ID = Deno.env.get("FIREBASE_PROJECT_ID")!;
const FIREBASE_CLIENT_EMAIL = Deno.env.get("FIREBASE_CLIENT_EMAIL")!;
const FIREBASE_PRIVATE_KEY = Deno.env.get("FIREBASE_PRIVATE_KEY")!;

async function getAccessToken(): Promise<string> {
  const now = Math.floor(Date.now() / 1000);

  const header = { alg: "RS256", typ: "JWT" };
  const payload = {
    iss: FIREBASE_CLIENT_EMAIL,
    scope: "https://www.googleapis.com/auth/firebase.messaging",
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
  };

  const encode = (obj: object) =>
    btoa(JSON.stringify(obj))
      .replace(/=/g, "")
      .replace(/\+/g, "-")
      .replace(/\//g, "_");

  const headerB64 = encode(header);
  const payloadB64 = encode(payload);
  const signingInput = `${headerB64}.${payloadB64}`;

  const pemKey = FIREBASE_PRIVATE_KEY.replace(/\\n/g, "\n");
  const pemBody = pemKey
    .replace("-----BEGIN PRIVATE KEY-----", "")
    .replace("-----END PRIVATE KEY-----", "")
    .replace(/\s/g, "");

  const binaryKey = Uint8Array.from(atob(pemBody), (c) => c.charCodeAt(0));

  const cryptoKey = await crypto.subtle.importKey(
    "pkcs8",
    binaryKey,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"],
  );

  const signature = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    cryptoKey,
    new TextEncoder().encode(signingInput),
  );

  const sigB64 = btoa(String.fromCharCode(...new Uint8Array(signature)))
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");

  const jwt = `${signingInput}.${sigB64}`;

  const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body:
      `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${jwt}`,
  });

  const tokenData = await tokenRes.json();
  if (!tokenRes.ok || !tokenData?.access_token) {
    console.error("OAuth token error:", JSON.stringify(tokenData));
    throw new Error(`No se pudo obtener access_token de Google OAuth (${tokenRes.status})`);
  }
  return tokenData.access_token;
}

async function enviarNotificacion(
  fcmToken: string,
  titulo: string,
  cuerpo: string,
  channelId: string,
  data: Record<string, string> = {},
  imageUrl = "",
): Promise<boolean> {
  try {
    const accessToken = await getAccessToken();

    const androidNotification: Record<string, unknown> = {
      channel_id: channelId,
      default_sound: true,
      color: "#4B2FA7",
    };

    if (imageUrl) {
      androidNotification.image = imageUrl;
    }

    const res = await fetch(
      `https://fcm.googleapis.com/v1/projects/${FIREBASE_PROJECT_ID}/messages:send`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: {
            token: fcmToken,
            notification: { title: titulo, body: cuerpo },
            android: {
              priority: "high",
              notification: androidNotification,
            },
            data,
          },
        }),
      },
    );

    const result = await res.json();
    console.log("FCM result:", JSON.stringify(result));
    return res.ok;
  } catch (e) {
    console.error("Error enviando notificacion:", e);
    return false;
  }
}

async function getFcmToken(
  supabase: ReturnType<typeof createClient>,
  uid: string,
): Promise<string | null> {
  const { data } = await supabase
    .from("usuarios")
    .select("fcm_token")
    .eq("uid", uid)
    .single();
  return data?.fcm_token || null;
}

async function getUsuarioBasico(
  supabase: ReturnType<typeof createClient>,
  uid: string,
): Promise<{ nombre?: string; email?: string; foto_url?: string } | null> {
  const { data } = await supabase
    .from("usuarios")
    .select("nombre,email,foto_url")
    .eq("uid", uid)
    .single();
  return data || null;
}

serve(async (req) => {
  try {
    if (!FIREBASE_PROJECT_ID || !FIREBASE_CLIENT_EMAIL || !FIREBASE_PRIVATE_KEY) {
      throw new Error("Faltan FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL o FIREBASE_PRIVATE_KEY en secrets");
    }

    const body = await req.json();
    const { tipo, data } = body;

    console.log("Notificacion solicitada:", tipo, JSON.stringify(data));

    if (tipo === "healthcheck") {
      return new Response(JSON.stringify({ ok: true, healthcheck: true }), {
        headers: { "Content-Type": "application/json" },
        status: 200,
      });
    }

    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

    switch (tipo) {
      case "consulta_pagada": {
        const token = await getFcmToken(supabase, data.abogado_uid);
        if (token) {
          await enviarNotificacion(
            token,
            "Nueva consulta",
            `Tienes una nueva consulta de ${data.cliente_email} - ${data.tipo_servicio}`,
            "consulta_channel",
            {
              consulta_id: String(data.consulta_id || ""),
              tipo: "consulta_pagada",
            },
          );
        }
        break;
      }

      case "consulta_aceptada": {
        const token = await getFcmToken(supabase, data.cliente_uid);
        if (token) {
          await enviarNotificacion(
            token,
            "Consulta aceptada",
            `Tu abogado acepto la consulta. Podes iniciar el ${data.tipo_servicio}.`,
            "consulta_channel",
            {
              consulta_id: String(data.consulta_id || ""),
              tipo: "consulta_aceptada",
            },
          );
        }
        break;
      }

      case "nuevo_mensaje": {
        const token = await getFcmToken(supabase, data.receptor_uid);
        if (token) {
          const emisor = (await getUsuarioBasico(supabase, data.emisor_uid)) || {};
          const titulo =
            String(data.emisor_nombre || emisor.nombre || emisor.email || "Nuevo mensaje");
          const cuerpo =
            String(data.preview || "Tienes un nuevo mensaje");

          await enviarNotificacion(
            token,
            titulo,
            cuerpo,
            "chat_channel",
            {
              consulta_id: String(data.consulta_id || ""),
              tipo: "nuevo_mensaje",
              emisor_uid: String(data.emisor_uid || ""),
              emisor_nombre: titulo,
              preview: cuerpo,
            },
            String(emisor.foto_url || ""),
          );
        }
        break;
      }

      case "consulta_finalizada": {
        const token = await getFcmToken(supabase, data.cliente_uid);
        if (token) {
          await enviarNotificacion(
            token,
            "Consulta finalizada",
            "Tu consulta ha finalizado. Podes dejar una resena.",
            "consulta_channel",
            {
              consulta_id: String(data.consulta_id || ""),
              tipo: "consulta_finalizada",
            },
          );
        }
        break;
      }

      case "videollamada": {
        const token = await getFcmToken(supabase, data.cliente_uid);
        if (token) {
          await enviarNotificacion(
            token,
            "Videollamada",
            "Tu abogado inicio la videollamada. Ingresa ahora.",
            "consulta_channel",
            {
              consulta_id: String(data.consulta_id || ""),
              tipo: "videollamada",
            },
          );
        }
        break;
      }

      case "retiro_pagado": {
        const token = await getFcmToken(supabase, data.abogado_uid);
        if (token) {
          await enviarNotificacion(
            token,
            "Retiro transferido",
            `Tu retiro de $${data.monto_neto || "0"} fue marcado como pagado.`,
            "consulta_channel",
            {
              tipo: "retiro_pagado",
              monto_neto: String(data.monto_neto || "0"),
            },
          );
        }
        break;
      }

      default:
        console.log("Tipo de notificacion desconocido:", tipo);
    }

    return new Response(JSON.stringify({ ok: true }), {
      headers: { "Content-Type": "application/json" },
      status: 200,
    });
  } catch (err) {
    console.error("Error:", err);
    return new Response(JSON.stringify({ ok: false, error: String(err) }), {
      headers: { "Content-Type": "application/json" },
      status: 500,
    });
  }
});
