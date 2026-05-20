def verificar_codigo(instance):
    print(f"DEBUG - Código ingresado: '{txt.text}'")
    print(f"DEBUG - Longitud: {len(txt.text)}")
    print(f"DEBUG - Comparación: {txt.text == 'LegalAdmin2024'}")

    if txt.text == 'LegalAdmin2024':
        popup.dismiss()
        self.manager.current = 'admin_panel'
    else:
        lbl.text = f'Código incorrecto. Ingresaste: {txt.text}'
        lbl.color = (0.9, 0.2, 0.2, 1)