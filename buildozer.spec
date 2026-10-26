[app]
title = العراق
package.name = iraq_sender
package.domain = com.iraq.sender
version = 1.0.0
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
icon.filename = %(source.dir)s/assets/icon.png

android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# مهم جداً لهاتف S26 Ultra
android.archs = arm64-v8a

android.api = 33
android.minapi = 24
android.ndk_api = 24

# نسخة مبسطة بدون arabic-reshaper
requirements = python3,kivy,requests,urllib3,certifi,idna,charset-normalizer
