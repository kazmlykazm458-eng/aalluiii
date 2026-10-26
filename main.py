import os
import traceback
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.utils import platform

class TestApp(App):
    def on_start(self):
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            try:
                request_permissions([Permission.INTERNET])
            except Exception as e:
                print(f"Permission error: {e}")

    def build(self):
        layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        layout.add_widget(Label(text="Hello Iraq!", font_size=30))
        
        btn = Button(text="Test Connection", font_size=20, size_hint_y=None, height=100)
        btn.bind(on_press=self.send_test)
        layout.add_widget(btn)
        return layout

    def send_test(self, instance):
        import requests
        try:
            r = requests.get("https://api.telegram.org", timeout=10)
            self.root.clear_widgets()
            self.root.add_widget(Label(text=f"Success: {r.status_code}", font_size=30))
        except Exception as e:
            self.root.clear_widgets()
            self.root.add_widget(Label(text="Network Error", font_size=30))

# حفظ الخطأ في مجلد التطبيق الآمن (لا يحتاج أذونات)
if __name__ == '__main__':
    try:
        TestApp().run()
    except Exception:
        err = traceback.format_exc()
        try:
            safe_dir = os.environ.get('ANDROID_PRIVATE', '/sdcard')
            with open(os.path.join(safe_dir, 'iraq_crash.txt'), 'w', encoding='utf-8') as f:
                f.write(err)
        except Exception:
            pass
        raise
