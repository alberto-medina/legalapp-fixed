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

Subí toda esta carpeta a [Netlify Drop](https://app.netlify.com/drop) arrastrándola, o conectá
un repositorio de GitHub con esta carpeta desde el panel de Netlify. No hace falta ningún paso
de build — son archivos estáticos.

## Qué incluye esta versión

- Panel de abogado: expedientes, carga de actuaciones, **Agenda** (audiencias y plazos de
  escritos con aviso de urgencia automático: Vencido / Urgente / Próximo / Programado, según
  cuántos días faltan) y Alertas pendientes.
- Panel de cliente: solo lectura de sus expedientes, línea de tiempo de actuaciones, y sus
  propias fechas de audiencia si el abogado las marcó como visibles.
- Panel de admin: todos los expedientes y usuarios.

## Qué falta (a propósito, para una próxima etapa)

- Notificaciones push/email reales (hoy la "alerta" se ve al entrar a la Agenda, no llega un
  aviso afuera de la app).
- Edición/gestión de usuarios desde el panel de admin (por ahora es de solo lectura).
