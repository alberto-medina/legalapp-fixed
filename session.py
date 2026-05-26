# session.py

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

# Ubicacion busqueda cliente
provincia_busqueda = None
ciudad_busqueda = None

# Compatibilidad con pantallas viejas
user_data = None
user_id = None
id_token = None

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
# SET SESSION
# =========================================================

def iniciar_sesion(user):
    global current_user, user_data, user_id, id_token
    current_user = user
    user_data = user
    if user:
        user_id = user.get("uid")
        id_token = user.get("idToken")
    else:
        user_id = None
        id_token = None


# =========================================================
# CONSULTA
# =========================================================

def set_consulta_id(consulta_id):
    global current_consulta_id
    current_consulta_id = consulta_id


def get_consulta_id():
    global current_consulta_id
    return current_consulta_id


# =========================================================
# LOGOUT
# =========================================================

def cerrar_sesion():
    global current_user, current_consulta_id, user_data
    global user_id, id_token, pending_uid, pending_email
    global abogado_registrando_uid, monto_suscripcion
    global especialidades_abogado, area_legal
    global abogado_seleccionado, estado_abogado, tipo_servicio
    global provincia_busqueda, ciudad_busqueda

    current_user = None
    current_consulta_id = None
    user_data = None
    user_id = None
    id_token = None
    pending_uid = None
    pending_email = None
    abogado_registrando_uid = None
    monto_suscripcion = 55000
    especialidades_abogado = []
    area_legal = None
    abogado_seleccionado = None
    estado_abogado = None
    tipo_servicio = None
    provincia_busqueda = None
    ciudad_busqueda = None