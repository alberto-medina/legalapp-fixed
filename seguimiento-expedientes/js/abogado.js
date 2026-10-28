// Panel del abogado: resumen, expedientes (con carga de actuaciones), agenda y alertas.
// Datos en Firestore. Para evitar N+1 lecturas (Firestore no tiene joins), cada
// actuacion/alerta guarda una copia chica de datos del expediente (titulo,
// abogadoId, clienteId) al momento de crearse -- patron normal en NoSQL.

const Abogado = (() => {
  let perfilActual = null;

  function fechaCorta(iso) {
    const d = new Date(iso + "T00:00:00");
    return d.toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  const ETIQUETA_TIPO = {
    general: "General",
    audiencia: "Audiencia",
    plazo_escrito: "Plazo de escrito",
  };

  // Calcula la urgencia en base a la fecha, sin depender de nada "corriendo" en
  // segundo plano: cada vez que se abre la Agenda o el Inicio, se recalcula sola
  // a partir de la fecha de hoy -- asi la alerta se va poniendo mas urgente a
  // medida que se acerca el vencimiento, sin que el abogado tenga que hacer nada.
  function calcularUrgencia(fechaIso) {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    const fecha = new Date(fechaIso + "T00:00:00");
    const dias = Math.round((fecha - hoy) / 86400000);

    if (dias < 0) return { label: "Vencido", clase: "badge danger" };
    if (dias <= 3) return { label: "Urgente", clase: "badge danger" };
    if (dias <= 7) return { label: "Próximo", clase: "badge" };
    return { label: "Programado", clase: "badge gris" };
  }

  function docA(doc) {
    return { id: doc.id, ...doc.data() };
  }

  function fechaLarga(timestamp) {
    if (!timestamp || !timestamp.toDate) return "—";
    return timestamp.toDate().toLocaleDateString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  // Numero de expediente cosmetico (no es un numero judicial real, solo para
  // identificar el caso de un vistazo, como en el SED del Poder Judicial).
  function generarNumero() {
    const d = new Date();
    const yy = String(d.getFullYear()).slice(-2);
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const rand = Math.random().toString(36).slice(2, 6).toUpperCase();
    return `EXP-${yy}${mm}-${rand}`;
  }

  // Para la linea de tiempo: pasado = sin clase (punto teal por defecto),
  // hoy = resaltado, futuro = amber, futuro-cercano (<=3 dias) = rojo.
  function claseLinea(fecha) {
    const hoy = new Date().toISOString().slice(0, 10);
    if (fecha === hoy) return "hoy";
    if (fecha > hoy) {
      const dias = Math.round((new Date(fecha + "T00:00:00") - new Date(hoy + "T00:00:00")) / 86400000);
      return dias <= 3 ? "urgente" : "futuro";
    }
    return "";
  }

  function chipEstado(estado) {
    const e = (estado || "").toLowerCase();
    if (e.includes("tramite") || e.includes("trámite")) return "chip-estado";
    if (e.includes("final")) return "chip-estado finalizado";
    if (e.includes("archiv")) return "chip-estado archivado";
    return "chip-estado";
  }

  // Cache en memoria de la ultima lista de expedientes cargada, para poder
  // armar la ficha sin pedirle el documento de nuevo a Firestore.
  let expedientesCache = [];

  async function obtenerExpedientes() {
    try {
      const snap = await db
        .collection("expedientes")
        .where("abogadoId", "==", perfilActual.id)
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

  async function obtenerAlertasDeExpediente(expedienteId) {
    try {
      const snap = await db
        .collection("alertas")
        .where("expedienteId", "==", expedienteId)
        .orderBy("fecha", "asc")
        .get();
      return snap.docs.map(docA);
    } catch (e) {
      console.error(e);
      return [];
    }
  }

  async function obtenerProximasActuaciones() {
    const hoy = new Date().toISOString().slice(0, 10);
    try {
      const snap = await db
        .collection("actuaciones")
        .where("abogadoId", "==", perfilActual.id)
        .where("fecha", ">=", hoy)
        .orderBy("fecha", "asc")
        .limit(10)
        .get();
      return snap.docs.map(docA);
    } catch (e) {
      console.error(e);
      return [];
    }
  }

  async function obtenerAlertasPendientes() {
    try {
      const snap = await db
        .collection("alertas")
        .where("abogadoId", "==", perfilActual.id)
        .where("leida", "==", false)
        .orderBy("fecha", "asc")
        .get();
      return snap.docs.map(docA);
    } catch (e) {
      console.error(e);
      return [];
    }
  }

  // Agenda completa: TODAS las alertas (leidas o no) de los expedientes del
  // abogado -- audiencias y plazos de escritos, ordenadas por fecha.
  async function obtenerAgendaCompleta() {
    try {
      const snap = await db
        .collection("alertas")
        .where("abogadoId", "==", perfilActual.id)
        .orderBy("fecha", "asc")
        .get();
      return snap.docs.map(docA);
    } catch (e) {
      console.error(e);
      return [];
    }
  }

  async function obtenerClientes() {
    try {
      const snap = await db.collection("perfiles").where("rol", "==", "cliente").orderBy("nombre").get();
      return snap.docs.map(docA);
    } catch (e) {
      console.error(e);
      return [];
    }
  }

  // Crea un usuario de Firebase Auth nuevo (el cliente) sin cerrar la sesion
  // del abogado: usa una segunda instancia de Firebase, aislada, solo para
  // este alta, y la descarta apenas termina.
  async function crearClienteNuevo(nombre, email, password) {
    const appSecundaria = firebase.initializeApp(firebaseConfig, "alta-cliente-" + Date.now());
    try {
      const cred = await appSecundaria.auth().createUserWithEmailAndPassword(email, password);
      const uid = cred.user.uid;
      await appSecundaria.auth().signOut();
      await db.collection("perfiles").doc(uid).set({ email, nombre, rol: "cliente" });
      return { id: uid, email, nombre, rol: "cliente" };
    } finally {
      await appSecundaria.delete();
    }
  }

  async function crearExpediente(titulo, clienteId, objeto, etapasTexto) {
    let clienteNombre = null;
    let clienteEmail = null;
    if (clienteId) {
      const clienteDoc = await db.collection("perfiles").doc(clienteId).get();
      if (clienteDoc.exists) {
        clienteNombre = clienteDoc.data().nombre;
        clienteEmail = clienteDoc.data().email;
      }
    }
    const etapas = (etapasTexto || "")
      .split(",")
      .map((e) => e.trim())
      .filter((e) => e.length > 0);

    await db.collection("expedientes").add({
      titulo,
      numero: generarNumero(),
      objeto: objeto || "",
      clienteId: clienteId || null,
      clienteNombre,
      clienteEmail,
      abogadoId: perfilActual.id,
      estado: "en trámite",
      etapas,
      etapaActualIndex: etapas.length > 0 ? 0 : -1,
      createdAt: firebase.firestore.FieldValue.serverTimestamp(),
    });
  }

  async function avanzarEtapa(expedienteId, nuevoIndex) {
    await db.collection("expedientes").doc(expedienteId).update({ etapaActualIndex: nuevoIndex });
  }

  async function guardarEtapas(expedienteId, etapasTexto) {
    const etapas = (etapasTexto || "")
      .split(",")
      .map((et) => et.trim())
      .filter((et) => et.length > 0);
    await db.collection("expedientes").doc(expedienteId).update({ etapas, etapaActualIndex: 0 });
    return etapas;
  }

  async function crearActuacion(expedienteId, tipo, fecha, descripcion) {
    const expDoc = await db.collection("expedientes").doc(expedienteId).get();
    const expediente = expDoc.data() || {};
    await db.collection("actuaciones").add({
      expedienteId,
      expedienteTitulo: expediente.titulo || "",
      abogadoId: perfilActual.id,
      tipo,
      fecha,
      descripcion: descripcion || "",
      createdBy: perfilActual.id,
      createdAt: firebase.firestore.FieldValue.serverTimestamp(),
    });
    // Se guarda una copia del ultimo movimiento en el propio expediente para
    // poder mostrarlo en la lista sin tener que leer todas las actuaciones.
    await db.collection("expedientes").doc(expedienteId).update({
      ultimaActuacionFecha: fecha,
      ultimaActuacionTipo: tipo,
    });
  }

  async function crearAlerta(expedienteId, tipo, fecha, mensaje, paraRol) {
    const expDoc = await db.collection("expedientes").doc(expedienteId).get();
    const expediente = expDoc.data() || {};
    await db.collection("alertas").add({
      expedienteId,
      expedienteTitulo: expediente.titulo || "",
      abogadoId: perfilActual.id,
      clienteId: expediente.clienteId || null,
      tipo,
      fecha,
      mensaje,
      paraRol,
      leida: false,
      createdAt: firebase.firestore.FieldValue.serverTimestamp(),
    });
  }

  async function marcarAlertaLeida(alertaId) {
    await db.collection("alertas").doc(alertaId).update({ leida: true });
  }

  // ---------------- vistas ----------------

  async function vistaInicio(contenedor) {
    const [expedientes, proximas, alertas] = await Promise.all([
      obtenerExpedientes(),
      obtenerProximasActuaciones(),
      obtenerAlertasPendientes(),
    ]);
    const enTramite = expedientes.filter((e) => e.estado === "en trámite").length;

    contenedor.innerHTML = `
      <div class="encabezado-pagina">
        <h1>Bienvenido, Dr./Dra.</h1>
        <p>Panel de seguimiento y gestión de casos.</p>
      </div>
      <div class="tiles">
        <div class="tile"><div class="label">Expedientes</div><div class="val">${expedientes.length}</div></div>
        <div class="tile"><div class="label">Alertas pendientes</div><div class="val">${alertas.length}</div></div>
        <div class="tile"><div class="label">En trámite</div><div class="val">${enTramite}</div></div>
        <div class="tile"><div class="label">Próximas actuaciones</div><div class="val">${proximas.length}</div></div>
      </div>
      <div class="panel">
        <h2>Próximas actuaciones</h2>
        ${
          proximas.length === 0
            ? '<div class="vacio">No hay actuaciones próximas cargadas.</div>'
            : `<table class="tabla">
                <tr><th>Expediente</th><th>Actuación</th><th>Fecha</th></tr>
                ${proximas
                  .map(
                    (a) => `<tr>
                      <td>${a.expedienteTitulo}</td>
                      <td><span class="badge">${a.tipo}</span></td>
                      <td>${fechaCorta(a.fecha)}</td>
                    </tr>`
                  )
                  .join("")}
              </table>`
        }
      </div>
    `;
  }

  async function vistaExpedientes(contenedor) {
    const expedientes = await obtenerExpedientes();
    expedientesCache = expedientes;

    contenedor.innerHTML = `
      <div class="encabezado-pagina">
        <h1>Mis expedientes</h1>
        <p>Expandí un expediente para ver la ficha, las actuaciones y la agenda.</p>
      </div>
      <div class="lista-expedientes">
        ${
          expedientes.length === 0
            ? '<div class="vacio">Todavía no cargaste ningún expediente.</div>'
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
    if (!e.etapas || e.etapas.length === 0) {
      return `
        <div class="stepper-wrap">
          <div class="stepper-titulo">Etapas del proceso</div>
          <p style="color:var(--ink-soft);font-size:12px;margin:0 0 10px;">Este expediente todavía no tiene etapas cargadas.</p>
          <form class="form-inline" data-rol="etapas">
            <div class="campo">
              <input type="text" name="etapas" placeholder="Ej: Apertura, Declaratoria de herederos, Inventario y avalúo, Partición" required>
            </div>
            <button type="submit" class="btn-chico">Agregar etapas</button>
          </form>
        </div>
      `;
    }
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
        <div class="stepper-acciones">
          ${actual > 0 ? `<button class="btn-chico" data-etapa="${actual - 1}">← Etapa anterior</button>` : ""}
          ${
            actual < e.etapas.length - 1
              ? `<button class="btn-teal" data-etapa="${actual + 1}">Avanzar a "${e.etapas[actual + 1]}" →</button>`
              : `<span class="badge teal">Proceso completo</span>`
          }
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
        <div class="ficha-campo"><div class="label">Cliente</div><div class="val ${e.clienteNombre ? "" : "vacio-campo"}">${e.clienteNombre || "Sin asignar"}</div></div>
        <div class="ficha-campo"><div class="label">Objeto</div><div class="val ${e.objeto ? "" : "vacio-campo"}">${e.objeto || "Sin especificar"}</div></div>
        <div class="ficha-campo"><div class="label">Último movimiento</div><div class="val ${e.ultimaActuacionFecha ? "" : "vacio-campo"}">${e.ultimaActuacionFecha ? fechaCorta(e.ultimaActuacionFecha) + " — " + e.ultimaActuacionTipo : "Sin movimientos"}</div></div>
      </div>
    `;

    panel.querySelectorAll("[data-etapa]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const nuevoIndex = parseInt(btn.getAttribute("data-etapa"), 10);
        try {
          await avanzarEtapa(e.id, nuevoIndex);
          e.etapaActualIndex = nuevoIndex;
          renderFicha(panel, e);
        } catch (err) {
          alert("No se pudo actualizar la etapa: " + err.message);
        }
      });
    });

    const formEtapas = panel.querySelector('form[data-rol="etapas"]');
    if (formEtapas) {
      formEtapas.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const f = new FormData(ev.target);
        try {
          const etapas = await guardarEtapas(e.id, f.get("etapas"));
          e.etapas = etapas;
          e.etapaActualIndex = 0;
          renderFicha(panel, e);
        } catch (err) {
          alert("No se pudieron guardar las etapas: " + err.message);
        }
      });
    }
  }

  async function renderActuacionesTab(panel, expedienteId) {
    panel.innerHTML = '<div class="vacio">Cargando...</div>';
    const [actuaciones, alertas] = await Promise.all([
      obtenerActuaciones(expedienteId),
      obtenerAlertasDeExpediente(expedienteId),
    ]);

    // Linea de tiempo del proceso: actuaciones ya presentadas + audiencias/plazos
    // agendados, todo junto en orden cronologico (lo mas viejo arriba).
    const items = [
      ...actuaciones.map((a) => ({ fecha: a.fecha, titulo: a.tipo, desc: a.descripcion, etiqueta: "Actuación" })),
      ...alertas.map((a) => ({
        fecha: a.fecha,
        titulo: a.mensaje,
        desc: "",
        etiqueta: ETIQUETA_TIPO[a.tipo] || a.tipo,
      })),
    ].sort((x, y) => x.fecha.localeCompare(y.fecha));

    panel.innerHTML = `
      <div class="timeline">
        ${
          items.length === 0
            ? '<div class="vacio">Sin actuaciones ni fechas cargadas todavía.</div>'
            : items
                .map(
                  (it) => `
          <div class="timeline-item ${claseLinea(it.fecha)}">
            <div class="timeline-fecha">${fechaCorta(it.fecha)}</div>
            <div class="timeline-cuerpo">
              <div class="tipo">${it.titulo}<span class="lt-badge">${it.etiqueta}</span></div>
              ${it.desc ? `<div class="desc">${it.desc}</div>` : ""}
            </div>
          </div>`
                )
                .join("")
        }
      </div>
      <form class="form-inline" data-rol="actuacion">
        <div class="campo chico">
          <label>Tipo</label>
          <input type="text" name="tipo" placeholder="Ej: Escrito" required>
        </div>
        <div class="campo chico">
          <label>Fecha</label>
          <input type="date" name="fecha" required>
        </div>
        <div class="campo">
          <label>Descripción</label>
          <input type="text" name="descripcion" placeholder="Opcional">
        </div>
        <button type="submit" class="btn-teal">Agregar</button>
      </form>
    `;

    panel.querySelector('form[data-rol="actuacion"]').addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const f = new FormData(ev.target);
      try {
        await crearActuacion(expedienteId, f.get("tipo"), f.get("fecha"), f.get("descripcion"));
        renderActuacionesTab(panel, expedienteId);
      } catch (e) {
        alert("No se pudo cargar la actuación: " + e.message);
      }
    });
  }

  function renderAgendaTab(panel, expedienteId) {
    panel.innerHTML = `
      <p style="color:var(--ink-soft);font-size:12.5px;margin:0 0 14px;">
        Agendá una audiencia o un plazo de escrito para este expediente — vas a verlo listado
        también en "Agenda" y en "Alertas" del menú.
      </p>
      <form class="form-inline" data-rol="alerta">
        <div class="campo chico">
          <label>Tipo</label>
          <select name="tipo_alerta">
            <option value="audiencia">Audiencia</option>
            <option value="plazo_escrito">Plazo de escrito</option>
          </select>
        </div>
        <div class="campo chico">
          <label>Fecha</label>
          <input type="date" name="fecha_alerta" required>
        </div>
        <div class="campo">
          <label>Detalle</label>
          <input type="text" name="mensaje" placeholder="Ej: Audiencia de mediación" required>
        </div>
        <div class="campo chico">
          <label>Visible para</label>
          <select name="para_rol">
            <option value="abogado">Solo yo (abogado)</option>
            <option value="cliente">También el cliente</option>
          </select>
        </div>
        <button type="submit" class="btn-chico">Agendar</button>
      </form>
    `;

    panel.querySelector('form[data-rol="alerta"]').addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const f = new FormData(ev.target);
      try {
        await crearAlerta(
          expedienteId,
          f.get("tipo_alerta"),
          f.get("fecha_alerta"),
          f.get("mensaje"),
          f.get("para_rol")
        );
        alert("Fecha agendada. La vas a ver en Agenda y en las Alertas pendientes.");
        ev.target.reset();
      } catch (e) {
        alert("No se pudo agendar: " + e.message);
      }
    });
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
        <button class="tab-btn" data-tab="actuaciones">Línea de tiempo</button>
        <button class="tab-btn" data-tab="documentos">Documentos</button>
        <button class="tab-btn" data-tab="honorarios">Honorarios</button>
        <button class="tab-btn" data-tab="agenda">Agenda</button>
      </div>
      <div class="tab-panel"></div>
    `;

    const panel = detalle.querySelector(".tab-panel");

    function activarTab(tab) {
      detalle.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("activo", b.getAttribute("data-tab") === tab));
      if (tab === "ficha") renderFicha(panel, expediente);
      if (tab === "actuaciones") renderActuacionesTab(panel, expedienteId);
      if (tab === "documentos") Adjuntos.renderTab(panel, expediente, perfilActual, "abogado");
      if (tab === "honorarios") Honorarios.renderTab(panel, expediente, perfilActual, true);
      if (tab === "agenda") renderAgendaTab(panel, expedienteId);
    }

    detalle.querySelectorAll(".tab-btn").forEach((b) => {
      b.addEventListener("click", () => activarTab(b.getAttribute("data-tab")));
    });

    activarTab("ficha");
  }

  async function vistaNuevoExpediente(contenedor) {
    const clientes = await obtenerClientes();
    contenedor.innerHTML = `
      <div class="encabezado-pagina">
        <h1>Nuevo expediente</h1>
        <p>Creá un expediente y, si ya está registrado, asignale un cliente.</p>
      </div>
      <div class="panel" style="max-width:480px">
        <form id="form-nuevo-expediente">
          <div class="campo">
            <label>Título / carátula</label>
            <input type="text" name="titulo" placeholder="Ej: Pérez c/ Empresa S.A. – Daños" required>
          </div>
          <div class="campo">
            <label>Objeto / tipo de trámite</label>
            <input type="text" name="objeto" placeholder="Ej: Sucesión ab intestato, Daños y perjuicios">
          </div>
          <div class="campo">
            <label>Cliente</label>
            <div style="display:flex;gap:16px;margin-bottom:8px;font-size:12.5px;color:var(--ink-soft);">
              <label><input type="radio" name="modo_cliente" value="existente" checked> Cliente existente</label>
              <label><input type="radio" name="modo_cliente" value="nuevo"> Cliente nuevo</label>
            </div>
            <select name="cliente_id" id="select-cliente-existente">
              <option value="">Sin asignar por ahora</option>
              ${clientes.map((c) => `<option value="${c.id}">${c.nombre} (${c.email})</option>`).join("")}
            </select>
            <div id="campos-cliente-nuevo" class="oculto" style="margin-top:10px;display:flex;flex-direction:column;gap:10px;">
              <input type="text" name="cliente_nuevo_nombre" placeholder="Nombre y apellido del cliente">
              <input type="email" name="cliente_nuevo_email" placeholder="Email del cliente">
              <input type="password" name="cliente_nuevo_password" placeholder="Contraseña inicial (se la pasás vos al cliente)">
            </div>
          </div>
          <div class="campo">
            <label>Etapas del proceso (opcional)</label>
            <input type="text" name="etapas" placeholder="Ej: Apertura, Declaratoria de herederos, Inventario y avalúo, Partición">
          </div>
          <button type="submit" class="btn-teal">Crear expediente</button>
        </form>
      </div>
    `;

    const radiosModo = contenedor.querySelectorAll('input[name="modo_cliente"]');
    const selectExistente = contenedor.querySelector("#select-cliente-existente");
    const camposNuevo = contenedor.querySelector("#campos-cliente-nuevo");
    radiosModo.forEach((r) => {
      r.addEventListener("change", () => {
        const esNuevo = contenedor.querySelector('input[name="modo_cliente"]:checked').value === "nuevo";
        selectExistente.classList.toggle("oculto", esNuevo);
        camposNuevo.classList.toggle("oculto", !esNuevo);
      });
    });

    document.getElementById("form-nuevo-expediente").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const f = new FormData(ev.target);
      const btn = ev.target.querySelector('button[type="submit"]');
      const original = btn.textContent;
      try {
        let clienteId = f.get("cliente_id");
        if (f.get("modo_cliente") === "nuevo") {
          const nombre = (f.get("cliente_nuevo_nombre") || "").trim();
          const email = (f.get("cliente_nuevo_email") || "").trim();
          const password = f.get("cliente_nuevo_password") || "";
          if (!nombre || !email || !password) {
            alert("Completá nombre, email y contraseña del cliente nuevo.");
            return;
          }
          btn.disabled = true;
          btn.textContent = "Creando cliente...";
          const nuevoCliente = await crearClienteNuevo(nombre, email, password);
          clienteId = nuevoCliente.id;
        }
        btn.textContent = "Creando expediente...";
        await crearExpediente(f.get("titulo"), clienteId, f.get("objeto"), f.get("etapas"));
        navegarA("expedientes");
      } catch (e) {
        alert("No se pudo crear: " + e.message);
        btn.disabled = false;
        btn.textContent = original;
      }
    });
  }

  async function vistaAlertas(contenedor) {
    const alertas = await obtenerAlertasPendientes();
    contenedor.innerHTML = `
      <div class="encabezado-pagina">
        <h1>Alertas</h1>
        <p>Pendientes sin marcar como leídas.</p>
      </div>
      <div class="panel">
        ${
          alertas.length === 0
            ? '<div class="vacio">No tenés alertas pendientes.</div>'
            : `<table class="tabla">
                <tr><th>Expediente</th><th>Mensaje</th><th>Fecha</th><th></th></tr>
                ${alertas
                  .map(
                    (a) => `<tr>
                      <td>${a.expedienteTitulo}</td>
                      <td>${a.mensaje}</td>
                      <td>${fechaCorta(a.fecha)}</td>
                      <td><button class="btn-chico" data-marcar="${a.id}">Marcar leída</button></td>
                    </tr>`
                  )
                  .join("")}
              </table>`
        }
      </div>
    `;

    contenedor.querySelectorAll("[data-marcar]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await marcarAlertaLeida(btn.getAttribute("data-marcar"));
        vistaAlertas(contenedor);
      });
    });
  }

  async function vistaAgenda(contenedor) {
    const agenda = await obtenerAgendaCompleta();
    contenedor.innerHTML = `
      <div class="encabezado-pagina">
        <h1>Agenda</h1>
        <p>Audiencias y plazos de todos tus expedientes, ordenados por fecha.</p>
      </div>
      <div class="panel">
        ${
          agenda.length === 0
            ? '<div class="vacio">Todavía no agendaste audiencias ni plazos. Entrá a un expediente para cargar el primero.</div>'
            : `<table class="tabla">
                <tr><th>Estado</th><th>Expediente</th><th>Tipo</th><th>Detalle</th><th>Fecha</th><th></th></tr>
                ${agenda
                  .map((a) => {
                    const u = calcularUrgencia(a.fecha);
                    return `<tr>
                      <td><span class="${u.clase}">${u.label}</span></td>
                      <td>${a.expedienteTitulo}</td>
                      <td>${ETIQUETA_TIPO[a.tipo] || a.tipo}</td>
                      <td>${a.mensaje}${a.paraRol === "cliente" ? " <span class=\"badge teal\">visible al cliente</span>" : ""}</td>
                      <td>${fechaCorta(a.fecha)}</td>
                      <td>${a.leida ? "" : `<button class="btn-chico" data-marcar="${a.id}">Marcar leída</button>`}</td>
                    </tr>`;
                  })
                  .join("")}
              </table>`
        }
      </div>
    `;

    contenedor.querySelectorAll("[data-marcar]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await marcarAlertaLeida(btn.getAttribute("data-marcar"));
        vistaAgenda(contenedor);
      });
    });
  }

  async function render(perfil, vista, contenedor) {
    perfilActual = perfil;
    if (vista === "expedientes") return vistaExpedientes(contenedor);
    if (vista === "nuevo") return vistaNuevoExpediente(contenedor);
    if (vista === "agenda") return vistaAgenda(contenedor);
    if (vista === "alertas") return vistaAlertas(contenedor);
    return vistaInicio(contenedor);
  }

  const menu = [
    { id: "inicio", label: "Inicio" },
    { id: "expedientes", label: "Mis expedientes" },
    { id: "nuevo", label: "Nuevo expediente" },
    { id: "agenda", label: "Agenda" },
    { id: "alertas", label: "Alertas" },
  ];

  return { render, menu };
})();
