[app]
title = العراق
package.name = iraq_sender
package.domain = com.iraq.sender
version = 1.0.0
source.dir = .
# تأكد من إضافة ttf و png هنا
source.include_exts = py,png,jpg,kv,atlas,ttf,otf,json
source.include_patterns = assets/fonts/*.ttf,assets/*.png
icon.filename = %(source.dir)s/assets/icon.png

android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.ndk_api = 24

# إضافة مكتبات اللغة العربية للـ requirements
requirements = python3,kivy,requests,urllib3,certifi,idna,charset-normalizer,pillow,arabic-reshaper,python-bidi
