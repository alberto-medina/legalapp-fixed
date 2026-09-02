[app]

title = Legal App

package.name = legalapp
package.domain = com.legalapp.app

version = 1.1.10
android.numeric_version = 120

source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,webp,ttf,otf,json,xml
source.exclude_patterns = firebase.json,firestore.indexes.json,firestore.rules,*.BACKUP.py,legal_app.db,.env,.env.example,*.pyc,__pycache__,*.spec,*.md,*.bak,*.log,*.txt,*.zip,*.apk,tests/*,.git/*,.idea/*,.buildozer/*,bin/*,backups/*,functions/*,supabase/*,scripts/*,serviceAccountKey.json,legalapp-release.keystore

requirements = python3,kivy,kivymd,pillow,requests,pyjnius,certifi,urllib3,charset-normalizer,idna,plyer,android

orientation = portrait

android.permissions = INTERNET,CAMERA,RECORD_AUDIO,READ_EXTERNAL_STORAGE,READ_MEDIA_IMAGES,READ_MEDIA_AUDIO,VIBRATE,WAKE_LOCK,RECEIVE_BOOT_COMPLETED,POST_NOTIFICATIONS

android.minapi = 26
android.api = 36
android.ndk = 25c
android.sdk_build_tools_version = 36.0.0

android.release_artifact = apk

android.release_keystore = legalapp-release.keystore
android.release_keyalias = legalapp

android.network_security_config = network_security_config.xml

android.gradle_dependencies = com.google.firebase:firebase-messaging:23.4.0

android.gradle_plugins = com.google.gms.google-services

android.enable_androidx = True

p4a.branch = master

icon.filename = assets/icon_512.png
presplash.filename = assets/splash_1080.png

log_level = 2
warn_on_root = 1

[buildozer]
log_level = 2
warn_on_root = 1



