// Crea los 3 perfiles de prueba en Firestore usando la clave de administrador.
// Correr una sola vez: node seed-perfiles.js

const { initializeApp, cert } = require("firebase-admin/app");
const { getFirestore } = require("firebase-admin/firestore");
const serviceAccount = require("./service-account.json");

const app = initializeApp({ credential: cert(serviceAccount) });
const db = getFirestore(app);

const perfiles = [
  {
    uid: "BWh4EDjsofgL53CTvOg5aUahUUl1",
    email: "abogado@tudominio.com",
    nombre: "Alberto Medina",
    rol: "abogado",
  },
  {
    uid: "3fZY72fAZrZ5XCZTsqGsqz1aLs83",
    email: "cliente@tudominio.com",
    nombre: "Cliente de Prueba",
    rol: "cliente",
  },
  {
    uid: "jtSLg5LxPQfTFTYHEUMVyhd4HfE3",
    email: "admin@tudominio.com",
    nombre: "Administrador",
    rol: "admin",
  },
];

(async () => {
  for (const p of perfiles) {
    await db.collection("perfiles").doc(p.uid).set({
      email: p.email,
      nombre: p.nombre,
      rol: p.rol,
    });
    console.log(`Creado: ${p.rol} (${p.email})`);
  }
  console.log("Listo. Los 3 perfiles quedaron cargados en Firestore.");
  process.exit(0);
})().catch((e) => {
  console.error("Error:", e.message);
  process.exit(1);
});
