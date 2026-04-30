import os
AVATAR_DEFAULT = "assets/avatar_default.png"
def get_avatar_source(foto_path):
    if foto_path and os.path.isfile(foto_path):
        return foto_path
    return AVATAR_DEFAULT
