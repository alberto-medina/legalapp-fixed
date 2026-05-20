import firebase_config as fb

# Test 1: Enviar notificación a un abogado demo
print("=== TEST NOTIFICACIONES ===")

# Usá el UID de un abogado demo que tenga FCM token
# Si no tiene, primero tenemos que registrar el token desde la app
abogado = fb.obtener_usuario_por_email('maria.gonzalez@legalapp.demo')
if abogado:
    print(f"Abogado: {abogado.get('username')}")
    print(f"FCM Token: {abogado.get('fcm_token', 'NO TIENE')}")

    if abogado.get('fcm_token'):
        ok = fb.enviar_notificacion_a_usuario(
            abogado['uid'],
            "Test LegalApp",
            "Esta es una notificación de prueba"
        )
        print(f"Notificación enviada: {ok}")
    else:
        print("❌ No hay FCM token. Hay que registrarlo desde la app.")
else:
    print("❌ Abogado no encontrado")