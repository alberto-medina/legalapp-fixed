import os

AVATAR_DEFAULT = "assets/avatar_default.png"


def _avatar_local_por_email(email):
    if not email:
        return None
    safe = str(email).replace("@", "_").replace(".", "_")
    base = os.path.join("assets", "fotos")
    if not os.path.isdir(base):
        return None

    candidatos = []
    prefijo = f"perfil_{safe}".lower()
    for nombre in os.listdir(base):
        nombre_lower = nombre.lower()
        if not nombre_lower.startswith(prefijo):
            continue
        if not any(nombre_lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
            continue
        path = os.path.join(base, nombre)
        if os.path.isfile(path):
            candidatos.append(path)

    if not candidatos:
        return None

    candidatos.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return os.path.abspath(candidatos[0])


def get_avatar_source(foto_path, email=None):
    if foto_path and str(foto_path).startswith(("http://", "https://")):
        return str(foto_path)

    if foto_path and os.path.isfile(foto_path):
        return os.path.abspath(foto_path)

    local_email = _avatar_local_por_email(email)
    if local_email:
        return local_email

    return AVATAR_DEFAULT


def set_avatar_image(widget, foto_path, email=None, force=False):
    source = get_avatar_source(foto_path, email)
    actual = str(getattr(widget, "source", "") or "")

    if not force and actual == source:
        return source

    widget.source = source
    try:
        widget.reload()
    except Exception:
        pass
    return source
