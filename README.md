# Juris Lex — Guía de configuración y deploy

## Stack
- **Frontend:** Python + KivyMD (Android, iOS, Windows)
- **Base de datos:** Supabase (PostgreSQL en la nube)
- **Autenticación:** pbkdf2_hmac con salt (256k iteraciones SHA-256)
- **Pagos:** MercadoPago API

---

## 1. Configuración local (desarrollo)

```bash
# 1. Clonar repo
git clone https://github.com/alberto-medina/legalapp-fixed
cd legalapp-fixed

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install kivy kivymd pillow requests supabase python-dotenv

# 4. Configurar credenciales
cp .env.example .env
# Editar .env con tus datos de Supabase

# 5. Correr la app
python main.py
```

---

## 2. Configurar Supabase (base de datos en la nube)

1. Crear cuenta gratis en https://supabase.com
2. Crear nuevo proyecto (ej: "jurislex")
3. Ir a **SQL Editor → New query**
4. Copiar y ejecutar todo el contenido de `supabase_schema.sql`
5. Ir a **Settings → API** y copiar:
   - `URL` → `SUPABASE_URL` en `.env`
   - `anon public` key → `SUPABASE_ANON_KEY` en `.env`

**Plan gratuito de Supabase incluye:**
- 500 MB de base de datos
- 50,000 filas
- 50 MB de almacenamiento
- 2 GB de transferencia

Para producción con miles de usuarios: plan Pro desde $25/mes.

---

## 3. Build Android (Google Play)

```bash
# Instalar buildozer (en Linux o WSL)
pip install buildozer

# Build debug (para testear)
buildozer android debug

# Build release (para Google Play — requiere keystore)
buildozer android release
```

### Keystore para firma (una sola vez)
```bash
keytool -genkey -v -keystore jurislex.keystore -alias jurislex \
  -keyalg RSA -keysize 2048 -validity 10000
```

---

## 4. Build iOS (App Store)

Requiere **Mac con Xcode 15+**.

```bash
# Instalar kivy-ios
pip install kivy-ios

# Build
toolchain build python3 kivy
toolchain create JurisLex .
cd JurisLex-ios
open JurisLex.xcworkspace
```

En Xcode:
- Seleccionar tu Apple Developer Team
- Configurar Bundle ID: `com.jurislex.app`
- Agregar Privacy descriptions en Info.plist (ver abajo)
- Archivar y subir a App Store Connect

### Privacy descriptions requeridas (Info.plist)
```xml
<key>NSCameraUsageDescription</key>
<string>Juris Lex necesita acceso a la cámara para actualizar tu foto de perfil.</string>

<key>NSPhotoLibraryUsageDescription</key>
<string>Juris Lex necesita acceso a fotos para adjuntar archivos a tu consulta.</string>

<key>NSMicrophoneUsageDescription</key>
<string>Juris Lex necesita el micrófono para las videollamadas con tu abogado.</string>
```

---

## 5. Checklist App Store / Google Play

### Google Play
- [ ] AAB firmado con keystore (buildozer genera .aab)
- [ ] targetSdkVersion = 34 (requerido 2024)
- [ ] Política de privacidad publicada en URL pública
- [ ] Screenshots 2-8 por tipo de dispositivo
- [ ] Descripción sin palabras prohibidas

### Apple App Store
- [ ] Cuenta Apple Developer ($99/año)
- [ ] Privacy Nutrition Label completada en App Store Connect
- [ ] Info.plist con NSUsageDescription para cada permiso
- [ ] App Transport Security habilitado (HTTPS forzado)
- [ ] Soporte para iPhone SE hasta iPhone 15 Pro Max

---

## 6. Archivos eliminados (scripts de debug)

Los siguientes archivos existían en el repo original y fueron eliminados
porque son scripts manuales de setup que no deben ir en el APK producción:

- `crear_abogado.py` — script de inserción manual
- `fix_abogado.py` — parche de debug
- `ver_usuarios.py` — admin tool sin autenticación
- `reset_password.py` — script CLI suelto

Su funcionalidad está integrada en `database.py` (usuarios demo via `crear_usuarios_demo()`)
y en `auth_controller.py` (cambio de contraseña via `change_password()`).

---

## 7. Seguridad implementada

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| Hash de contraseñas | SHA-256 sin salt | pbkdf2_hmac + salt aleatorio 32 bytes, 260k iteraciones |
| Errores de BD | `except: pass` silencioso | Logging + mensajes de usuario claros |
| Importaciones circulares | database.py importaba kivy.App | Eliminado, usa os.environ |
| Credenciales | Hardcodeadas | Variables de entorno (.env) |
| HTTP/HTTPS | Sin restricción | network_security_config.xml fuerza HTTPS |
| Archivos basura en APK | 4 scripts de debug | Excluidos via .gitignore y buildozer |
