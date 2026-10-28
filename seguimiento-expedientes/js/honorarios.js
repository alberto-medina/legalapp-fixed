// Modulo compartido (abogado y cliente) para los honorarios de un expediente:
// el abogado carga items (concepto + monto + fecha), el cliente los puede ver,
// y cualquiera de los dos puede imprimir/descargar el recibo con el total.

const Honorarios = (() => {
  function docA(doc) {
    return { id: doc.id, ...doc.data() };
  }

  function fechaCorta(iso) {
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  function formatoMoneda(n) {
    return "$ " + Number(n || 0).toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  async function obtener(expedienteId) {
    try {
      const snap = await db
        .collection("honorarios")
        .where("expedienteId", "==", expedienteId)
        .orderBy("fecha", "asc")
        .get();
      return snap.docs.map(docA);
    } catch (e) {
      console.error(e);
      return [];
    }
  }

  async function crear(expediente, perfil, concepto, monto, fecha, ticketFile) {
    let ticketPath = null;
    let ticketNombre = null;
    if (ticketFile) {
      const subida = await Adjuntos.subirAlWorker(expediente.id, ticketFile, "honorarios");
      ticketPath = subida.path;
      ticketNombre = subida.nombreOriginal;
    }
    await db.collection("honorarios").add({
      expedienteId: expediente.id,
      abogadoId: expediente.abogadoId,
      clienteId: expediente.clienteId || null,
      concepto,
      monto: Number(monto) || 0,
      fecha,
      ticketPath,
      ticketNombre,
      createdAt: firebase.firestore.FieldValue.serverTimestamp(),
    });
  }

  async function eliminar(id) {
    await db.collection("honorarios").doc(id).delete();
  }

  // expediente: objeto del expediente. perfil: usuario logueado.
  // esAbogado: true muestra el formulario de carga y los botones de borrar.
  async function renderTab(panel, expediente, perfil, esAbogado) {
    panel.innerHTML = '<div class="vacio">Cargando...</div>';
    const items = await obtener(expediente.id);
    const total = items.reduce((acc, it) => acc + (Number(it.monto) || 0), 0);
    const hoy = new Date().toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" });

    panel.innerHTML = `
      <div id="recibo-${expediente.id}" class="recibo">
        <div class="recibo-header">
          <div>
            <div class="recibo-titulo">Detalle de honorarios</div>
            <div class="recibo-sub">${expediente.numero || "EXP-S/N"} — ${expediente.titulo}</div>
            ${expediente.clienteNombre ? `<div class="recibo-sub">Cliente: ${expediente.clienteNombre}</div>` : ""}
          </div>
          <div class="recibo-fecha">Emitido: ${hoy}</div>
        </div>

        ${
          items.length === 0
            ? '<div class="vacio">Todavía no se cargó ningún honorario.</div>'
            : `<table class="tabla">
                <tr><th>Fecha</th><th>Concepto</th><th>Monto</th><th>Ticket</th><th class="no-imprimir"></th></tr>
                ${items
                  .map(
                    (it) => `<tr>
                      <td>${fechaCorta(it.fecha)}</td>
                      <td>${it.concepto}</td>
                      <td>${formatoMoneda(it.monto)}</td>
                      <td>${it.ticketPath ? `<a href="#" class="ticket-link" data-path="${it.ticketPath}">📎 Ver</a>` : "—"}</td>
                      <td class="no-imprimir">${esAbogado ? `<button class="btn-chico" data-borrar="${it.id}">Borrar</button>` : ""}</td>
                    </tr>`
                  )
                  .join("")}
              </table>`
        }

        <div class="recibo-total">Total: ${formatoMoneda(total)}</div>
      </div>

      <div class="form-inline no-imprimir" style="margin-top:14px;">
        <button class="btn-chico" id="btn-imprimir-${expediente.id}">🖨️ Imprimir / descargar recibo</button>
      </div>

      ${
        esAbogado
          ? `
      <div class="subtitulo-form no-imprimir">Agregar honorario</div>
      <form class="form-inline no-imprimir" data-rol="honorario">
        <div class="campo chico">
          <label>Fecha</label>
          <input type="date" name="fecha" required>
        </div>
        <div class="campo">
          <label>Concepto</label>
          <input type="text" name="concepto" placeholder="Ej: Honorarios por inicio de sucesorio" required>
        </div>
        <div class="campo chico">
          <label>Monto</label>
          <input type="number" name="monto" min="0" step="0.01" placeholder="0.00" required>
        </div>
        <div class="campo">
          <label>Ticket / comprobante (opcional)</label>
          <input type="file" name="ticket">
        </div>
        <button type="submit" class="btn-teal">Agregar</button>
      </form>`
          : ""
      }
    `;

    const btnImprimir = panel.querySelector(`#btn-imprimir-${expediente.id}`);
    if (btnImprimir) {
      btnImprimir.addEventListener("click", () => window.print());
    }

    panel.querySelectorAll(".ticket-link").forEach((link) => {
      link.addEventListener("click", async (ev) => {
        ev.preventDefault();
        const original = link.textContent;
        link.textContent = "Abriendo...";
        try {
          const url = await Adjuntos.obtenerUrlDescarga(link.getAttribute("data-path"));
          window.open(url, "_blank", "noopener");
        } catch (e) {
          alert("No se pudo abrir el ticket: " + e.message);
        } finally {
          link.textContent = original;
        }
      });
    });

    if (esAbogado) {
      panel.querySelectorAll("[data-borrar]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          if (!confirm("¿Borrar este honorario?")) return;
          await eliminar(btn.getAttribute("data-borrar"));
          renderTab(panel, expediente, perfil, esAbogado);
        });
      });

      const form = panel.querySelector('form[data-rol="honorario"]');
      if (form) {
        form.addEventListener("submit", async (ev) => {
          ev.preventDefault();
          const f = new FormData(ev.target);
          const ticketFile = ev.target.querySelector('input[name="ticket"]').files[0] || null;
          const btn = ev.target.querySelector('button[type="submit"]');
          const original = btn.textContent;
          btn.disabled = true;
          btn.textContent = ticketFile ? "Subiendo..." : "Agregando...";
          try {
            await crear(expediente, perfil, f.get("concepto"), f.get("monto"), f.get("fecha"), ticketFile);
            renderTab(panel, expediente, perfil, esAbogado);
          } catch (e) {
            alert("No se pudo agregar el honorario: " + e.message);
            btn.disabled = false;
            btn.textContent = original;
          }
        });
      }
    }
  }

  return { renderTab };
})();
