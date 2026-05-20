# session.py - guarda datos del usuario logueado (ahora dict de Firebase)
current_user = None
current_consulta_id = None
abogado_seleccionado = None
estado_abogado = None
tipo_servicio = None
area_legal = None

# Variables para verificación de email pendiente
pending_uid = None
pending_email = None


def get_uid():
    return current_user.get('uid') if current_user else None


def get_email():
    return current_user.get('email') if current_user else None


def get_rol():
    return current_user.get('rol') if current_user else None


def get_nombre():
    return current_user.get('username', '') or current_user.get('nombre', '') if current_user else ''


def es_abogado():
    return get_rol() == 'abogado'


def es_cliente():
    return get_rol() == 'cliente'