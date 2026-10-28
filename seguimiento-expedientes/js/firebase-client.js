// Inicializa Firebase (compat SDK, sin build step) y expone auth/db compartidos.
// Los archivos NO usan Firebase Storage (pide plan pago) -- van a Backblaze B2
// a traves de un Worker de Cloudflare, ver js/archivos.js.
firebase.initializeApp(firebaseConfig);
const authClient = firebase.auth();
const db = firebase.firestore();
