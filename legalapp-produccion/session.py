import json
import os
from kivy.utils import platform

# =========================================================
# SESSION GLOBAL
# =========================================================

current_user = None
current_consulta_id = None

pending_uid = None
pending_email = None

# Registro abogado
abogado_registrando_uid = None
monto_suscripcion = 55000
especialidades_abogado = []

# Flujo consulta
area_legal = None
abogado_seleccionado = None
estado_abogado = None
tipo_servicio = None

# Pago consulta
pago_pending_abogado_uid = None
pago_pending_abogado_email = None
pago_pending_cliente_uid = None
pago_pending_cliente_email = None
pago_pending_precio = None
pago_external_reference = None
pago_preference_id = None
pago_init_point = None
pago_tipo = None
pago_monto = None
especialidad_a_agregar = None
especialidades_actuales = None

# Ubicacion busqueda cliente
provincia_busqueda = None
ciudad_busqueda = None

# Compatibilidad con pantallas viejas
user_data = None
user_id = None
id_token = None
refresh_token = None

# =========================================================
# ARCHIVO DE PERSISTENCIA
# =========================================================

SESSION_FILENAME = '.legalapp_session.json'
SESSION_FILE = os.path.join(os.path.expanduser('~'), SESSION_FILENAME)


def _session_paths():
    paths = []

    try:
        from kivy.app import App
        app = App.get_running_app()
        if app and app.user_data_dir:
            paths.append(os.path.join(app.user_data_dir, SESSION_FILENAME))
    except Exception:
        pass

    # En Android priorizamos solo el directorio privado de la app.
    # Evita intentar escribir en /data/.legalapp_session.json al pausar/reanudar,
    # lo que generaba errores repetidos al volver desde notificaciones.
    if platform != "android":
        paths.append(SESSION_FILE)

    unique = []
    for path in paths:
        if path and path not in unique:
            unique.append(path)
    return unique

# =========================================================
# GETTERS
# =========================================================

def get_uid():
    global current_user
    if current_user:
        return current_user.get("uid")
    return None


def get_email():
    global current_user
    if current_user:
        return current_user.get("email")
    return None


def get_nombre():
    global current_user
    if current_user:
        return (
            current_user.get("nombre")
            or current_user.get("username")
            or ""
        )
    return ""


def get_rol():
    global current_user
    if current_user:
        return current_user.get("rol")
    return None


def es_abogado():
    global current_user
    if current_user:
        return current_user.get("rol") == "abogado"
    return False


def es_cliente():
    global current_user
    if current_user:
        return current_user.get("rol") == "cliente"
    return False


# =========================================================
# PERSISTENCIA
# =========================================================

def guardar():
    """Guarda la sesion en disco para sobrevivir cierres de app"""
    global current_user, current_consulta_id, pending_uid, pending_email
    global abogado_registrando_uid, monto_suscripcion, especialidades_abogado
    global area_legal, abogado_seleccionado, estado_abogado, tipo_servicio
    global pago_pending_abogado_uid, pago_pending_abogado_email
    global pago_pending_cliente_uid, pago_pending_cliente_email, pago_pending_precio
    global pago_external_reference, pago_preference_id, pago_init_point
    global pago_tipo, pago_monto, especialidad_a_agregar, especialidades_actuales
    global provincia_busqueda, ciudad_busqueda, user_data, user_id, id_token, refresh_token

    data = {
        'current_user': current_user,
        'current_consulta_id': current_consulta_id,
        'pending_uid': pending_uid,
        'pending_email': pending_email,
        'abogado_registrando_uid': abogado_registrando_uid,
        'monto_suscripcion': monto_suscripcion,
        'especialidades_abogado': especialidades_abogado,
        'area_legal': area_legal,
        'abogado_seleccionado': abogado_seleccionado,
        'estado_abogado': estado_abogado,
        'tipo_servicio': tipo_servicio,
        'pago_pending_abogado_uid': pago_pending_abogado_uid,
        'pago_pending_abogado_email': pago_pending_abogado_email,
        'pago_pending_cliente_uid': pago_pending_cliente_uid,
        'pago_pending_cliente_email': pago_pending_cliente_email,
        'pago_pending_precio': pago_pending_precio,
        'pago_external_reference': pago_external_reference,
        'pago_preference_id': pago_preference_id,
        'pago_init_point': pago_init_point,
        'pago_tipo': pago_tipo,
        'pago_monto': pago_monto,
        'especialidad_a_agregar': especialidad_a_agregar,
        'especialidades_actuales': especialidades_actuales,
        'provincia_busqueda': provincia_busqueda,
        'ciudad_busqueda': ciudad_busqueda,
        'user_data': user_data,
        'user_id': user_id,
        'id_token': id_token,
        'refresh_token': refresh_token,
    }

    guardada = False
    ultimo_error = None

    for path in _session_paths():
        try:
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(path, 'w') as f:
                json.dump(data, f)
            guardada = True
            print(f"Sesion guardada: {path}")
        except Exception as e:
            ultimo_error = e
            print(f"ERROR guardando sesion en {path}: {e}")

    if not guardada and ultimo_error:
        print(f"ERROR guardando sesion: {ultimo_error}")


def cargar():
    """Carga la sesion desde disco"""
    global current_user, current_consulta_id, pending_uid, pending_email
    global abogado_registrando_uid, monto_suscripcion, especialidades_abogado
    global area_legal, abogado_seleccionado, estado_abogado, tipo_servicio
    global pago_pending_abogado_uid, pago_pending_abogado_email
    global pago_pending_cliente_uid, pago_pending_cliente_email, pago_pending_precio
    global pago_external_reference, pago_preference_id, pago_init_point
    global pago_tipo, pago_monto, especialidad_a_agregar, especialidades_actuales
    global provincia_busqueda, ciudad_busqueda, user_data, user_id, id_token, refresh_token

    for path in _session_paths():
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)

                current_user = data.get('current_user')
                current_consulta_id = data.get('current_consulta_id')
                pending_uid = data.get('pending_uid')
                pending_email = data.get('pending_email')
                abogado_registrando_uid = data.get('abogado_registrando_uid')
                monto_suscripcion = data.get('monto_suscripcion', 55000)
                especialidades_abogado = data.get('especialidades_abogado', [])
                area_legal = data.get('area_legal')
                abogado_seleccionado = data.get('abogado_seleccionado')
                estado_abogado = data.get('estado_abogado')
                tipo_servicio = data.get('tipo_servicio')
                pago_pending_abogado_uid = data.get('pago_pending_abogado_uid')
                pago_pending_abogado_email = data.get('pago_pending_abogado_email')
                pago_pending_cliente_uid = data.get('pago_pending_cliente_uid')
                pago_pending_cliente_email = data.get('pago_pending_cliente_email')
                pago_pending_precio = data.get('pago_pending_precio')
                pago_external_reference = data.get('pago_external_reference')
                pago_preference_id = data.get('pago_preference_id')
                pago_init_point = data.get('pago_init_point')
                pago_tipo = data.get('pago_tipo')
                pago_monto = data.get('pago_monto')
                especialidad_a_agregar = data.get('especialidad_a_agregar')
                especialidades_actuales = data.get('especialidades_actuales')
                provincia_busqueda = data.get('provincia_busqueda')
                ciudad_busqueda = data.get('ciudad_busqueda')
                user_data = data.get('user_data')
                user_id = data.get('user_id')
                id_token = data.get('id_token')
                refresh_token = data.get('refresh_token')

                print(f"Sesion cargada: {path}")
                return True

        except Exception as e:
            print(f"ERROR cargando sesion desde {path}: {e}")

    return False


def limpiar():
    """Limpia sesion en memoria y en disco"""
    global current_user, current_consulta_id, pending_uid, pending_email
    global abogado_registrando_uid, monto_suscripcion, especialidades_abogado
    global area_legal, abogado_seleccionado, estado_abogado, tipo_servicio
    global pago_pending_abogado_uid, pago_pending_abogado_email
    global pago_pending_cliente_uid, pago_pending_cliente_email, pago_pending_precio
    global pago_external_reference, pago_preference_id, pago_init_point
    global pago_tipo, pago_monto, especialidad_a_agregar, especialidades_actuales
    global provincia_busqueda, ciudad_busqueda, user_data, user_id, id_token, refresh_token

    current_user = None
    current_consulta_id = None
    user_data = None
    user_id = None
    id_token = None
    refresh_token = None
    pending_uid = None
    pending_email = None
    abogado_registrando_uid = None
    monto_suscripcion = 55000
    especialidades_abogado = []
    area_legal = None
    abogado_seleccionado = None
    estado_abogado = None
    tipo_servicio = None
    pago_pending_abogado_uid = None
    pago_pending_abogado_email = None
    pago_pending_cliente_uid = None
    pago_pending_cliente_email = None
    pago_pending_precio = None
    pago_external_reference = None
    pago_preference_id = None
    pago_init_point = None
    pago_tipo = None
    pago_monto = None
    especialidad_a_agregar = None
    especialidades_actuales = None
    provincia_busqueda = None
    ciudad_busqueda = None

    for path in _session_paths():
        try:
            if os.path.exists(path):
                os.remove(path)
                print(f"Sesion limpiada: {path}")
        except Exception as e:
            print(f"ERROR limpiando sesion en {path}: {e}")


# =========================================================
# SET SESSION
# =========================================================

def refrescar_id_token():
    """Pide a Firebase un id_token fresco usando el refresh_token guardado.

    Los id_token de Firebase vencen a la hora. session.id_token se guarda una
    sola vez al loguearse y nunca se renovaba -- pasada esa hora, cualquier
    accion de administrador (via la Edge Function admin-actions, que valida
    el id_token contra Firebase) fallaba en silencio con un error generico
    ("Error al guardar en Supabase. Verifica conexion y permisos"), sin decir
    la razon real (confirmado 2026-08-26: admin-actions devuelve "Token de
    Firebase invalido o expirado", pero el cliente solo mostraba el mensaje
    generico). Llamar esto antes de cualquier accion de admin evita el
    problema sin tener que detectar si el token esta vencido -- simplemente
    siempre pide uno fresco."""
    global id_token, refresh_token
    if not refresh_token:
        return id_token
    try:
        import firebase_auth
        ok, token_data, _error = firebase_auth.refrescar_id_token(refresh_token)
        if ok and token_data and token_data.get("id_token"):
            id_token = token_data.get("id_token")
            refresh_token = token_data.get("refresh_token") or refresh_token
            guardar()
    except Exception as e:
        print(f"ERROR refrescando id_token: {e}")
    return id_token


def iniciar_sesion(user):
    global current_user, user_data, user_id, id_token, refresh_token
    current_user = user
    user_data = user
    if user:
        user_id = user.get("uid")
        id_token = user.get("idToken")
        refresh_token = user.get("refreshToken", refresh_token)
    else:
        user_id = None
        id_token = None
        refresh_token = None
    guardar()  # FIX: Guardar automaticamente al iniciar sesion


# =========================================================
# CONSULTA
# =========================================================

def set_consulta_id(consulta_id):
    global current_consulta_id
    current_consulta_id = consulta_id
    guardar()  # FIX: Guardar automaticamente


def get_consulta_id():
    global current_consulta_id
    return current_consulta_id


# =========================================================
# LOGOUT
# =========================================================

def cerrar_sesion():
    limpiar()  # FIX: Limpiar archivo tambien


# =========================================================
# CREDENCIALES RECORDADAS (login)
# =========================================================
# Archivo APARTE de la sesion, a proposito: cerrar_sesion()/limpiar() borran
# el token y el usuario activo, pero el usuario igual quiere que la proxima
# vez que abra la app el email/contrasena ya esten cargados en el login, sin
# tener que volver a escribirlos. Si esto viviera en el mismo archivo de
# sesion, un logout normal lo borraria tambien.

CREDENCIALES_FILENAME = '.legalapp_credenciales.json'


def _credenciales_paths():
    paths = []

    try:
        from kivy.app import App
        app = App.get_running_app()
        if app and app.user_data_dir:
            paths.append(os.path.join(app.user_data_dir, CREDENCIALES_FILENAME))
    except Exception:
        pass

    if platform != "android":
        paths.append(os.path.join(os.path.expanduser('~'), CREDENCIALES_FILENAME))

    unique = []
    for path in paths:
        if path and path not in unique:
            unique.append(path)
    return unique


def _guardar_datos_credenciales(data):
    for path in _credenciales_paths():
        try:
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            with open(path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"ERROR guardando credenciales en {path}: {e}")


def _cargar_datos_credenciales():
    for path in _credenciales_paths():
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"ERROR cargando credenciales desde {path}: {e}")
    return {}


def guardar_credenciales(email, password):
    """Si el dispositivo tiene huella digital configurada, la contrasena se
    cifra con una clave del Android Keystore (nunca queda en texto plano en
    disco). Si no hay huella disponible (celular sin sensor, o no es
    Android), cae al mismo texto plano de antes -- sigue siendo mejor que
    obligar a re-escribir la contrasena cada vez."""
    try:
        import biometria
        cifrada = biometria.cifrar(password) if biometria.huella_disponible() else None
    except Exception:
        cifrada = None

    if cifrada:
        data = {'email': email, 'password_cifrada': cifrada}
    else:
        data = {'email': email, 'password': password}
    _guardar_datos_credenciales(data)


def cargar_email_guardado():
    """El email nunca esta cifrado (no es un dato sensible) -- siempre se
    puede prellenar de una, sin esperar ninguna huella."""
    return _cargar_datos_credenciales().get('email', '') or ''


def hay_password_con_huella():
    return bool(_cargar_datos_credenciales().get('password_cifrada'))


def cargar_password_plano():
    """Solo para cuando la contrasena se guardo SIN cifrar (dispositivo sin
    huella al momento de loguearse). Si esta cifrada, esto devuelve ''."""
    return _cargar_datos_credenciales().get('password', '') or ''


def cargar_password_con_huella(on_resultado):
    """Dispara el prompt de huella y llama on_resultado(password_o_None).
    Nunca deja al caller esperando -- ante cualquier error, cancelacion o
    fallo, on_resultado(None) se llama igual."""
    cifrada = _cargar_datos_credenciales().get('password_cifrada')
    if not cifrada:
        on_resultado(None)
        return
    try:
        import biometria
        biometria.descifrar_con_huella(cifrada, on_resultado)
    except Exception as e:
        print(f"ERROR cargar_password_con_huella: {e}")
        on_resultado(None)


def borrar_credenciales():
    for path in _credenciales_paths():
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"ERROR borrando credenciales en {path}: {e}")
