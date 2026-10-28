// Modulo compartido (abogado y cliente) para subir y listar documentos de un
// expediente: comprobantes del abogado, fotos o archivos que manda el cliente.
// Los archivos NO van a Firebase Storage (pide plan pago) -- van a Backblaze
// B2 a traves de un Worker de Cloudflare que valida contra Firestore quien
// puede subir/bajar cada archivo. Firestore solo guarda la ruta y quien lo
// subio; el Worker genera un link de descarga temporal cada vez que hace falta.

const ARCHIVOS_WORKER_URL = "https://seguimiento-expedientes-archivos.beto77am.workers.dev";

const Adjuntos = (() => {
  function docA(doc) {
    return { id: doc.id, ...doc.data() };
  }

  function fechaCorta(timestamp) {
    if (!timestamp || !timestamp.toDate) return "recién";
    return timestamp.toDate().toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  function iconoPara(tipo) {
    if (!tipo) return "📄";
    if (tipo.startsWith("image/")) return "🖼️";
    if (tipo === "application/pdf") return "📕";
    return "📄";
  }

  async function obtener(expedienteId) {
    try {
      const snap = await db
        .collection("adjuntos")
        .where("expedienteId", "==", expedienteId)
        .orderBy("createdAt", "desc")
        .get();
      return snap.docs.map(docA);
    } catch (e) {
      console.error(e);
      return [];
    }
  }

  async function subirAlWorker(expedienteId, file, subcarpeta) {
    const idToken = await authClient.currentUser.getIdToken();
    const fd = new FormData();
    fd.append("archivo", file);
    fd.append("expedienteId", expedienteId);
    if (subcarpeta) fd.append("subcarpeta", subcarpeta);

    const res = await fetch(`${ARCHIVOS_WORKER_URL}/subir`, {
      method: "POST",
      headers: { Authorization: `Bearer ${idToken}` },
      body: fd,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "No se pudo subir el archivo");
    return data; // { path, nombreOriginal }
  }

  async function obtenerUrlDescarga(path) {
    const idToken = await authClient.currentUser.getIdToken();
    const res = await fetch(`${ARCHIVOS_WORKER_URL}/descargar`, {
      method: "POST",
      headers: { Authorization: `Bearer ${idToken}`, "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "No se pudo abrir el archivo");
    return data.url;
  }

  async function subir(expediente, perfil, rolSubidor, file) {
    const { path, nombreOriginal } = await subirAlWorker(expediente.id, file);
    await db.collection("adjuntos").add({
      expedienteId: expediente.id,
      abogadoId: expediente.abogadoId,
      clienteId: expediente.clienteId || null,
      subidoPor: perfil.id,
      subidoPorNombre: perfil.nombre,
      subidoPorRol: rolSubidor,
      nombreArchivo: nombreOriginal,
      storagePath: path,
      tipo: file.type || "",
      createdAt: firebase.firestore.FieldValue.serverTimestamp(),
    });
  }

  async function abrirArchivo(path, link) {
    const original = link.textContent;
    link.textContent = "Abriendo...";
    try {
      const url = await obtenerUrlDescarga(path);
      window.open(url, "_blank", "noopener");
    } catch (e) {
      alert("No se pudo abrir el archivo: " + e.message);
    } finally {
      link.textContent = original;
    }
  }

  // expediente: objeto del expediente (necesita .id, .abogadoId, .clienteId).
  // perfil: perfil del usuario logueado. rolSubidor: "abogado" o "cliente".
  async function renderTab(panel, expediente, perfil, rolSubidor) {
    panel.innerHTML = '<div class="vacio">Cargando...</div>';
    const archivos = await obtener(expediente.id);

    panel.innerHTML = `
      <div class="lista-adjuntos">
        ${
          archivos.length === 0
            ? '<div class="vacio">Todavía no se subió ningún archivo.</div>'
            : archivos
                .map(
                  (a) => `
          <a class="adjunto-item" href="#" data-path="${a.storagePath}">
            <span class="adjunto-icono">${iconoPara(a.tipo)}</span>
            <span class="adjunto-info">
              <span class="adjunto-nombre">${a.nombreArchivo}</span>
              <span class="adjunto-meta">Subido por ${a.subidoPorNombre} (${a.subidoPorRol}) · ${fechaCorta(a.createdAt)}</span>
            </span>
          </a>`
                )
                .join("")
        }
      </div>
      <form class="form-inline" data-rol="adjunto">
        <div class="campo">
          <label>Subir archivo (PDF, foto, documento)</label>
          <input type="file" name="archivo" required>
        </div>
        <button type="submit" class="btn-teal">Subir</button>
      </form>
    `;

    panel.querySelectorAll(".adjunto-item[data-path]").forEach((a) => {
      a.addEventListener("click", (ev) => {
        ev.preventDefault();
        abrirArchivo(a.getAttribute("data-path"), a.querySelector(".adjunto-nombre"));
      });
    });

    panel.querySelector('form[data-rol="adjunto"]').addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const file = ev.target.querySelector('input[type="file"]').files[0];
      if (!file) return;
      const btn = ev.target.querySelector("button");
      const original = btn.textContent;
      btn.disabled = true;
      btn.textContent = "Subiendo...";
      try {
        await subir(expediente, perfil, rolSubidor, file);
        renderTab(panel, expediente, perfil, rolSubidor);
      } catch (e) {
        alert("No se pudo subir el archivo: " + e.message);
        btn.disabled = false;
        btn.textContent = original;
      }
    });
  }

  return { renderTab, subirAlWorker, obtenerUrlDescarga };
})();
