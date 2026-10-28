// Panel del cliente: solo lectura de sus propios expedientes, actuaciones y
// fechas (audiencias) que el abogado marcó como visibles para él.

const Cliente = (() => {
  let perfilActual = null;
  let expedientesCache = [];

  function fechaCorta(iso) {
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  function fechaLarga(timestamp) {
    if (!timestamp || !timestamp.toDate) return "—";
    return timestamp.toDate().toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  function chipEstado(estado) {
    const e = (estado || "").toLowerCase();
    if (e.includes("final")) return "chip-estado finalizado";
    if (e.includes("archiv")) return "chip-estado archivado";
    return "chip-estado";
  }

  function docA(doc) {
    return { id: doc.id, ...doc.data() };
  }

  async function obtenerExpedientes() {
    try {
      const snap = await db
        .collection("expedientes")
        .where("clienteId", "==", perfilActual.id)
        .orderBy("createdAt", "desc")
        .get();
      return snap.docs.map(docA);
    } catch (e) {
      console.error(e);
      return [];
    }
  }

  async function obtenerActuaciones(expedienteId) {
    try {
      const snap = await db
        .collection("actuaciones")
        .where("expedienteId", "==", expedienteId)
        .orderBy("fecha", "desc")
        .get();
      return snap.docs.map(docA);
    } catch (e) {
      console.error(e);
      return [];
    }
  }

  async function obtenerProximasFechas() {
    const hoy = new Date().toISOString().slice(0, 10);
    try {
      const snap = await db
        .collection("alertas")
        .where("clienteId", "==", perfilActual.id)
        .where("paraRol", "==", "cliente")
        .orderBy("fecha", "asc")
        .get();
      return snap.docs.map(docA).filter((a) => a.fecha >= hoy);
    } catch (e) {
      console.error(e);
      return [];
    }
  }

  async function vistaInicio(contenedor) {
    const [expedientes, proximasFechas] = await Promise.all([obtenerExpedientes(), obtenerProximasFechas()]);
    expedientesCache = expedientes;

    contenedor.innerHTML = `
      <div class="encabezado-pagina">
        <h1>Mis expedientes</h1>
        <p>Seguimiento del estado de tus casos.</p>
      </div>
      ${
        proximasFechas.length > 0
          ? `<div class="panel">
              <h2>Próximas fechas</h2>
              <table class="tabla">
                <tr><th>Expediente</th><th>Detalle</th><th>Fecha</th></tr>
                ${proximasFechas
                  .map(
                    (a) => `<tr>
                      <td>${a.expedienteTitulo}</td>
                      <td>${a.mensaje}</td>
                      <td>${fechaCorta(a.fecha)}</td>
                    </tr>`
                  )
                  .join("")}
              </table>
            </div>`
          : ""
      }
      <div class="lista-expedientes">
        ${
          expedientes.length === 0
            ? '<div class="vacio">Todavía no tenés expedientes asignados.</div>'
            : expedientes
                .map(
                  (e) => `
          <div class="expediente-item" data-id="${e.id}">
            <div class="expediente-cab" data-toggle="${e.id}">
              <div class="exp-info">
                <div class="exp-numero">${e.numero || "EXP-S/N"}</div>
                <div class="exp-caratula">${e.titulo}</div>
                ${e.objeto ? `<div class="exp-objeto">${e.objeto}</div>` : ""}
              </div>
              <div class="exp-cab-der">
                <span class="${chipEstado(e.estado)}">${e.estado}</span>
                <button class="btn-chico">Ver</button>
              </div>
            </div>
            ${
              e.ultimaActuacionFecha
                ? `<div class="exp-ultimo-mov"><span class="bell">🔔</span><span class="fecha">${fechaCorta(e.ultimaActuacionFecha)}</span> — última actuación: ${e.ultimaActuacionTipo}</div>`
                : ""
            }
            <div class="expediente-detalle" id="detalle-${e.id}"></div>
          </div>`
                )
                .join("")
        }
      </div>
    `;

    contenedor.querySelectorAll("[data-toggle]").forEach((el) => {
      el.addEventListener("click", () => abrirExpediente(el.getAttribute("data-toggle")));
    });
  }

  function renderStepper(e) {
    if (!e.etapas || e.etapas.length === 0) return "";
    const actual = e.etapaActualIndex ?? 0;
    return `
      <div class="stepper-wrap">
        <div class="stepper-titulo">Etapas del proceso</div>
        <div class="stepper">
          ${e.etapas
            .map(
              (et, i) => `
            <div class="stepper-item ${i < actual ? "completado" : i === actual ? "activo" : ""}">
              <div class="stepper-linea"></div>
              <div class="stepper-circulo">${i < actual ? "✓" : i + 1}</div>
              <div class="stepper-label">${et}</div>
            </div>`
            )
            .join("")}
        </div>
      </div>
    `;
  }

  function renderFicha(panel, e) {
    panel.innerHTML = `
      ${renderStepper(e)}
      <div class="ficha-grid">
        <div class="ficha-campo"><div class="label">N° de expediente</div><div class="val">${e.numero || "—"}</div></div>
        <div class="ficha-campo"><div class="label">Estado</div><div class="val">${e.estado}</div></div>
        <div class="ficha-campo"><div class="label">Fecha de inicio</div><div class="val">${fechaLarga(e.createdAt)}</div></div>
        <div class="ficha-campo"><div class="label">Objeto</div><div class="val ${e.objeto ? "" : "vacio-campo"}">${e.objeto || "Sin especificar"}</div></div>
      </div>
    `;
  }

  async function renderActuacionesTab(panel, expedienteId) {
    panel.innerHTML = '<div class="vacio">Cargando...</div>';
    const actuaciones = await obtenerActuaciones(expedienteId);
    panel.innerHTML = `
      <div class="timeline">
        ${
          actuaciones.length === 0
            ? '<div class="vacio">Tu abogado todavía no cargó actuaciones en este expediente.</div>'
            : actuaciones
                .map(
                  (a) => `
          <div class="timeline-item">
            <div class="timeline-fecha">${fechaCorta(a.fecha)}</div>
            <div class="timeline-cuerpo">
              <div class="tipo">${a.tipo}</div>
              ${a.descripcion ? `<div class="desc">${a.descripcion}</div>` : ""}
            </div>
          </div>`
                )
                .join("")
        }
      </div>
    `;
  }

  async function abrirExpediente(expedienteId) {
    const detalle = document.getElementById(`detalle-${expedienteId}`);
    const abierto = detalle.classList.contains("abierto");
    document.querySelectorAll(".expediente-detalle.abierto").forEach((d) => d.classList.remove("abierto"));
    if (abierto) return;

    detalle.classList.add("abierto");
    const expediente = expedientesCache.find((x) => x.id === expedienteId) || {};

    detalle.innerHTML = `
      <div class="tabs-expediente">
        <button class="tab-btn activo" data-tab="ficha">Ficha</button>
        <button class="tab-btn" data-tab="actuaciones">Actuaciones</button>
        <button class="tab-btn" data-tab="documentos">Documentos</button>
        <button class="tab-btn" data-tab="honorarios">Honorarios</button>
      </div>
      <div class="tab-panel"></div>
    `;

    const panel = detalle.querySelector(".tab-panel");

    function activarTab(tab) {
      detalle.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("activo", b.getAttribute("data-tab") === tab));
      if (tab === "ficha") renderFicha(panel, expediente);
      if (tab === "actuaciones") renderActuacionesTab(panel, expedienteId);
      if (tab === "documentos") Adjuntos.renderTab(panel, expediente, perfilActual, "cliente");
      if (tab === "honorarios") Honorarios.renderTab(panel, expediente, perfilActual, false);
    }

    detalle.querySelectorAll(".tab-btn").forEach((b) => {
      b.addEventListener("click", () => activarTab(b.getAttribute("data-tab")));
    });

    activarTab("ficha");
  }

  async function render(perfil, _vista, contenedor) {
    perfilActual = perfil;
    return vistaInicio(contenedor);
  }

  const menu = [{ id: "inicio", label: "Mis expedientes" }];

  return { render, menu };
})();
