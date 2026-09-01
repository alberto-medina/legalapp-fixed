# LegalApp Pro

App móvil Android que conecta clientes con abogados en tiempo real — chat, videollamada,
pagos y gestión de consultas legales. Publicada en Google Play, en producción.

*Android app connecting clients with lawyers in real time — chat, video calls, payments,
and legal case management. Published on Google Play, live in production.*

---

## 🇦🇷 Español

### Stack técnico

- **Frontend:** Python + [Kivy](https://kivy.org/) (Android, compilado con Buildozer /
  python-for-android)
- **Backend / base de datos:** [Supabase](https://supabase.com) (PostgreSQL administrado +
  Edge Functions en Deno/TypeScript)
- **Autenticación:** Firebase Auth (email/contraseña y Google Sign-In vía REST API, sin SDK
  nativo de Firebase del lado del cliente)
- **Login biométrico:** `android.hardware.biometrics.BiometricPrompt` nativo, con un puente
  Java propio (pyjnius no puede extender clases abstractas de Java, solo interfaces)
- **Notificaciones push:** Firebase Cloud Messaging
- **Pagos:** MercadoPago, procesados a través de una Edge Function propia (nunca se expone
  ningún token de pago del lado del cliente)

### Arquitectura de seguridad

Este proyecto pasó por un proceso real de hardening de seguridad, no solo lo básico:

- **Row Level Security (RLS)** en las tablas sensibles de Postgres (roles, aprobaciones,
  retiros de dinero).
- Las acciones administrativas (aprobar abogado, procesar un retiro, editar precios) **no
  se resuelven del lado del cliente** — pasan por una Edge Function que valida el `id_token`
  de Firebase contra el rol real guardado en la base antes de ejecutar nada.
- Ninguna credencial privada vive en el código. Las únicas claves embebidas en el cliente
  son la `anon key` pública de Supabase (protegida por RLS, no por estar oculta) y la API key
  pública de Firebase — el mismo diseño que usa cualquier app móvil.
- El historial de git fue reescrito para eliminar una clave de servicio que se había subido
  por error en una etapa temprana del proyecto (ya revocada de todos modos, pero limpiada del
  historial igual).

### Estado

Publicada en Google Play, versión en producción activa. Repositorio en desarrollo continuo.

---

## 🇬🇧 English

### Tech stack

- **Frontend:** Python + [Kivy](https://kivy.org/) (Android, built with Buildozer /
  python-for-android)
- **Backend / database:** [Supabase](https://supabase.com) (managed PostgreSQL + Deno/
  TypeScript Edge Functions)
- **Authentication:** Firebase Auth (email/password and Google Sign-In via REST API, no
  client-side native Firebase SDK)
- **Biometric login:** native `android.hardware.biometrics.BiometricPrompt`, wrapped in a
  small custom Java bridge (pyjnius can only implement Java interfaces from Python, not
  extend abstract classes — `BiometricPrompt.AuthenticationCallback` is abstract)
- **Push notifications:** Firebase Cloud Messaging
- **Payments:** MercadoPago, processed through a dedicated Edge Function (no payment token
  is ever exposed client-side)

### Security architecture

This project went through a real security hardening pass, not just the basics:

- **Row Level Security (RLS)** on sensitive Postgres tables (user roles, approvals,
  withdrawals).
- Admin actions (approving a lawyer, processing a withdrawal, editing prices) are **never
  resolved client-side** — they go through an Edge Function that validates the Firebase
  `id_token` against the real role stored in the database before executing anything.
- No private credential lives in the codebase. The only keys embedded on the client are
  Supabase's public `anon key` (protected by RLS, not by secrecy) and Firebase's public API
  key — the same design any mobile app uses.
- Git history was rewritten to remove a service account key that had been committed by
  mistake early in the project (already revoked regardless, but scrubbed from history too).

### Status

Published on Google Play, active production release. Actively maintained.
