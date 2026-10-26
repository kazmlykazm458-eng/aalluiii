[app]
title = العراق
package.name = iraq_sender
package.domain = com.iraq.sender
version = 1.0.0
source.dir = .
source.include_exts = py,png,jpg,jpeg,webp,kv,atlas,ttf,otf
source.include_patterns = assets/fonts/*.ttf,assets/*.png
icon.filename = %(source.dir)s/assets/icon.png

android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, MANAGE_EXTERNAL_STORAGE, FOREGROUND_SERVICE, POST_NOTIFICATIONS, WAKE_LOCK
android.requestLegacyExternalStorage = True
android.archs = arm64-v8a
android.api = 33
android.minapi = 24
android.ndk_api = 24

# تضمين الخط بشكل صريح في assets الـ APK
android.add_assets = assets/fonts/NotoNaskhArabic-Regular.ttf:fonts/NotoNaskhArabic-Regular.ttf

requirements = python3,kivy,requests,urllib3,certifi,idna,charset-normalizer,arabic-reshaper,python-bidi==0.4.2
