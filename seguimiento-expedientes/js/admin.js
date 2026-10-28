// Panel de admin: visibilidad total de expedientes y usuarios (primera versión, sin edición).

const Admin = (() => {
  function docA(doc) {
    return { id: doc.id, ...doc.data() };
  }

  async function obtenerExpedientes() {
    try {
      const snap = await db.collection("expedientes").orderBy("createdAt", "desc").get();
      return snap.docs.map(docA);
    } catch (e) {
      console.error(e);
      return [];
    }
  }

  async function obtenerUsuarios() {
    try {
      const snap = await db.collection("perfiles").orderBy("rol").get();
      return snap.docs.map(docA);
    } catch (e) {
      console.error(e);
      return [];
    }
  }

  async function vistaExpedientes(contenedor) {
    const expedientes = await obtenerExpedientes();
    contenedor.innerHTML = `
      <div class="encabezado-pagina">
        <h1>Todos los expedientes</h1>
        <p>Vista de administrador — solo lectura por ahora.</p>
      </div>
      <div class="panel">
        ${
          expedientes.length === 0
            ? '<div class="vacio">No hay expedientes cargados todavía.</div>'
            : `<table class="tabla">
                <tr><th>N°</th><th>Carátula</th><th>Cliente</th><th>Estado</th></tr>
                ${expedientes
                  .map(
                    (e) => `<tr>
                      <td>${e.numero || "—"}</td>
                      <td>${e.titulo}</td>
                      <td>${e.clienteNombre || "sin asignar"}</td>
                      <td><span class="badge teal">${e.estado}</span></td>
                    </tr>`
                  )
                  .join("")}
              </table>`
        }
      </div>
    `;
  }

  async function vistaUsuarios(contenedor) {
    const usuarios = await obtenerUsuarios();
    contenedor.innerHTML = `
      <div class="encabezado-pagina">
        <h1>Usuarios</h1>
        <p>Todos los perfiles registrados en el sistema.</p>
      </div>
      <div class="panel">
        <table class="tabla">
          <tr><th>Nombre</th><th>Email</th><th>Rol</th></tr>
          ${usuarios
            .map(
              (u) => `<tr>
                <td>${u.nombre}</td>
                <td>${u.email}</td>
                <td><span class="badge">${u.rol}</span></td>
              </tr>`
            )
            .join("")}
        </table>
      </div>
    `;
  }

  async function render(_perfil, vista, contenedor) {
    if (vista === "usuarios") return vistaUsuarios(contenedor);
    return vistaExpedientes(contenedor);
  }

  const menu = [
    { id: "inicio", label: "Expedientes" },
    { id: "usuarios", label: "Usuarios" },
  ];

  return { render, menu };
})();
