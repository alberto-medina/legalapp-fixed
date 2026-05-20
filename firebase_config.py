import firebase_admin
from firebase_admin import credentials, firestore, auth, storage, messaging
from firebase_admin.exceptions import FirebaseError
from google.cloud.firestore_v1 import Increment
import requests
import os
import re
import random
from datetime import datetime, timedelta

# ========== EMAIL CON GMAIL SMTP ==========
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GMAIL_USER = os.environ.get("GMAIL_USER", "beto77am@gmail.com")
GMAIL_PASS = os.environ.get("GMAIL_PASS", "gopt bryk mkfw mbvd")


def enviar_email_smtp(destino, asunto, html):
    """Envia email usando Gmail SMTP"""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = asunto
    msg['From'] = f"LegalApp <{GMAIL_USER}>"
    msg['To'] = destino

    msg.attach(MIMEText(html, 'html'))

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(GMAIL_USER, GMAIL_PASS)
    server.sendmail(GMAIL_USER, destino, msg.as_string())
    server.quit()


# ========== INICIALIZAR FIREBASE ==========
SERVICE_ACCOUNT_FILE = "serviceAccountKey.json"
GOOGLE_SERVICES_FILE = "google-services.json"

project_id = "legalapp-pro"
cred = None

if not firebase_admin._apps:
    try:
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'legalapp-pro.appspot.com'
            })
            print("Firebase conectado con Service Account")
        elif os.path.exists(GOOGLE_SERVICES_FILE):
            print("Usando google-services.json - SOLO para desarrollo")
            import json
            with open(GOOGLE_SERVICES_FILE) as f:
                gs_data = json.load(f)
                project_id = gs_data.get('project_info', {}).get('project_id', 'legalapp-pro')
            firebase_admin.initialize_app(options={
                'projectId': project_id,
                'storageBucket': 'legalapp-pro.appspot.com'
            })
            print("Firebase inicializado en modo DESARROLLO")
        else:
            print("No se encontro ningun archivo de credenciales")
            raise FileNotFoundError("Falta serviceAccountKey.json o google-services.json")
    except Exception as e:
        print(f"Error Firebase: {e}")

# ========== CONECTAR A FIRESTORE ==========
try:
    db = firestore.client()
    db._database = "default"
    bucket = storage.bucket()
except Exception as e:
    print(f"Error conectando a Firestore/Storage: {e}")
    db = None
    bucket = None

API_KEY = os.environ.get("FIREBASE_API_KEY", "AIzaSyBmBKc5MkGmWBjeEa2YPOqCKa9Ve3fxWbE")


# ========== VALIDACIONES DE SEGURIDAD ==========
def validar_email(email):
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None


def validar_password(password):
    if len(password) < 8:
        return False, "Minimo 8 caracteres"
    if not re.search(r'[A-Z]', password):
        return False, "Debe tener al menos una mayuscula"
    if not re.search(r'[a-z]', password):
        return False, "Debe tener al menos una minuscula"
    if not re.search(r'\d', password):
        return False, "Debe tener al menos un numero"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Debe tener al menos un caracter especial"
    return True, "OK"


def validar_dni(dni):
    if not dni:
        return True, "OK"
    if re.match(r'^\d{7,8}$', dni):
        return True, "OK"
    return False, "DNI invalido (7-8 digitos)"


def validar_telefono(telefono):
    if not telefono:
        return True, "OK"
    limpio = re.sub(r'[\s\-\.]', '', telefono)
    if re.match(r'^\+?54\d{10,12}$', limpio) or re.match(r'^0?\d{10}$', limpio):
        return True, "OK"
    return False, "Telefono invalido"


# ========== EMAIL VERIFICATION ==========
def enviar_codigo_verificacion(email, uid):
    codigo = str(random.randint(100000, 999999))
    expira = datetime.utcnow() + timedelta(minutes=30)
    db.collection('verificaciones').document(uid).set({
        'email': email,
        'codigo': codigo,
        'creado': firestore.SERVER_TIMESTAMP,
        'expira': expira,
        'intentos': 0,
        'verificado': False
    })

    try:
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
            <div style="background: #3d2b8c; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="margin: 0; font-size: 28px;">LEGAL APP</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">Verificacion de cuenta</p>
            </div>
            <div style="background: white; padding: 40px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #3d2b8c;">Hola!</h2>
                <p style="color: #555; font-size: 16px;">
                    Gracias por registrarte en <strong>LegalApp</strong>. Para activar tu cuenta, ingresa el siguiente codigo:
                </p>
                <div style="background: #f0eef7; border-left: 4px solid #3d2b8c; padding: 20px; margin: 30px 0; text-align: center;">
                    <span style="font-size: 36px; font-weight: bold; color: #3d2b8c; letter-spacing: 8px;">{codigo}</span>
                </div>
                <p style="color: #888; font-size: 14px;">Este codigo expira en <strong>30 minutos</strong>.</p>
            </div>
        </div>
        """
        enviar_email_smtp(email, "Codigo de verificacion - LegalApp", html)
        print(f"Email enviado a {email}")
        return True, codigo
    except Exception as e:
        print(f"Error enviando email: {e}")
        return True, codigo


def verificar_email_con_codigo(uid, codigo_ingresado):
    doc_ref = db.collection('verificaciones').document(uid)
    doc = doc_ref.get()
    if not doc.exists:
        return False, "No hay codigo pendiente"
    data = doc.to_dict()
    expira = data.get('expira')
    if expira:
        if hasattr(expira, 'replace'):
            expira_naive = expira.replace(tzinfo=None)
        else:
            expira_naive = expira
        if expira_naive < datetime.utcnow():
            return False, "Codigo expirado. Solicita uno nuevo."
    if data.get('codigo') == codigo_ingresado:
        db.collection('users').document(uid).update({'email_verified': True})
        doc_ref.update({
            'verificado': True,
            'verificado_en': firestore.SERVER_TIMESTAMP
        })
        return True, "Email verificado correctamente"
    intentos = data.get('intentos', 0) + 1
    doc_ref.update({'intentos': intentos})
    if intentos >= 3:
        return False, "Demasiados intentos. Solicita un nuevo codigo."
    return False, f"Codigo incorrecto. Intentos restantes: {3 - intentos}"


def reenviar_codigo_verificacion(email, uid):
    db.collection('verificaciones').document(uid).delete()
    return enviar_codigo_verificacion(email, uid)


# ========== AUTH ==========
def crear_usuario(email, password, nombre, rol="cliente", telefono="", datos_extra=None):
    try:
        if not validar_email(email):
            return False, None, "Email invalido"
        ok_pass, msg_pass = validar_password(password)
        if not ok_pass:
            return False, None, f"Contrasena insegura: {msg_pass}"
        ok_dni, msg_dni = validar_dni(datos_extra.get('dni', '') if datos_extra else '')
        if not ok_dni:
            return False, None, msg_dni
        ok_tel, msg_tel = validar_telefono(telefono)
        if not ok_tel:
            return False, None, msg_tel
        user = auth.create_user(email=email, password=password, display_name=nombre)
        user_data = {
            'username': nombre,
            'email': email,
            'rol': rol,
            'telefono': telefono,
            'saldo': 0.0,
            'estado_abogado': 'disponible' if rol == 'abogado' else '',
            'matricula': datos_extra.get('matricula', '') if datos_extra else '',
            'experiencia': datos_extra.get('experiencia', '') if datos_extra else '',
            'descripcion': datos_extra.get('descripcion', '') if datos_extra else '',
            'especialidad': datos_extra.get('especialidad', '') if datos_extra else '',
            'dni': datos_extra.get('dni', '') if datos_extra else '',
            'direccion': datos_extra.get('direccion', '') if datos_extra else '',
            'cuenta_bancaria': '',
            'foto_url': '',
            'fcm_token': '',
            'email_verified': False,
            'creado': firestore.SERVER_TIMESTAMP
        }
        db.collection('users').document(user.uid).set(user_data)
        return True, user.uid, None
    except FirebaseError as e:
        return False, None, str(e)


def crear_abogado_manual(email, password, nombre, telefono, matricula, especialidad, experiencia, descripcion):
    try:
        if not validar_email(email):
            return False, None, "Email invalido"
        ok_pass, msg_pass = validar_password(password)
        if not ok_pass:
            return False, None, f"Contrasena insegura: {msg_pass}"
        user = auth.create_user(email=email, password=password, display_name=nombre)
        user_data = {
            'username': nombre,
            'email': email,
            'rol': 'abogado',
            'telefono': telefono,
            'saldo': 0.0,
            'estado_abogado': 'disponible',
            'matricula': matricula,
            'experiencia': experiencia,
            'descripcion': descripcion,
            'especialidad': especialidad,
            'dni': '',
            'direccion': '',
            'cuenta_bancaria': '',
            'foto_url': '',
            'fcm_token': '',
            'email_verified': True,
            'creado': firestore.SERVER_TIMESTAMP
        }
        db.collection('users').document(user.uid).set(user_data)
        return True, user.uid, None
    except FirebaseError as e:
        return False, None, str(e)


def login_usuario(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        if response.status_code == 200:
            uid = data['localId']
            id_token = data.get('idToken')
            user_data = obtener_usuario(uid)
            if user_data:
                user_data['uid'] = uid
                user_data['idToken'] = id_token
                return True, user_data, None
            return False, None, "Usuario no encontrado"
        error = data.get('error', {}).get('message', 'Error')
        return False, None, error
    except Exception as e:
        return False, None, str(e)


# ========== USUARIOS ==========
def obtener_usuario(uid):
    doc = db.collection('users').document(uid).get()
    if doc.exists:
        data = doc.to_dict()
        data['uid'] = uid
        return data
    return None


def obtener_usuario_por_email(email):
    query = db.collection('users').where('email', '==', email).limit(1).get()
    for doc in query:
        data = doc.to_dict()
        data['uid'] = doc.id
        return data
    return None


def actualizar_usuario(uid, datos):
    db.collection('users').document(uid).update(datos)


def listar_abogados(disponibles=True):
    query = db.collection('users').where('rol', '==', 'abogado')
    if disponibles:
        query = query.where('estado_abogado', '==', 'disponible')
    docs = query.stream()
    return [doc.to_dict() | {'uid': doc.id} for doc in docs]


# ========== CONSULTAS ==========
PRECIOS_CONSULTA = {"chat": 1000.0, "video": 3000.0, "urgente": 5000.0}
COMISION_PLATAFORMA = 0.20  # 20% para la plataforma


def crear_consulta(cliente_uid, abogado_uid, tipo_servicio, descripcion=""):
    consulta_ref = db.collection('consultas').document()
    cliente = obtener_usuario(cliente_uid)
    abogado = obtener_usuario(abogado_uid)
    precio = PRECIOS_CONSULTA.get(tipo_servicio, 1000.0)
    consulta_ref.set({
        'cliente_uid': cliente_uid,
        'cliente_email': cliente.get('email', '') if cliente else '',
        'abogado_uid': abogado_uid,
        'abogado_email': abogado.get('email', '') if abogado else '',
        'tipo_servicio': tipo_servicio,
        'descripcion': descripcion,
        'estado': 'pendiente',
        'precio': precio,
        'monto': precio,
        'fecha_creacion': firestore.SERVER_TIMESTAMP,
        'created_at': firestore.SERVER_TIMESTAMP,
        'fecha_finalizacion': None,
        'ultimo_mensaje': '',
        'ultimo_mensaje_timestamp': None
    })
    return consulta_ref.id


def obtener_consultas_usuario(uid, rol):
    query = db.collection('consultas').where('cliente_uid' if rol == 'cliente' else 'abogado_uid', '==', uid)
    query = query.order_by('fecha_creacion', direction=firestore.Query.DESCENDING)
    return [(doc.id, doc.to_dict()) for doc in query.stream()]


def obtener_consulta(consulta_id):
    doc = db.collection('consultas').document(consulta_id).get()
    if doc.exists:
        data = doc.to_dict()
        data['id'] = doc.id
        return data
    return None


def actualizar_estado_consulta(consulta_id, nuevo_estado):
    datos = {'estado': nuevo_estado}
    if nuevo_estado == 'finalizado':
        datos['fecha_finalizacion'] = firestore.SERVER_TIMESTAMP
    db.collection('consultas').document(consulta_id).update(datos)


def escuchar_consulta(consulta_id, callback):
    """
    Listener en tiempo real para una consulta especifica.
    Se llama cuando cambia el estado (videollamada, finalizado, etc).
    """
    def on_snapshot(doc_snapshot, changes, read_time):
        for doc in doc_snapshot:
            if doc.exists:
                callback(doc.to_dict())

    return db.collection('consultas').document(consulta_id).on_snapshot(on_snapshot)


# ========== PAGOS ==========
def acreditar_honorario(abogado_uid, tipo_servicio):
    monto_total = PRECIOS_CONSULTA.get(tipo_servicio, 1000.0)
    comision = round(monto_total * COMISION_PLATAFORMA, 2)  # 20% plataforma
    monto_neto = round(monto_total - comision, 2)  # 80% abogado
    db.collection('users').document(abogado_uid).update({'saldo': Increment(monto_neto)})
    registrar_transaccion(abogado_uid, 'ingreso', monto_neto, f'Honorario {tipo_servicio}')
    return monto_neto, comision


def registrar_transaccion(uid, tipo, monto, descripcion):
    db.collection('users').document(uid).collection('transacciones').document().set({
        'tipo': tipo, 'monto': monto, 'descripcion': descripcion,
        'estado': 'completado', 'fecha': firestore.SERVER_TIMESTAMP
    })


def pagar_consulta(cliente_uid, consulta_id):
    consulta = obtener_consulta(consulta_id)
    if not consulta: return False, "No existe"
    precio = consulta.get('precio', 0)
    abogado_uid = consulta.get('abogado_uid')
    cliente = obtener_usuario(cliente_uid)
    if cliente.get('saldo', 0) < precio: return False, "Saldo insuficiente"
    db.collection('users').document(cliente_uid).update({'saldo': Increment(-precio)})
    registrar_transaccion(cliente_uid, 'pago_consulta', -precio, 'Pago')
    acreditar_honorario(abogado_uid, consulta['tipo_servicio'])
    actualizar_estado_consulta(consulta_id, 'pagado')
    return True, None


def solicitar_retiro(abogado_uid, monto_bruto, cuenta=None):
    abogado = obtener_usuario(abogado_uid)
    if not abogado: return False, "No encontrado", 0
    saldo = abogado.get('saldo', 0)
    cuenta_dest = cuenta or abogado.get('cuenta_bancaria', '')
    if not cuenta_dest: return False, "Falta CBU/alias", 0
    if monto_bruto <= 0: return False, "Monto > 0", 0
    if monto_bruto > saldo: return False, f"Saldo: ${saldo:,.0f}", 0
    db.collection('users').document(abogado_uid).update({'saldo': Increment(-monto_bruto)})
    from datetime import datetime
    db.collection('retiros').add({
        'abogado_uid': abogado_uid, 'abogado_email': abogado.get('email', ''),
        'monto_bruto': monto_bruto, 'comision_plataforma': 0, 'monto_neto': monto_bruto,
        'cuenta_destino': cuenta_dest, 'estado': 'pendiente',
        'fecha': datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    return True, f"Retiro ${monto_bruto:,.0f} solicitado", monto_bruto


# ========== RETIROS ADMIN ==========
def listar_retiros_pendientes():
    """Lista todos los retiros con estado 'pendiente'"""
    query = db.collection('retiros').where('estado', '==', 'pendiente').order_by('fecha', direction=firestore.Query.DESCENDING)
    return [doc.to_dict() | {'id': doc.id} for doc in query.stream()]


def procesar_retiro(retiro_id, admin_uid):
    """Marca un retiro como pagado y notifica al abogado"""
    try:
        retiro_ref = db.collection('retiros').document(retiro_id)
        retiro = retiro_ref.get().to_dict()

        if not retiro or retiro.get('estado') != 'pendiente':
            return False, "Retiro no encontrado o ya procesado"

        abogado_uid = retiro['abogado_uid']
        monto = retiro['monto_bruto']

        # Actualizar retiro
        retiro_ref.update({
            'estado': 'pagado',
            'pagado_at': firestore.SERVER_TIMESTAMP,
            'admin_uid': admin_uid
        })

        # Registrar transacción de retiro
        registrar_transaccion(abogado_uid, 'retiro', -monto, f'Retiro procesado ${monto:,.2f}')

        # Notificar al abogado
        enviar_notificacion_a_usuario(
            abogado_uid,
            "Retiro procesado",
            f"Se te transfirio ${monto:,.2f} a tu cuenta. Gracias por usar LegalApp.",
            {'tipo': 'retiro_procesado'}
        )

        return True, f"Retiro de ${monto:,.2f} procesado correctamente"
    except Exception as e:
        return False, str(e)


# ========== CHAT ==========
def enviar_mensaje(consulta_id, emisor_uid, texto, tipo='texto'):
    mensaje_ref = db.collection('consultas').document(consulta_id).collection('mensajes').document()
    mensaje_ref.set({
        'emisor_uid': emisor_uid,
        'emisor_email': obtener_usuario(emisor_uid).get('email', ''),
        'texto': texto, 'mensaje': texto, 'tipo': tipo,
        'timestamp': firestore.SERVER_TIMESTAMP, 'leido': False
    })
    db.collection('consultas').document(consulta_id).update({
        'ultimo_mensaje': texto, 'ultimo_mensaje_timestamp': firestore.SERVER_TIMESTAMP
    })
    return mensaje_ref.id


def obtener_mensajes(consulta_id, limite=100):
    query = db.collection('consultas').document(consulta_id).collection('mensajes').order_by('timestamp').limit(limite)
    return [doc.to_dict() | {'id': doc.id} for doc in query.stream()]


def escuchar_mensajes(consulta_id, callback):
    def on_snapshot(doc_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == 'ADDED':
                callback(change.document.to_dict() | {'id': change.document.id})

    return db.collection('consultas').document(consulta_id).collection('mensajes').on_snapshot(on_snapshot)


# ========== RESENAS ==========
def guardar_resena(consulta_id, abogado_email, cliente_email, puntaje, comentario):
    from datetime import datetime
    db.collection('resenas').document(str(consulta_id)).set({
        'consulta_id': consulta_id, 'abogado_email': abogado_email,
        'cliente_email': cliente_email, 'puntaje': puntaje,
        'comentario': comentario, 'fecha': datetime.now().strftime("%Y-%m-%d %H:%M")
    })


def tiene_resena(consulta_id):
    return db.collection('resenas').document(str(consulta_id)).get().exists


def obtener_resenas_abogado(abogado_email):
    return [doc.to_dict() for doc in db.collection('resenas').where('abogado_email', '==', abogado_email).stream()]


# ========== NOTIFICACIONES ==========
def enviar_notificacion_a_usuario(uid_destino, titulo, cuerpo, datos_extra=None):
    try:
        user = obtener_usuario(uid_destino)
        token = user.get('fcm_token') if user else None
        if not token: return False
        message = messaging.Message(
            notification=messaging.Notification(title=titulo, body=cuerpo),
            data=datos_extra or {}, token=token,
            android=messaging.AndroidConfig(priority='high',
                                            notification=messaging.AndroidNotification(channel_id='default_channel',
                                                                                       sound='default'))
        )
        messaging.send(message)
        return True
    except Exception as e:
        print(f"Error notif: {e}")
        return False


def notificar_nuevo_mensaje(consulta_id, emisor_uid, texto):
    consulta = obtener_consulta(consulta_id)
    if not consulta: return
    receptor_uid = consulta['abogado_uid'] if emisor_uid == consulta['cliente_uid'] else consulta['cliente_uid']
    enviar_notificacion_a_usuario(receptor_uid, "Nuevo mensaje", texto[:50] + "...",
                                  {'tipo': 'chat', 'consulta_id': consulta_id})


def notificar_nueva_consulta(abogado_uid, tipo_servicio, precio):
    enviar_notificacion_a_usuario(abogado_uid, "Nueva consulta!", f"{tipo_servicio} - ${precio}",
                                  {'tipo': 'nueva_consulta'})


def notificar_consulta_pagada(abogado_uid, tipo_servicio, precio):
    enviar_notificacion_a_usuario(
        abogado_uid,
        "Nueva consulta pagada",
        f"Tenes una consulta {tipo_servicio} de ${precio} esperando tu atencion. Aceptala para empezar.",
        {'tipo': 'consulta_pagada', 'accion': 'abrir_panel'}
    )


def notificar_consulta_aceptada(cliente_uid, tipo_servicio):
    enviar_notificacion_a_usuario(
        cliente_uid,
        "Abogado conectado",
        f"Tu consulta {tipo_servicio} fue aceptada. Ya podes chatear con el abogado.",
        {'tipo': 'consulta_aceptada', 'accion': 'abrir_chat'}
    )


def notificar_consulta_finalizada(cliente_uid):
    enviar_notificacion_a_usuario(
        cliente_uid,
        "Consulta finalizada",
        "El abogado finalizo la consulta. Dejale una reseña.",
        {'tipo': 'consulta_finalizada', 'accion': 'abrir_resena'}
    )


def notificar_videollamada(cliente_uid, consulta_id):
    enviar_notificacion_a_usuario(
        cliente_uid,
        "Videollamada iniciada",
        "El abogado inicio una videollamada. Toca para unirte.",
        {'tipo': 'videollamada', 'consulta_id': consulta_id, 'accion': 'abrir_videollamada'}
    )


# ========== STORAGE ==========
# Limite de tamano para archivos: 2MB
MAX_FILE_SIZE_MB = 2
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def subir_foto_perfil(uid, ruta_imagen):
    """Sube foto de perfil con compresion y limite de tamano"""
    try:
        # Verificar tamano
        tamano = os.path.getsize(ruta_imagen)
        if tamano > MAX_FILE_SIZE_BYTES:
            # Intentar comprimir con PIL
            try:
                from PIL import Image
                img = Image.open(ruta_imagen)
                # Redimensionar si es muy grande
                max_size = (800, 800)
                img.thumbnail(max_size, Image.LANCZOS)
                # Guardar con calidad reducida
                img.save(ruta_imagen, quality=70, optimize=True)
                tamano = os.path.getsize(ruta_imagen)
                if tamano > MAX_FILE_SIZE_BYTES:
                    return False, f"Imagen muy grande. Maximo {MAX_FILE_SIZE_MB}MB despues de comprimir"
            except ImportError:
                return False, f"Imagen muy grande. Maximo {MAX_FILE_SIZE_MB}MB"

        blob = bucket.blob(f"perfiles/{uid}.jpg")
        blob.upload_from_filename(ruta_imagen)
        blob.make_public()
        url = blob.public_url
        actualizar_usuario(uid, {'foto_url': url})
        return True, url
    except Exception as e:
        return False, str(e)


def subir_archivo_chat(consulta_id, ruta_archivo, nombre_archivo):
    """Sube archivo al chat con limite de tamano"""
    try:
        tamano = os.path.getsize(ruta_archivo)
        if tamano > MAX_FILE_SIZE_BYTES:
            return False, f"Archivo muy grande. Maximo {MAX_FILE_SIZE_MB}MB"

        blob = bucket.blob(f"chat/{consulta_id}/{nombre_archivo}")
        blob.upload_from_filename(ruta_archivo)
        blob.make_public()
        return True, blob.public_url
    except Exception as e:
        return False, str(e)


# ========== CREAR ABOGADOS DEMO ==========
def crear_abogados_demo():
    abogados_demo = [
        {
            'email': 'maria.gonzalez@legalapp.demo',
            'password': 'Demo1234!',
            'nombre': 'Dra. Maria Gonzalez',
            'telefono': '+54 9 351 987-6543',
            'matricula': 'MP 12.345',
            'especialidad': 'Derecho Laboral',
            'experiencia': '12 anos de experiencia en juicios laborales, despidos y accidentes de trabajo',
            'descripcion': 'Especialista en derecho laboral y seguridad social. Amplia trayectoria en negociaciones colectivas y mediaciones.'
        },
        {
            'email': 'carlos.rodriguez@legalapp.demo',
            'password': 'Demo1234!',
            'nombre': 'Dr. Carlos Rodriguez',
            'telefono': '+54 9 351 654-3210',
            'matricula': 'MP 56.789',
            'especialidad': 'Derecho Penal',
            'experiencia': '15 anos en defensa criminal y derecho procesal penal',
            'descripcion': 'Especialista en derecho penal y criminologia. Experto en defensa de flagrancias, excarcelaciones y recursos de casacion.'
        },
        {
            'email': 'laura.martinez@legalapp.demo',
            'password': 'Demo1234!',
            'nombre': 'Dra. Laura Martinez',
            'telefono': '+54 9 351 456-7890',
            'matricula': 'MP 98.765',
            'especialidad': 'Derecho Civil y Comercial',
            'experiencia': '10 anos en contratos, danos y sucesiones',
            'descripcion': 'Especialista en derecho civil, comercial y sucesiones. Experta en contratos complejos y resolucion de conflictos patrimoniales.'
        },
        {
            'email': 'juan.perez@legalapp.demo',
            'password': 'Demo1234!',
            'nombre': 'Dr. Juan Perez',
            'telefono': '+54 9 351 789-0123',
            'matricula': 'MP 45.678',
            'especialidad': 'Derecho de Familia',
            'experiencia': '8 anos en divorcios, custodia y alimentos',
            'descripcion': 'Especialista en derecho de familia. Enfoque en mediacion familiar y resolucion pacifica de conflictos de custodia y alimentos.'
        }
    ]

    creados = 0
    for abogado in abogados_demo:
        query = db.collection('users').where('email', '==', abogado['email']).limit(1).get()
        if list(query):
            print(f"Abogado demo ya existe: {abogado['nombre']}")
            continue

        ok, uid, error = crear_abogado_manual(
            email=abogado['email'],
            password=abogado['password'],
            nombre=abogado['nombre'],
            telefono=abogado['telefono'],
            matricula=abogado['matricula'],
            especialidad=abogado['especialidad'],
            experiencia=abogado['experiencia'],
            descripcion=abogado['descripcion']
        )
        if ok:
            print(f"Abogado demo creado: {abogado['nombre']} (UID: {uid})")
            creados += 1
        else:
            print(f"Error creando {abogado['nombre']}: {error}")

    print(f"\nTotal abogados demo creados: {creados}")
    return creados


# ========== DEMO CLIENTE ==========
def crear_usuarios_demo():
    query = db.collection('users').where('email', '==', 'cliente@test.com').limit(1).get()
    if not list(query):
        ok, uid, err = crear_usuario(
            'cliente@test.com',
            'Cliente123!',
            'Cliente Test',
            'cliente',
            '+54 9 351 111-2222',
            {'dni': '30123456', 'direccion': 'Av. Colon 1234, Cordoba'}
        )
        print("Cliente demo" if ok else f"Error: {err}")

    crear_abogados_demo()