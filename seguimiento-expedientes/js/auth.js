// Login, logout y lectura del perfil (rol) del usuario logueado. (Firebase Auth + Firestore)

async function iniciarSesion(email, password) {
  return authClient.signInWithEmailAndPassword(email, password);
}

async function cerrarSesion() {
  await authClient.signOut();
  window.location.href = "index.html";
}

async function obtenerPerfilActual() {
  const user = authClient.currentUser;
  if (!user) return null;

  const doc = await db.collection("perfiles").doc(user.uid).get();
  if (!doc.exists) {
    console.error("No existe un perfil en Firestore para este usuario:", user.uid);
    return null;
  }
  return { id: doc.id, ...doc.data() };
}

// Espera a que Firebase resuelva el estado de sesión inicial (es asíncrono).
function esperarUsuario() {
  return new Promise((resolve) => {
    const quitar = authClient.onAuthStateChanged((user) => {
      quitar();
      resolve(user);
    });
  });
}

// Llamar al principio de app.html: si no hay sesión o no hay perfil, redirige al login.
async function exigirSesion() {
  const user = await esperarUsuario();
  if (!user) {
    window.location.href = "index.html";
    return null;
  }

  const perfil = await obtenerPerfilActual();
  if (!perfil) {
    window.location.href = "index.html";
    return null;
  }
  return perfil;
}
