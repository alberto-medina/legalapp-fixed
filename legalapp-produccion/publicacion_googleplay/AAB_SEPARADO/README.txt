GOOGLE PLAY - BUILD AAB SEPARADO

Objetivo:
- generar el .aab sin tocar el flujo estable del APK
- usar esta carpeta como referencia de Google Play
- mantener Uptodown / APK fuera de riesgo

Regla:
- NO cambiar el build estable APK por el de AAB
- el AAB se genera en una copia separada del proyecto

Idea de trabajo:
1. tomar como fuente la base estable de:
   C:\legalapp-fixed\legalapp-produccion
2. copiarla a una carpeta separada en Ubuntu:
   /home/eto_/legalapp-googleplay-build
3. en esa copia, cambiar solo:
   - android.release_artifact = aab
   - android.targetapi = 35
4. compilar AAB desde esa copia

Resultado:
- APK estable sigue intacto
- AAB de Google Play sale por carril aparte
