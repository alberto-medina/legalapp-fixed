// Worker "portero": recibe archivos desde la app, confirma contra Firestore
// (usando las MISMAS reglas de seguridad ya definidas) que quien pide subir o
// bajar un archivo realmente es el abogado o el cliente de ESE expediente, y
// recien ahi habla con Backblaze B2. La clave de Backblaze nunca se expone al
// navegador -- solo vive como secreto de este Worker.

function corsHeaders(origin) {
  return {
    "Access-Control-Allow-Origin": origin || "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
  };
}

function jsonResponse(data, status, origin) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders(origin), "Content-Type": "application/json" },
  });
}

// Pide el documento del expediente a Firestore CON el token del usuario que
// hizo la peticion. Si Firestore lo deja leer (porque nuestras reglas dicen
// que es el abogado o el cliente de ese expediente), esta funcion devuelve el
// documento; si no, tira un error -- asi reusamos la autorizacion que ya
// esta escrita una sola vez en firestore.rules, sin duplicarla aca.
async function leerExpedienteAutorizado(projectId, expedienteId, idToken) {
  const url = `https://firestore.googleapis.com/v1/projects/${projectId}/databases/(default)/documents/expedientes/${expedienteId}`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${idToken}` } });
  if (!res.ok) {
    throw new Error("No autorizado para este expediente");
  }
  return res.json();
}

async function b2Authorize(env) {
  const credenciales = btoa(`${env.B2_KEY_ID}:${env.B2_APP_KEY}`);
  const res = await fetch("https://api.backblazeb2.com/b2api/v3/b2_authorize_account", {
    headers: { Authorization: `Basic ${credenciales}` },
  });
  if (!res.ok) throw new Error("No se pudo autorizar con Backblaze");
  return res.json();
}

async function sha1Hex(buffer) {
  const hash = await crypto.subtle.digest("SHA-1", buffer);
  return Array.from(new Uint8Array(hash))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function sanitizarNombre(nombre) {
  return (nombre || "archivo").replace(/[^a-zA-Z0-9._-]/g, "_").slice(0, 150);
}

async function manejarSubida(request, env, origin) {
  const authHeader = request.headers.get("Authorization") || "";
  const idToken = authHeader.replace("Bearer ", "");
  if (!idToken) return jsonResponse({ error: "Falta autenticación" }, 401, origin);

  const formData = await request.formData();
  const file = formData.get("archivo");
  const expedienteId = formData.get("expedienteId");
  const subcarpeta = sanitizarNombre(formData.get("subcarpeta") || "");

  if (!file || !expedienteId) {
    return jsonResponse({ error: "Faltan datos (archivo o expedienteId)" }, 400, origin);
  }

  try {
    await leerExpedienteAutorizado(env.FIREBASE_PROJECT_ID, expedienteId, idToken);
  } catch (e) {
    return jsonResponse({ error: e.message }, 403, origin);
  }

  const nombreSeguro = sanitizarNombre(file.name);
  const path = subcarpeta
    ? `expedientes/${expedienteId}/${subcarpeta}/${Date.now()}_${nombreSeguro}`
    : `expedientes/${expedienteId}/${Date.now()}_${nombreSeguro}`;

  try {
    const auth = await b2Authorize(env);
    const uploadUrlRes = await fetch(`${auth.apiInfo.storageApi.apiUrl}/b2api/v3/b2_get_upload_url`, {
      method: "POST",
      headers: { Authorization: auth.authorizationToken, "Content-Type": "application/json" },
      body: JSON.stringify({ bucketId: env.B2_BUCKET_ID }),
    });
    if (!uploadUrlRes.ok) throw new Error("No se pudo preparar la subida");
    const uploadInfo = await uploadUrlRes.json();

    const fileBuffer = await file.arrayBuffer();
    const sha1 = await sha1Hex(fileBuffer);

    const subidaRes = await fetch(uploadInfo.uploadUrl, {
      method: "POST",
      headers: {
        Authorization: uploadInfo.authorizationToken,
        "X-Bz-File-Name": path
          .split("/")
          .map((seg) => encodeURIComponent(seg))
          .join("/"),
        "Content-Type": file.type || "b2/x-auto",
        "X-Bz-Content-Sha1": sha1,
      },
      body: fileBuffer,
    });

    if (!subidaRes.ok) {
      const txt = await subidaRes.text();
      throw new Error("Backblaze rechazó la subida: " + txt);
    }

    return jsonResponse({ path, nombreOriginal: file.name }, 200, origin);
  } catch (e) {
    return jsonResponse({ error: e.message }, 500, origin);
  }
}

async function manejarDescarga(request, env, origin) {
  const authHeader = request.headers.get("Authorization") || "";
  const idToken = authHeader.replace("Bearer ", "");
  if (!idToken) return jsonResponse({ error: "Falta autenticación" }, 401, origin);

  const { path } = await request.json();
  if (!path || !path.startsWith("expedientes/")) {
    return jsonResponse({ error: "Ruta inválida" }, 400, origin);
  }

  // expedientes/{expedienteId}/... -> sacamos el expedienteId del propio path
  const expedienteId = path.split("/")[1];

  try {
    await leerExpedienteAutorizado(env.FIREBASE_PROJECT_ID, expedienteId, idToken);
  } catch (e) {
    return jsonResponse({ error: e.message }, 403, origin);
  }

  try {
    const auth = await b2Authorize(env);
    const authDescargaRes = await fetch(
      `${auth.apiInfo.storageApi.apiUrl}/b2api/v3/b2_get_download_authorization`,
      {
        method: "POST",
        headers: { Authorization: auth.authorizationToken, "Content-Type": "application/json" },
        body: JSON.stringify({
          bucketId: env.B2_BUCKET_ID,
          fileNamePrefix: path,
          validDurationInSeconds: 3600,
        }),
      }
    );
    if (!authDescargaRes.ok) throw new Error("No se pudo autorizar la descarga");
    const authDescarga = await authDescargaRes.json();

    const urlArchivo =
      `${auth.apiInfo.storageApi.downloadUrl}/file/${env.B2_BUCKET_NAME}/` +
      path.split("/").map(encodeURIComponent).join("/") +
      `?Authorization=${authDescarga.authorizationToken}`;

    return jsonResponse({ url: urlArchivo }, 200, origin);
  } catch (e) {
    return jsonResponse({ error: e.message }, 500, origin);
  }
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin");
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders(origin) });
    }

    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/subir") {
      return manejarSubida(request, env, origin);
    }
    if (request.method === "POST" && url.pathname === "/descargar") {
      return manejarDescarga(request, env, origin);
    }
    return jsonResponse({ error: "Not found" }, 404, origin);
  },
};
