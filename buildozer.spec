[app]

title = Legal App
package.name = legalapp
package.domain = com.legalapp.app
version = 1.0.1

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,svg,ttf,otf,json,sql,xml,txt
source.exclude_patterns = legal_app.db,.env,*.pyc,__pycache__,*.spec,tests/*,*.md

requirements = python3,kivy,kivymd,pillow,requests,supabase,pyjnius,certifi,urllib3,charset-normalizer,idna,plyer,android

orientation = portrait

android.permissions = INTERNET,CAMERA,RECORD_AUDIO,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,VIBRATE,WAKE_LOCK,RECEIVE_BOOT_COMPLETED,POST_NOTIFICATIONS

android.minapi = 26
android.targetapi = 34
android.ndk = 25c

android.release_artifact = apk

android.network_security_config = network_security_config.xml

android.gradle_dependencies = com.google.firebase:firebase-messaging:23.4.0,com.google.firebase:firebase-analytics:21.5.0

android.gradle_plugins = com.google.gms.google-services

android.enable_androidx = True

p4a.branch = develop

icon.filename = assets/icon_512.png
presplash.filename = assets/splash_1080.png

log_level = 2
warn_on_root = 1

[buildozer]
log_level = 2
warn_on_root = 1