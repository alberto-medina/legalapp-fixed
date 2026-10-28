# Portal de Seguimiento de Expedientes — puesta en marcha (Firebase)

Sistema aparte de Legal App, con su propio proyecto de Firebase (plan gratis "Spark",
de sobra para esto). Seguí estos pasos en orden, una sola vez.

## 1. Crear el proyecto en Firebase

1. Entrá a https://console.firebase.google.com y creá un proyecto nuevo (botón "Agregar proyecto").
2. Nombre sugerido: `seguimiento-expedientes`. Podés desactivar Google Analytics, no hace falta.
3. Esperá a que termine de crearse.

## 2. Activar el login por email/contraseña

1. En el menú de la izquierda: **Authentication → Comenzar** (o "Get started").
2. Pestaña **Sign-in method** → elegí **Email/contraseña** → activalo → Guardar.

## 3. Crear la base de datos (Firestore)

1. En el menú: **Firestore Database → Crear base de datos**.
2. Elegí **modo producción** (no "modo de prueba") y una ubicación (cualquiera de
   Sudamérica si está disponible, sino la más cercana).
3. Esperá a que se cree.

## 4. Cargar las reglas de seguridad

1. Dentro de Firestore Database → pestaña **Reglas**.
2. Borrá lo que haya y pegá TODO el contenido del archivo `firestore.rules` de esta carpeta.
3. **Publicar**.

## 5. Conectar la app web con tu proyecto

1. En el ícono de **engranaje (Configuración del proyecto)** → abajo, en "Tus apps" → ícono
   `</>` (Web) → registrá una app (el nombre no importa, ej. "seguimiento-web").
2. Te va a mostrar un objeto `firebaseConfig` con varios valores. Copiá TODO ese bloque.
3. Abrí el archivo `js/firebase-config.js` de esta carpeta y reemplazá los valores
   `PEGA_AQUI_...` por los reales que te dio Firebase.

## 6. Crear los usuarios de prueba

1. **Authentication → Users → Add user**.
2. Creá estos 3 (podés usar otros emails si preferís, solo recordalos):
   - `abogado@tudominio.com` / una contraseña
   - `cliente@tudominio.com` / una contraseña
   - `admin@tudominio.com` / una contraseña
3. Para cada uno, copiá el **User UID** que le queda asignado (una cadena larga de letras y
   números) — lo vas a necesitar en el paso siguiente.

## 7. Crear el perfil (rol) de cada usuario

1. **Firestore Database → Datos → Iniciar colección**.
2. Nombre de la colección: `perfiles`.
3. Para cada uno de los 3 usuarios: el **ID del documento** tiene que ser exactamente el
   **User UID** que copiaste en el paso anterior (no lo escribas vos, pegá el UID real).
4. Agregale estos campos (tipo `string` los tres):
   - `email` → el mismo email que usaste al crear el usuario
   - `nombre` → el nombre que quieras mostrar (ej. "Alberto Medina")
   - `rol` → `abogado`, `cliente` o `admin` según corresponda
5. Repetí para los 3 usuarios (3 documentos distintos dentro de la misma colección `perfiles`).

## 8. Probarlo

- Abrí `index.html` haciendo doble clic (se abre en tu navegador).
- Entrá con el usuario `abogado@...` → creá un expediente, asignale el cliente de prueba,
  cargale una actuación, y agendale una audiencia marcada como "También el cliente".
- Cerrá sesión y entrá con `cliente@...` → tiene que ver ese expediente, esa actuación, y la
  audiencia agendada en "Próximas fechas" — pero sin poder editar nada.
- Entrá con `admin@...` → tiene que ver todos los expedientes y todos los usuarios.

### Si una pantalla queda en blanco o tira error de "índice" (index)

Es normal la primera vez: Firestore necesita un "índice compuesto" para algunas de las
consultas (por ejemplo, "mis alertas sin leer, ordenadas por fecha"). Cuando falta, el error
que aparece en la consola del navegador (F12 → Console) trae un **link directo** que dice algo
como "create it here" — hacé clic, confirmá, esperá 1-2 minutos a que termine de crearse, y
recargá la página. Puede pasar 3 o 4 veces la primera vez que se usa cada pantalla nueva
(Inicio, Alertas, Agenda) — es solo la primera vez por cada combinación de filtros.

## 9. Publicarlo (cuando quieras que sea accesible por internet, no solo en tu PC)

El sitio está publicado en **Cloudflare Pages** (proyecto `seguimiento-expediente`, URL
`seguimiento-expediente.pages.dev`). No hace falta ningún paso de build — son archivos
estáticos. Para subir una actualización:

1. Reconstruir la carpeta `dist/` (copia de `index.html`, `app.html`, `css/`, `js/`, `assets/`
   — sin `worker-archivos/`, `node_modules/`, `.wrangler/`, `service-account.json`, `sql/`,
   `seed-perfiles.js` ni este archivo).
2. Entrar a Cloudflare → **Trabajadores y Pajes** (Workers & Pages) → proyecto
   `seguimiento-expediente` (el que tiene el rayito ⚡, **no** el que termina en
   `-archivos`) → pestaña **Despliegues**.
3. Arrastrar la carpeta `dist` para subir la nueva versión.

**Importante:** en esa misma lista de "Trabajadores y Pajes" también vas a ver
`seguimiento-expedientes-archivos` (el Worker de archivos, ver sección siguiente) y
posiblemente `evidencia-digital` (de tu otro proyecto, "bóveda" — no tiene nada que ver con
este sistema, no tocar).

## 10. Archivos adjuntos: Backblaze B2 + Cloudflare Worker

Firebase Storage pide activar un plan de facturación (Blaze) incluso para uso gratuito, así que
los archivos (documentos que sube el abogado, adjuntos del cliente, tickets de gastos, foto del
estudio) **no** se guardan en Firebase. Se guardan en **Backblaze B2** (gratis, sin tarjeta), y
en el medio hay un **Cloudflare Worker** (`seguimiento-expedientes-archivos`,
`worker-archivos/src/index.js`) que actúa de portero:

1. El navegador le pide al Worker "quiero subir/bajar este archivo", mandando su propio token
   de sesión de Firebase.
2. El Worker le pregunta a Firestore, con ESE mismo token, si el usuario tiene permiso de leer
   el expediente o el perfil correspondiente — reusando `firestore.rules` tal cual están, sin
   duplicar lógica de permisos.
3. Si Firestore dice que sí, recién ahí el Worker habla con Backblaze usando la clave secreta
   de Backblaze, que **nunca** llega al navegador (vive solo como secreto del Worker, cargada
   con `wrangler secret put B2_KEY_ID` / `B2_APP_KEY`).

El bucket de Backblaze (`seguimiento-expedientes`) y su clave de aplicación son propios de este
proyecto — **no** son los mismos que usa "bóveda"/evidencia-digital, aunque estén en la misma
cuenta de Backblaze.

Para volver a desplegar el Worker después de cambiarlo:
```
cd worker-archivos
CLOUDFLARE_API_TOKEN="..." npx wrangler deploy
```

## Qué incluye esta versión

- Panel de abogado: expedientes (con número, carátula y objeto), **etapas del proceso**
  (stepper editable, ej. las 4 estaciones de un sucesorio — el proceso se marca "completo" con
  un botón explícito, no solo por estar parado en la última etapa), carga de actuaciones con
  **semáforo** (🟡 en proceso / 🟢 avanza / 🔴 cancelado) combinadas en una línea de tiempo con
  la Agenda, **Agenda** (audiencias y plazos de escritos con aviso de urgencia automático:
  Vencido / Urgente / Próximo / Programado), Alertas pendientes, **Documentos** (subida de
  archivos vía Backblaze) y **Honorarios** (carga de montos con ticket de gasto adjunto y
  recibo imprimible). También puede dar de alta clientes nuevos directamente desde el panel
  (sin usar la consola de Firebase, y sin perder su propia sesión de abogado).
- Panel de cliente: solo lectura de sus expedientes, etapas, línea de tiempo con semáforo,
  Documentos (puede además subir sus propios archivos), Honorarios/recibo, y sus propias
  fechas de audiencia si el abogado las marcó como visibles.
- Panel de admin: todos los expedientes y usuarios (solo lectura).
- Logo real de LegalApp (no emoji) en login y barra superior.

## Qué falta (a propósito, para una próxima etapa)

- **"Mi estudio" (foto + nombre + contacto del abogado, visible para el cliente):** la base ya
  está lista (reglas de Firestore permiten que el abogado actualice `estudioNombre` /
  `estudioContacto` / `estudioFotoPath` en su propio perfil, y el Worker ya acepta subir/bajar
  archivos de tipo `perfil` además de `expediente`), pero **todavía no existe la pantalla** para
  cargarlo ni el bloque que lo muestre en la ficha del cliente. Queda pendiente.
- Notificaciones push/email reales (hoy la "alerta" se ve al entrar a la Agenda, no llega un
  aviso afuera de la app).
- Edición/gestión de usuarios desde el panel de admin (por ahora es de solo lectura).
- Calendario visual (mes/semana) para la Agenda — hoy es una lista.
