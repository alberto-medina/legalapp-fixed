[app]

title = LegalApp
package.name = legalapp
package.domain = org.legalapp

source.dir = .

source.include_exts = py,png,jpg,kv,atlas,db

version = 0.1

requirements = python3,kivy,sqlite3,plyer

orientation = portrait

fullscreen = 0

android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = True

android.debug_artifact = apk


[buildozer]

log_level = 2
warn_on_root = 1
