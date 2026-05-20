from firebase_functions import https_fn
from firebase_functions.options import set_global_options
from firebase_admin import initialize_app, firestore
import requests

# Limitar instancias para control de costos (Spark plan)
set_global_options(max_instances=10)

# Inicializar Firebase Admin
initialize_app()
db = firestore.client()

# ============================================================
# CREDENCIALES MERCADOPAGO
# ============================================================
MP_ACCESS_TOKEN = "APP_USR-8223001580318083-051723-d41d4a65e646511dc89ec94555cfb6a3-3369360530"
MP_API_URL = "https://api.mercadopago.com/v1/payments/"


@https_fn.on_request()
def mp_webhook(req: https_fn.Request) -> https_fn.Response:
    """
    Recibe notificaciones de MercadoPago cuando un pago cambia de estado.
    URL: https://us-central1-legalapp-pro.cloudfunctions.net/mp_webhook
    """

    # Solo aceptar POST
    if req.method != "POST":
        return https_fn.Response("OK", status=200)

    try:
        data = req.get_json(silent=True) or {}

        # MP envia 'data.id' con el payment_id
        payment_id = data.get("data", {}).get("id")
        tipo = data.get("type")  # 'payment'

        if not payment_id or tipo != "payment":
            return https_fn.Response("OK", status=200)

        # Consultar a MP el estado del pago
        headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}"}
        resp = requests.get(f"{MP_API_URL}{payment_id}", headers=headers, timeout=10)

        if resp.status_code != 200:
            print(f"ERROR consultando MP: {resp.status_code}")
            return https_fn.Response("OK", status=200)

        payment_data = resp.json()
        status = payment_data.get("status")
        external_reference = payment_data.get("external_reference")

        if status != "approved" or not external_reference:
            return https_fn.Response("OK", status=200)

        # Buscar consulta por external_reference
        consultas_ref = db.collection("consultas")
        query = consultas_ref.where("external_reference", "==", external_reference).limit(1)
        docs = query.get()

        if not docs:
            print(f"Consulta no encontrada: {external_reference}")
            return https_fn.Response("OK", status=200)

        doc = docs[0]
        consulta_id = doc.id
        consulta_data = doc.to_dict()

        # Solo actualizar si esta pendiente
        if consulta_data.get("estado") == "pendiente":
            consultas_ref.document(consulta_id).update({
                "estado": "pagado",
                "payment_id": payment_id,
                "pagado_at": firestore.SERVER_TIMESTAMP
            })
            print(f"PAGO CONFIRMADO: consulta={consulta_id}, payment={payment_id}")

        return https_fn.Response("OK", status=200)

    except Exception as e:
        print(f"ERROR webhook: {e}")
        return https_fn.Response("OK", status=200)