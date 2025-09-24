import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/home/pi/Desktop/v2_Tripple S/cloudKey.json"
import json
import hashlib
import subprocess
import time
from datetime import datetime, time as dt_time
from pathlib import Path
from random import shuffle, choice, uniform, random
import types
import threading
import signal
import logging
import fcntl
import socket
import http.server
import socketserver
import urllib.parse
import base64
try:
    from tkinter import Tk, Button, Label
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

try:
    import qrcode
    from PIL import Image as PILImage
    QR_CODE_AVAILABLE = True
except ImportError:
    QR_CODE_AVAILABLE = False

# Setup debug logging for recording workflow
def setup_debug_logging():
    """Setup debug logging for recording workflow"""
    log_dir = Path(__file__).parent
    log_file = log_dir / "recording_debug.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(str(log_file), mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# Initialize debug logger
debug_logger = setup_debug_logging()

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, Line
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.slider import Slider
from kivy.app import App
from kivy.core.window import Window

# ------------------ KONFIG ------------------
APP_DIR = Path(__file__).parent
IMAGE_DIR = Path("/home/pi/Desktop/v2_Tripple S/BilderVertex")
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png')
ACCOUNTS_PATH = Path("/home/pi/Desktop/v2_Tripple S/Accounts.txt")
MODES_PATH = APP_DIR / "modes.json"
IMAGE_META_PATH = APP_DIR / "image_meta.json"

# Upload Server Configuration
# The upload server allows file uploads via web interface accessible through QR code
# Default port is 8080, but can be changed by modifying UPLOAD_PORT variable below
# Example QR link: http://192.168.1.100:8080/upload (replace IP with your device's IP)
# If you get "Address already in use" error, change UPLOAD_PORT to another value like 8000, 8001, 9000, etc.
UPLOAD_PORT = int(os.environ.get('UPLOAD_PORT', 8080))  # Configurable via environment variable or change here

DEFAULT_INTERVAL = 5
SCHEDULER_INTERVAL_SEC = 60
FADE_OUT_DUR = 0.35
FADE_IN_DUR = 0.45
THUMB_SIZE = dp(140)
MAX_IMAGES_DISPLAY = 2000
SHOW_DELETE_BUTTONS = True

SHOW_INFO_LABEL = False
SHOW_FAB_GALLERY = False
HIDE_TOOLBAR_TITLE = True
ENABLE_SOFT_KEYBOARD = True

INTERVAL_NEW_FILES = 3
TOOLBAR_FADE_DURATION = 0.4
TOOLBAR_VISIBLE_SECS = 7

IMAGE_SCALE_MODE = "cover"

EFFECTS_AVAILABLE = [
    ("fade", "Fade"),
    ("slide_left", "Slide Links"),
    ("slide_right", "Slide Rechts"),
    ("zoom_in", "Zoom In"),
    ("zoom_pan", "Zoom+Pan"),
    ("rotate", "Rotate"),
    ("blitz", "Blitz"),
    ("none", "Keine")
]
DEFAULT_EFFECTS = {"fade"}

# ------------------ Upload Server Implementation ------------------
class UploadHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for file uploads"""
    
    def do_GET(self):
        """Handle GET requests - serve upload form"""
        if self.path == '/upload' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html_content = f"""
            <!DOCTYPE html>
            <html lang="de">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Tripple-S Upload</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    h1 {{ color: #333; text-align: center; }}
                    .upload-area {{ border: 2px dashed #ccc; padding: 40px; text-align: center; margin: 20px 0; border-radius: 10px; }}
                    .upload-area:hover {{ border-color: #007bff; }}
                    input[type="file"] {{ margin: 20px 0; }}
                    button {{ background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }}
                    button:hover {{ background: #0056b3; }}
                    .status {{ margin: 20px 0; padding: 10px; border-radius: 5px; }}
                    .success {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
                    .error {{ background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
                    .port-info {{ background: #e7f3ff; padding: 10px; border-radius: 5px; margin-bottom: 20px; font-size: 14px; color: #0066cc; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🎵 Tripple-S File Upload</h1>
                    <div class="port-info">
                        📡 Server läuft auf Port {UPLOAD_PORT}
                    </div>
                    <form enctype="multipart/form-data" method="POST" action="/upload">
                        <div class="upload-area">
                            <p>📁 Datei zum Upload auswählen</p>
                            <input type="file" name="file" required>
                        </div>
                        <button type="submit">⬆️ Datei hochladen</button>
                    </form>
                    <div id="status"></div>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html_content.encode('utf-8'))
        else:
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests - process file uploads"""
        if self.path == '/upload':
            try:
                content_type = self.headers.get('Content-Type', '')
                if not content_type.startswith('multipart/form-data'):
                    self.send_error(400, "Invalid content type")
                    return
                
                # Parse multipart form data
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length == 0:
                    self.send_error(400, "No content")
                    return
                
                # Read the entire request body
                raw_data = self.rfile.read(content_length)
                
                # Simple multipart parsing (basic implementation)
                boundary = content_type.split('boundary=')[1].encode()
                parts = raw_data.split(b'--' + boundary)
                
                for part in parts:
                    if b'Content-Disposition: form-data' in part and b'filename=' in part:
                        # Extract filename
                        lines = part.split(b'\r\n')
                        for line in lines:
                            if b'Content-Disposition:' in line:
                                filename_start = line.find(b'filename="') + 10
                                filename_end = line.find(b'"', filename_start)
                                if filename_start > 9 and filename_end > filename_start:
                                    filename = line[filename_start:filename_end].decode('utf-8')
                                    break
                        else:
                            continue
                        
                        # Find file content (after double CRLF)
                        content_start = part.find(b'\r\n\r\n') + 4
                        if content_start > 3:
                            file_content = part[content_start:]
                            # Remove trailing boundary markers
                            if file_content.endswith(b'\r\n'):
                                file_content = file_content[:-2]
                            
                            # Save file to upload directory
                            upload_dir = APP_DIR / "uploads"
                            upload_dir.mkdir(exist_ok=True)
                            
                            file_path = upload_dir / filename
                            with open(file_path, 'wb') as f:
                                f.write(file_content)
                            
                            debug_logger.info(f"File uploaded successfully: {filename} ({len(file_content)} bytes)")
                            
                            # Send success response
                            self.send_response(200)
                            self.send_header('Content-type', 'text/html; charset=utf-8')
                            self.end_headers()
                            
                            success_html = f"""
                            <!DOCTYPE html>
                            <html lang="de">
                            <head>
                                <meta charset="UTF-8">
                                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                <title>Upload Erfolgreich</title>
                                <style>
                                    body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                                    .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
                                    .success {{ color: #28a745; font-size: 24px; margin: 20px 0; }}
                                    .back-link {{ display: inline-block; margin-top: 20px; padding: 10px 20px; background: #007bff; color: white; text-decoration: none; border-radius: 5px; }}
                                    .back-link:hover {{ background: #0056b3; }}
                                </style>
                            </head>
                            <body>
                                <div class="container">
                                    <div class="success">✅ Upload erfolgreich!</div>
                                    <p>Datei "{filename}" wurde hochgeladen.</p>
                                    <p>Größe: {len(file_content)} Bytes</p>
                                    <a href="/upload" class="back-link">🔄 Weitere Datei hochladen</a>
                                </div>
                            </body>
                            </html>
                            """
                            self.wfile.write(success_html.encode('utf-8'))
                            return
                
                # If we get here, no file was found
                self.send_error(400, "No file found in upload")
                
            except Exception as e:
                debug_logger.error(f"Upload error: {e}", exc_info=True)
                self.send_error(500, f"Upload failed: {str(e)}")
        else:
            self.send_error(404, "Not found")

class UploadServer:
    """Configurable upload server with port conflict detection"""
    
    def __init__(self, port=UPLOAD_PORT):
        self.port = port
        self.server = None
        self.server_thread = None
        self.running = False
        
    def is_port_available(self, port):
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                return result != 0
        except Exception:
            return False
    
    def get_local_ip(self):
        """Get the local IP address"""
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                return sock.getsockname()[0]
        except Exception:
            return "localhost"
    
    def start_server(self):
        """Start the upload server with port conflict handling"""
        if self.running:
            debug_logger.warning("Upload server already running")
            return True
            
        # Check if port is available
        if not self.is_port_available(self.port):
            error_msg = f"Port {self.port} ist bereits belegt (Address already in use)"
            debug_logger.error(error_msg)
            debug_logger.info("Lösung: Ändern Sie UPLOAD_PORT in main.py auf einen anderen Wert (z.B. 8000, 8001, 9000)")
            return False
        
        try:
            # Create server
            self.server = socketserver.TCPServer(("", self.port), UploadHandler)
            self.server.allow_reuse_address = True
            
            # Start server in background thread
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            
            self.running = True
            
            local_ip = self.get_local_ip()
            success_msg = f"Upload-Server gestartet auf Port {self.port}"
            debug_logger.info(success_msg)
            debug_logger.info(f"Upload-URL: http://{local_ip}:{self.port}/upload")
            
            return True
            
        except Exception as e:
            error_msg = f"Fehler beim Starten des Upload-Servers: {e}"
            debug_logger.error(error_msg, exc_info=True)
            if "Address already in use" in str(e):
                debug_logger.info("Tipp: Port ist bereits belegt. Ändern Sie UPLOAD_PORT auf einen anderen Wert.")
            return False
    
    def _run_server(self):
        """Run the server (internal method for thread)"""
        try:
            debug_logger.info(f"Upload server thread started on port {self.port}")
            self.server.serve_forever()
        except Exception as e:
            debug_logger.error(f"Upload server thread error: {e}", exc_info=True)
            self.running = False
    
    def stop_server(self):
        """Stop the upload server"""
        if self.server and self.running:
            debug_logger.info("Stopping upload server...")
            self.running = False
            self.server.shutdown()
            self.server.server_close()
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=2)
            debug_logger.info("Upload server stopped")
    
    def get_qr_url(self):
        """Get the URL for QR code generation"""
        local_ip = self.get_local_ip()
        return f"http://{local_ip}:{self.port}/upload"
    
    def generate_qr_code(self, url=None):
        """Generate QR code for upload URL"""
        if not QR_CODE_AVAILABLE:
            debug_logger.warning("QR code generation not available - qrcode library not installed")
            return None
            
        if url is None:
            url = self.get_qr_url()
            
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # Create QR code image
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Save to temp file
            temp_qr_path = APP_DIR / "temp_qr_code.png"
            qr_image.save(str(temp_qr_path))
            
            debug_logger.info(f"QR code generated for URL: {url}")
            return str(temp_qr_path)
            
        except Exception as e:
            debug_logger.error(f"Error generating QR code: {e}", exc_info=True)
            return None

# Global upload server instance
upload_server = UploadServer(UPLOAD_PORT)

SHOW_DEBUG_OVERLAY = True
DEBUG_OVERLAY_FONT_SIZE = 16
DEBUG_OVERLAY_POSITION = "top_left"
# --------------------------------------------

KIVYMD_OK = False
try:
    from kivymd.uix.toolbar import MDToolbar
    from kivymd.uix.textfield import MDTextField
    from kivymd.app import MDApp
    AppBarClass = MDToolbar
    KIVYMD_OK = True
except Exception:
    AppBarClass = None
    KIVYMD_OK = False

# ------------------ Account / Auth ------------------
def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode('utf-8')).hexdigest()

def load_accounts():
    if not ACCOUNTS_PATH.exists():
        return {}
    accounts = {}
    with ACCOUNTS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split(";")
            if len(parts) >= 6:
                username, pw_hash, vorname, nachname, email, firma = parts[:6]
                accounts[username.lower()] = {
                    "benutzername": username,
                    "passwort": pw_hash,
                    "vorname": vorname,
                    "nachname": nachname,
                    "email": email,
                    "firma": firma
                }
    return accounts

def save_account(benutzername, passwort, vorname, nachname, email, firma):
    pw_hash = hash_password(passwort)
    line = ";".join([benutzername, pw_hash, vorname, nachname, email, firma])
    ACCOUNTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ACCOUNTS_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def account_exists(benutzername):
    return benutzername.lower() in load_accounts()

def check_account(benutzername, passwort):
    if benutzername.lower() == "dennis" and passwort == "wojtyczka":
        return True
    acc = load_accounts()
    return benutzername.lower() in acc and acc[benutzername.lower()]["passwort"] == hash_password(passwort)

# ------------------ Mode / Scheduler ------------------
def parse_time(hhmm: str):
    try:
        h, m = hhmm.strip().split(":")
        return dt_time(int(h), int(m))
    except Exception:
        return None

def time_in_window(now_t: dt_time, start_t: dt_time, end_t: dt_time):
    if start_t <= end_t:
        return start_t <= now_t <= end_t
    return now_t >= start_t or now_t <= end_t

class Mode:
    def __init__(self, name, images=None, interval=DEFAULT_INTERVAL, windows=None,
                 auto=True, randomize=False):
        self.name = name
        self.images = images[:] if images else []
        self.interval = interval
        self.windows = windows[:] if windows else []
        self.auto = auto
        self.randomize = randomize
    def to_dict(self):
        return {
            "name": self.name,
            "images": self.images,
            "interval": self.interval,
            "windows": self.windows,
            "auto": self.auto,
            "randomize": self.randomize
        }
    @staticmethod
    def from_dict(d):
        return Mode(
            name=d.get("name", "Unbenannt"),
            images=d.get("images", []),
            interval=d.get("interval", DEFAULT_INTERVAL),
            windows=d.get("windows", []),
            auto=d.get("auto", True),
            randomize=d.get("randomize", False),
        )
    def is_active_now(self):
        if not self.auto or not self.windows:
            return False
        now_t = datetime.now().time()
        for w in self.windows:
            st = parse_time(w.get("start", "00:00"))
            et = parse_time(w.get("end", "23:59"))
            if st and et and time_in_window(now_t, st, et):
                return True
        return False
    def existing_images(self):
        return [p for p in self.images if os.path.isfile(p)]

class ModeManager:
    def __init__(self, path: Path):
        self.path = path
        self.modes = []
        self.load()
        self.ensure_defaults()
    def load(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.modes = [Mode.from_dict(x) for x in data.get("modes", [])]
            except Exception:
                self.modes = []
        else:
            self.modes = []
    def save(self):
        self.path.write_text(
            json.dumps({"modes": [m.to_dict() for m in self.modes]}, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    def ensure_defaults(self):
        names = [m.name for m in self.modes]
        changed = False
        if "Alle Bilder" not in names:
            self.modes.insert(0, Mode("Alle Bilder", images=[], interval=5, windows=[], auto=False)); changed = True
        if "Tag" not in names:
            self.modes.append(Mode("Tag", images=[], interval=5,
                                   windows=[{"start": "06:00", "end": "21:00"}], auto=True)); changed = True
        if "Standard" not in names:
            self.modes.append(Mode("Standard", images=[], interval=5, windows=[], auto=False)); changed = True
        if "Nacht" not in names:
            self.modes.append(Mode("Nacht", images=[], interval=7,
                                   windows=[{"start": "21:00", "end": "05:30"}], auto=True)); changed = True
        if "Urlaub" not in names:
            self.modes.append(Mode("Urlaub", images=[], interval=15,
                                   windows=[{"start": "12:30", "end": "13:30"}], auto=True)); changed = True
        if changed:
            self.save()
    def get(self, name):
        for m in self.modes:
            if m.name == name:
                return m
        return None
    def scheduled_mode(self):
        # Check if Urlaub mode is active first - it has priority and disables Tag/Nacht
        urlaub_mode = self.get("Urlaub")
        if urlaub_mode and urlaub_mode.is_active_now():
            return urlaub_mode
        
        # If Urlaub is not active, check other scheduled modes (excluding Tag/Nacht if Urlaub exists)
        for m in self.modes:
            if m.name in ("Alle Bilder", "Standard", "Urlaub"):
                continue
            if m.is_active_now():
                return m
        return None

# ---- UI Helpers ----
def make_text_field(hint, password=False):
    if KIVYMD_OK:
        try:
            return MDTextField(hint_text=hint, password=password)
        except Exception:
            pass
    box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(78))
    lbl = Label(text=hint, size_hint_y=None, height=dp(22), color=(0.85,0.85,0.9,1))
    ti = TextInput(password=password, multiline=False,
                   background_color=(0.2,0.2,0.24,1),
                   foreground_color=(1,1,1,1),
                   font_size=dp(20),
                   padding=[10,10,10,10],
                   height=dp(50), size_hint_y=None)
    box.add_widget(lbl); box.add_widget(ti); box._ti = ti
    return box

def get_text(widget):
    if hasattr(widget, "text"):
        try: return widget.text
        except: pass
    if hasattr(widget, "_ti"): return widget._ti.text
    for c in getattr(widget, "children", []):
        if isinstance(c, TextInput): return c.text
    return ""

def get_underlying_textinput(widget):
    if isinstance(widget, TextInput):
        return widget
    if hasattr(widget, "_ti"): return widget._ti
    return None

# ---- Soft Keyboard ----
class SoftKeyboard(FloatLayout):
    def __init__(self, on_close, **kw):
        super().__init__(**kw)
        self.on_close = on_close
        self.target = None
        with self.canvas.before:
            Color(0,0,0,0.85)
            self.bg = Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=self._upd_bg,size=self._upd_bg)
        rows = [
            "1 2 3 4 5 6 7 8 9 0 ←",
            "q w e r t z u i o p",
            "a s d f g h j k l",
            "⇧ y x c v b n m .",
            "SPACE OK"
        ]
        self.shift = False
        root = BoxLayout(orientation="vertical", size_hint=(1,None), height=dp(320), pos_hint={'x':0,'y':0})
        for r in rows:
            rb = BoxLayout(spacing=dp(4), size_hint_y=None, height=dp(56), padding=[dp(4),0,dp(4),0])
            for key in r.split():
                btn = Button(text=key,
                             background_normal='',
                             background_color=(0.25,0.25,0.3,1),
                             color=(1,1,1,1),
                             font_size=dp(20))
                btn.bind(on_release=lambda inst, k=key: self.press(k))
                rb.add_widget(btn)
            root.add_widget(rb)
        self.add_widget(root)
    def _upd_bg(self,*a):
        self.bg.pos=self.pos; self.bg.size=self.size
    def set_target(self, widget):
        self.target = get_underlying_textinput(widget)
    def press(self, key):
        if key == "⇧":
            self.shift = not self.shift; return
        if key == "←":
            if self.target: self.target.text = self.target.text[:-1]
            return
        if key == "SPACE": key = " "
        if key == "OK":
            self.on_close(); return
        if self.target:
            self.target.insert_text(key.upper() if self.shift and len(key)==1 else key)

# ---- Auth Screens (Login / Register) ----
class LoginScreen(FloatLayout):
    def __init__(self, on_success, on_register, **kw):
        super().__init__(**kw)
        self.on_success=on_success
        self.on_register=on_register
        self.keyboard_widget=None
        self.last_input=None
        with self.canvas.before:
            Color(0.07,0.07,0.09,1)
            self.bg=Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=self._upd_bg,size=self._upd_bg)
        card=BoxLayout(orientation="vertical", size_hint=(None,None),
                       size=(480,560),
                       pos_hint={"center_x":0.5,"center_y":0.55},
                       padding=dp(28), spacing=dp(18))
        with card.canvas.before:
            Color(0.16,0.16,0.20,1)
            self._c_bg=Rectangle(pos=card.pos,size=card.size)
        card.bind(pos=lambda *a:setattr(self._c_bg,'pos',card.pos),
                  size=lambda *a:setattr(self._c_bg,'size',card.size))
        self.add_widget(card)
        card.add_widget(Label(text="Login", size_hint_y=None, height=dp(64),
                              font_size=dp(32), color=(1,1,1,1)))
        self.user=make_text_field("Benutzername")
        self.pw=make_text_field("Passwort", password=True)
        for w in (self.user,self.pw):
            ti=get_underlying_textinput(w)
            if ti: ti.bind(focus=self._on_focus)
        card.add_widget(self.user); card.add_widget(self.pw)
        kb_btn=Button(text="Tastatur", size_hint_y=None, height=dp(50),
                      background_normal='', background_color=(0.3,0.35,0.5,1),
                      color=(1,1,1,1), font_size=dp(20))
        kb_btn.bind(on_release=lambda *_: self.toggle_keyboard())
        card.add_widget(kb_btn)
        self.status=Label(text="", size_hint_y=None, height=dp(30),
                          color=(1,0.4,0.4,1), font_size=dp(18))
        card.add_widget(self.status)
        row=BoxLayout(size_hint_y=None, height=dp(70), spacing=dp(20))
        b_login=Button(text="Login", background_normal='',
                       background_color=(0.25,0.45,0.25,1),
                       color=(1,1,1,1), font_size=dp(22))
        b_reg=Button(text="Registrieren", background_normal='',
                     background_color=(0.3,0.3,0.35,1),
                     color=(1,1,1,1), font_size=dp(22))
        b_login.bind(on_release=self.try_login)
        b_reg.bind(on_release=lambda *_: self.on_register())
        row.add_widget(b_login); row.add_widget(b_reg)
        card.add_widget(row)
    def _on_focus(self, textinput, focused):
        if focused:
            self.last_input=textinput
            if self.keyboard_widget:
                self.keyboard_widget.set_target(textinput)
    def toggle_keyboard(self):
        if not ENABLE_SOFT_KEYBOARD: return
        if self.keyboard_widget:
            self.remove_widget(self.keyboard_widget); self.keyboard_widget=None
        else:
            self.keyboard_widget=SoftKeyboard(on_close=self.toggle_keyboard,
                                              size_hint=(1,None),
                                              height=dp(320),
                                              pos_hint={'x':0,'y':0})
            target=self.last_input or get_underlying_textinput(self.user)
            self.keyboard_widget.set_target(target)
            self.add_widget(self.keyboard_widget)
    def _upd_bg(self,*a):
        self.bg.pos=self.pos; self.bg.size=self.size
    def try_login(self,*_):
        username=get_text(self.user).strip()
        password=get_text(self.pw)
        if check_account(username,password):
            self.status.text=""
            if self.keyboard_widget: self.remove_widget(self.keyboard_widget)
            self.on_success()
        else:
            self.status.text="Falscher Benutzername oder Passwort"



class RegisterScreen(FloatLayout):
    def __init__(self, on_done, **kw):
        super().__init__(**kw)
        self.on_done=on_done
        self.keyboard_widget=None
        self.last_input=None
        with self.canvas.before:
            Color(0.07,0.07,0.09,1)
            self.bg=Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=self._upd_bg,size=self._upd_bg)
        card=BoxLayout(orientation="vertical", size_hint=(None,None),
                       size=(520,820),
                       pos_hint={"center_x":0.5,"center_y":0.53},
                       padding=dp(28), spacing=dp(16))
        with card.canvas.before:
            Color(0.16,0.16,0.20,1)
            self._c2_bg=Rectangle(pos=card.pos,size=card.size)
        card.bind(pos=lambda *a:setattr(self._c2_bg,'pos',card.pos),
                  size=lambda *a:setattr(self._c2_bg,'size',card.size))
        self.add_widget(card)
        card.add_widget(Label(text="Registrieren", size_hint_y=None, height=dp(56),
                              font_size=dp(30), color=(1,1,1,1)))
        self.fname=make_text_field("Vorname")
        self.lname=make_text_field("Nachname")
        self.user=make_text_field("Benutzername")
        self.mail=make_text_field("E-Mail")
        self.company=make_text_field("Firma")
        self.pw1=make_text_field("Passwort", password=True)
        self.pw2=make_text_field("Passwort wiederholen", password=True)
        fields=[self.fname,self.lname,self.user,self.mail,self.company,self.pw1,self.pw2]
        for w in fields:
            ti=get_underlying_textinput(w)
            if ti: ti.bind(focus=self._on_focus)
            card.add_widget(w)
        kb_btn=Button(text="Tastatur", size_hint_y=None, height=dp(50),
                      background_normal='', background_color=(0.3,0.35,0.5,1),
                      color=(1,1,1,1), font_size=dp(20))
        kb_btn.bind(on_release=lambda *_: self.toggle_keyboard())
        card.add_widget(kb_btn)
        self.status=Label(text="", size_hint_y=None, height=dp(34),
                          color=(1,0.4,0.4,1), font_size=dp(16))
        card.add_widget(self.status)
        row=BoxLayout(size_hint_y=None, height=dp(64), spacing=dp(18))
        b_ok=Button(text="Speichern", background_normal='',
                    background_color=(0.25,0.45,0.25,1), color=(1,1,1,1), font_size=dp(22))
        b_cancel=Button(text="Abbrechen", background_normal='',
                        background_color=(0.3,0.3,0.35,1), color=(1,1,1,1), font_size=dp(22))
        b_ok.bind(on_release=self.try_register)
        b_cancel.bind(on_release=lambda *_: self.on_done())
        row.add_widget(b_ok); row.add_widget(b_cancel)
        card.add_widget(row)
    def _on_focus(self, textinput, focused):
        if focused:
            self.last_input=textinput
            if self.keyboard_widget:
                self.keyboard_widget.set_target(textinput)
    def toggle_keyboard(self):
        if not ENABLE_SOFT_KEYBOARD: return
        if self.keyboard_widget:
            self.remove_widget(self.keyboard_widget); self.keyboard_widget=None
        else:
            self.keyboard_widget=SoftKeyboard(on_close=self.toggle_keyboard,
                                              size_hint=(1,None),height=dp(320),
                                              pos_hint={'x':0,'y':0})
            target=self.last_input or get_underlying_textinput(self.fname)
            self.keyboard_widget.set_target(target)
            self.add_widget(self.keyboard_widget)
    def _upd_bg(self,*a):
        self.bg.pos=self.pos; self.bg.size=self.size
    def try_register(self,*_):
        vorname=get_text(self.fname).strip()
        nachname=get_text(self.lname).strip()
        benutzername=get_text(self.user).strip()
        email=get_text(self.mail).strip()
        firma=get_text(self.company).strip()
        pw1=get_text(self.pw1)
        pw2=get_text(self.pw2)
        def fail(msg): self.status.text=msg
        if not all([vorname,nachname,benutzername,email,pw1,pw2]): return fail("Bitte alle Felder")
        if '@' not in email or '.' not in email: return fail("Mail ungültig")
        if len(pw1)<6: return fail("Passwort zu kurz")
        if pw1!=pw2: return fail("Passwörter verschieden")
        if account_exists(benutzername): return fail("Benutzer existiert")
        try:
            save_account(benutzername,pw1,vorname,nachname,email,firma)
        except Exception:
            return fail("Fehler beim Speichern")
        self.status.text="Registriert!"
        Clock.schedule_once(lambda dt:self.on_done(),0.8)

# ---- CustomAppBar ----
class CustomAppBar(BoxLayout):
    def __init__(self, title="App", **kwargs):
        super().__init__(orientation="horizontal", size_hint=(1,None), height=dp(60), **kwargs)
        with self.canvas.before:
            Color(0.12,0.12,0.14,1)
            self.bg=Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=self._upd_bg,size=self._upd_bg)
        self._title_label=Label(text=("" if HIDE_TOOLBAR_TITLE else title),
                                color=(1,1,1,1), size_hint_x=1,
                                halign='left', valign='middle')
        self._title_label.bind(size=lambda inst,*a:setattr(inst,"text_size",inst.size))
        self.add_widget(self._title_label)
        self._buttons_box=BoxLayout(size_hint=(None,1)); self._buttons_box.width=0
        self.add_widget(self._buttons_box)
        self.opacity=1
        self.disabled=False
        self._fade_anim=None
    def _upd_bg(self,*a):
        self.bg.pos=self.pos; self.bg.size=self.size
    @property
    def title(self): return self._title_label.text
    @title.setter
    def title(self,v): self._title_label.text = "" if HIDE_TOOLBAR_TITLE else v
    def set_right_actions(self, items):
        self._buttons_box.clear_widgets(); total_w=0
        for text,cb in items:
            btn=Button(text=text,size_hint=(None,1),width=dp(110),
                       background_normal='',background_color=(0.20,0.22,0.26,1),
                       color=(1,1,1,1),font_size=dp(16))
            btn.bind(on_release=lambda inst,c=cb:c())
            self._buttons_box.add_widget(btn); total_w+=btn.width
        self._buttons_box.width=total_w
    def fade_in(self,duration=TOOLBAR_FADE_DURATION):
        self.disabled=False
        if self._fade_anim: self._fade_anim.stop(self)
        self._fade_anim=Animation(opacity=1,d=duration,t='out_quad')
        self._fade_anim.start(self)
    def fade_out(self,duration=TOOLBAR_FADE_DURATION):
        if self._fade_anim: self._fade_anim.stop(self)
        def _dis(*_): self.disabled=True
        self._fade_anim=Animation(opacity=0,d=duration,t='in_quad')
        self._fade_anim.bind(on_complete=_dis)
        self._fade_anim.start(self)

# ---- Persistenz Bild-Meta ----
def load_image_meta():
    base = {"effects":{}, "intervals":{}, "weights":{}, "brightness":{}, "global_interval": None, "global_brightness": None}
    if not IMAGE_META_PATH.exists():
        return base
    try:
        data=json.loads(IMAGE_META_PATH.read_text(encoding="utf-8"))
        for k,v in base.items():
            if k not in data: data[k]=v
        return data
    except Exception:
        return base

def save_image_meta(meta):
    try:
        IMAGE_META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print("[META] Speichern fehlgeschlagen:", e)

# ---- Image Settings Popup (per Bild) ----
class ImageSettingsPopup(FloatLayout):
    def __init__(self, image_path, slideshow, on_close=None, on_deleted=None, **kw):
        super().__init__(**kw)
        self.image_path=image_path
        self.slideshow=slideshow
        self.on_close=on_close
        self.on_deleted=on_deleted
        with self.canvas.before:
            Color(0,0,0,0.65)
            self.bg=Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=lambda *a:(setattr(self.bg,'pos',self.pos),setattr(self.bg,'size',self.size)))
        panel=BoxLayout(orientation='vertical',size_hint=(None,None),
                        size=(dp(500),dp(720)),
                        pos_hint={'center_x':0.5,'center_y':0.5},
                        padding=dp(20),spacing=dp(14))
        with panel.canvas.before:
            Color(0.16,0.16,0.2,0.97)
            panel._bg=Rectangle(pos=panel.pos,size=panel.size)
        panel.bind(pos=lambda *a:setattr(panel._bg,'pos',panel.pos),
                   size=lambda *a:setattr(panel._bg,'size',panel.size))
        name=Path(image_path).name
        panel.add_widget(Label(text=name,size_hint_y=None,height=dp(40),
                               font_size=dp(18),color=(1,1,1,1)))

        # Effekt Override
        panel.add_widget(Label(text="Effekt Override:",size_hint_y=None,height=dp(28),
                               font_size=dp(16),color=(1,1,1,0.9)))
        from kivy.uix.gridlayout import GridLayout
        grid=GridLayout(cols=2,spacing=dp(6),size_hint_y=None)
        grid.bind(minimum_height=lambda inst,val:setattr(inst,'height',val))
        cur_eff=self.slideshow.image_effect_overrides.get(image_path)
        def add_eff(key,label):
            btn=ToggleButton(text=("Standard" if key is None else label),
                             group="imgfx",
                             state='down' if cur_eff==key else ('down' if (key is None and cur_eff is None) else 'normal'),
                             size_hint_y=None,height=dp(44),
                             background_normal='',background_down='',
                             background_color=(0.25,0.35,0.5,1),
                             color=(1,1,1,1),font_size=dp(14))
            btn.bind(on_release=lambda inst,k=key:self._set_effect(k))
            grid.add_widget(btn)
        add_eff(None,"Standard")
        for k,lbl in EFFECTS_AVAILABLE: add_eff(k,lbl)
        scr=ScrollView(size_hint=(1,0.38)); scr.add_widget(grid)
        panel.add_widget(scr)

        # Per-Bild Intervall
        panel.add_widget(Label(text="Anzeigedauer (s, 0 = Aus):",size_hint_y=None,height=dp(26),
                               font_size=dp(16),color=(1,1,1,0.9)))
        cur_int=self.slideshow.image_interval_overrides.get(image_path,0)
        self.int_slider=Slider(min=0,max=120,value=cur_int,step=1,size_hint_y=None,height=dp(42))
        self.int_label=Label(text=f"{cur_int}s" if cur_int>0 else "Aus",size_hint_y=None,height=dp(22),
                             font_size=dp(16),color=(0.9,0.9,1,1))
        self.int_slider.bind(value=lambda inst,val:self._upd_int(val))
        panel.add_widget(self.int_slider); panel.add_widget(self.int_label)

        # Priorität / Gewicht
        panel.add_widget(Label(text="Priorität / Gewicht (1-5):",size_hint_y=None,height=dp(26),
                               font_size=dp(16),color=(1,1,1,0.9)))
        cur_w=self.slideshow.image_priority_weights.get(image_path,1)
        self.w_slider=Slider(min=1,max=5,value=cur_w,step=1,size_hint_y=None,height=dp(42))
        self.w_label=Label(text=str(int(cur_w)),size_hint_y=None,height=dp(22),
                           font_size=dp(16),color=(0.9,0.9,1,1))
        self.w_slider.bind(value=lambda inst,val:self.w_label.__setattr__('text',str(int(val))))
        panel.add_widget(self.w_slider); panel.add_widget(self.w_label)

        # Per-Bild Helligkeit
        panel.add_widget(Label(text="Helligkeit (50% - 150%):",size_hint_y=None,height=dp(26),
                               font_size=dp(16),color=(1,1,1,0.9)))
        cur_b = self.slideshow.image_brightness_overrides.get(image_path,1.0)
        self.bright_slider=Slider(min=0.5,max=1.5,value=cur_b,step=0.01,size_hint_y=None,height=dp(42))
        self.bright_label=Label(text=f"{cur_b*100:.0f}%",size_hint_y=None,height=dp(22),
                                font_size=dp(16),color=(0.9,0.9,1,1))
        self.bright_slider.bind(value=lambda inst,val:self.bright_label.__setattr__('text',f"{float(val)*100:.0f}%"))
        panel.add_widget(self.bright_slider); panel.add_widget(self.bright_label)

        # Buttons
        row=BoxLayout(size_hint_y=None,height=dp(56),spacing=dp(14))
        save_btn=Button(text="Speichern",background_normal='',background_color=(0.25,0.55,0.25,1),
                        color=(1,1,1,1),font_size=dp(18))
        del_btn=Button(text="Löschen",background_normal='',background_color=(0.6,0.25,0.25,1),
                       color=(1,1,1,1),font_size=dp(18))
        close_btn=Button(text="Schließen",background_normal='',background_color=(0.35,0.45,0.55,1),
                         color=(1,1,1,1),font_size=dp(18))
        save_btn.bind(on_release=lambda *_: self._save())
        del_btn.bind(on_release=lambda *_: self._confirm_delete())
        close_btn.bind(on_release=lambda *_: self._close())
        row.add_widget(save_btn); row.add_widget(del_btn); row.add_widget(close_btn)
        panel.add_widget(row)
        self._confirm_box=None
        self.add_widget(panel)
    def _set_effect(self,key):
        if key is None:
            self.slideshow.image_effect_overrides.pop(self.image_path, None)
        else:
            self.slideshow.image_effect_overrides[self.image_path]=key
    def _upd_int(self,val):
        v=int(val); self.int_label.text=f"{v}s" if v>0 else "Aus"
    def _save(self):
        # Interval
        v=int(self.int_slider.value)
        if v<=0:
            self.slideshow.image_interval_overrides.pop(self.image_path, None)
        else:
            self.slideshow.image_interval_overrides[self.image_path]=v
        # Gewicht
        w=int(self.w_slider.value)
        self.slideshow.image_priority_weights[self.image_path]=w
        # Brightness
        b=float(self.bright_slider.value)
        # Standard = 1.0 -> wenn 1.0 dann raus für Clean
        if abs(b-1.0)<0.001:
            self.slideshow.image_brightness_overrides.pop(self.image_path, None)
        else:
            self.slideshow.image_brightness_overrides[self.image_path]=b
        self.slideshow.persist_meta()
        # Falls aktuelles Bild -> sofort anwenden
        if self.slideshow.current_original_path == self.image_path:
            self.slideshow._apply_current_brightness()
            self.slideshow._reschedule_for_current()
        self._close()
    def _confirm_delete(self):
        if self._confirm_box: return
        box=BoxLayout(orientation='vertical',size_hint=(None,None),
                      size=(dp(340),dp(160)),
                      pos_hint={'center_x':0.5,'center_y':0.5},
                      padding=dp(16),spacing=dp(12))
        with box.canvas.before:
            Color(0.3,0.15,0.15,0.95)
            box._bg=Rectangle(pos=box.pos,size=box.size)
        box.bind(pos=lambda *a:setattr(box._bg,'pos',box.pos),
                 size=lambda *a:setattr(box._bg,'size',box.size))
        box.add_widget(Label(text="Bild wirklich löschen?",size_hint_y=None,
                             height=dp(40),font_size=dp(20),color=(1,1,1,1)))
        r=BoxLayout(size_hint_y=None,height=dp(50),spacing=dp(10))
        ja=Button(text="Ja",background_normal='',background_color=(0.7,0.2,0.2,1),color=(1,1,1,1))
        nein=Button(text="Nein",background_normal='',background_color=(0.4,0.4,0.5,1),color=(1,1,1,1))
        ja.bind(on_release=lambda *_: self._delete_now())
        nein.bind(on_release=lambda *_: self._remove_confirm())
        r.add_widget(ja); r.add_widget(nein)
        box.add_widget(r)
        self.add_widget(box); self._confirm_box=box
    def _remove_confirm(self):
        if self._confirm_box and self._confirm_box in self.children:
            self.remove_widget(self._confirm_box)
        self._confirm_box=None
    def _delete_now(self):
        self._remove_confirm()
        p=self.image_path
        try:
            if os.path.isfile(p): os.remove(p)
        except Exception as e: print("[Delete] Fehler:",e)
        for d in (self.slideshow.image_effect_overrides,
                  self.slideshow.image_interval_overrides,
                  self.slideshow.image_priority_weights,
                  self.slideshow.image_brightness_overrides):
            d.pop(p, None)
        for m in self.slideshow.mode_manager.modes:
            if p in m.images: m.images.remove(p)
        self.slideshow.mode_manager.save()
        self.slideshow.persist_meta()
        if self.slideshow.current_original_path == p:
            if p in self.slideshow.images:
                self.slideshow.images.remove(p)
            self.slideshow.index=0
            self.slideshow.show_current_image(initial=True)
        if self.on_deleted: self.on_deleted(p)
        self._close()
    def _close(self):
        if self.on_close: self.on_close()
        if self.parent: self.parent.remove_widget(self)

# ---- Globale Settings Hierarchie ----
class SettingsRootPopup(FloatLayout):
    def __init__(self, slideshow, **kw):
        super().__init__(**kw)
        self.slideshow=slideshow
        with self.canvas.before:
            Color(0,0,0,0.55); self.bg=Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=self._upd,size=self._upd)
        panel=BoxLayout(orientation='vertical',size_hint=(None,None),
                        size=(dp(500),dp(480)),
                        pos_hint={'center_x':0.5,'center_y':0.5},
                        padding=dp(24),spacing=dp(18))
        
        with panel.canvas.before:
            Color(0.16,0.16,0.2,0.97); panel._bg=Rectangle(pos=panel.pos,size=panel.size)
        panel.bind(pos=lambda *a:setattr(panel._bg,'pos',panel.pos),
                   size=lambda *a:setattr(panel._bg,'size',panel.size))
        panel.add_widget(Label(text="Einstellungen",
                               size_hint_y=None,height=dp(56),
                               font_size=dp(34),color=(1,1,1,1)))
        def make_btn(text, cb):
            b=Button(text=text,size_hint_y=None,height=dp(70),
                     background_normal='',background_color=(0.25,0.35,0.5,1),
                     color=(1,1,1,1),font_size=dp(22))
            b.bind(on_release=lambda *_: cb())
            return b
        panel.add_widget(make_btn("Allgemein", self._open_general))
        panel.add_widget(make_btn("Bilddauer", self._open_duration))
        panel.add_widget(make_btn("Schließen", self._close))
        self.add_widget(panel)
    def _upd(self,*a):
        self.bg.pos=self.pos; self.bg.size=self.size
    def _open_general(self):
        self.slideshow.open_single(GeneralSettingsPopup(self.slideshow))
    def _open_duration(self):
        self.slideshow.open_single(GlobalDurationPopup(self.slideshow))
    def _close(self):
        if self.parent: self.parent.remove_widget(self)
        if self.slideshow.current_overlay is self:
            self.slideshow.current_overlay=None
class AufnahmePopup(FloatLayout):
    """Popup window for recording functionality with improved error handling"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.process = None
        self.is_running = False
        self.start_time = None
        self.timer_event = None
        self.workflow_triggered = False  # Track if workflow was already triggered
        self.workflow_status_checker = None  # Track status checker
        self.workflow_lock_file = None  # NEW: Track workflow lockfile
        self.trigger_creation_lock = threading.Lock()  # NEW: Thread-safe trigger creation
        
        # Audio file path for validation (standardized location)
        self.audio_file_path = Path("/home/pi/Desktop/v2_Tripple S/aufnahme.wav")
        
        # Background
        with self.canvas.before:
            Color(0, 0, 0, 0.7)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        # Main panel - make it larger to accommodate output display
        panel = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(dp(600), dp(500)),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            padding=dp(20),
            spacing=dp(15)
        )
        
        with panel.canvas.before:
            Color(0.16, 0.16, 0.20, 0.95)
            panel._bg = Rectangle(pos=panel.pos, size=panel.size)
        panel.bind(pos=lambda *a: setattr(panel._bg, 'pos', panel.pos),
                  size=lambda *a: setattr(panel._bg, 'size', panel.size))
        
        # Title
        title = Label(
            text="Aufnahme",
            size_hint_y=None,
            height=dp(40),
            font_size=dp(28),
            color=(1, 1, 1, 1)
        )
        panel.add_widget(title)
        
        # Timer display
        self.timer_label = Label(
            text="00:00",
            size_hint_y=None,
            height=dp(50),
            font_size=dp(32),
            color=(0.8, 0.9, 1, 1)
        )
        panel.add_widget(self.timer_label)
        
        # Start/Stop button
        self.button = Button(
            text="Start",
            size_hint_y=None,
            height=dp(60),
            background_normal='',
            background_color=(0.25, 0.55, 0.25, 1),
            color=(1, 1, 1, 1),
            font_size=dp(24)
        )
        self.button.bind(on_press=self.toggle_recording)
        panel.add_widget(self.button)
        
        # Output display area
        output_label = Label(
            text="Ausgabe:",
            size_hint_y=None,
            height=dp(25),
            font_size=dp(18),
            color=(1, 1, 1, 0.8),
            halign='left'
        )
        output_label.bind(size=lambda inst, *args: setattr(inst, 'text_size', inst.size))
        panel.add_widget(output_label)
        
        # Scrollable output text area
        from kivy.uix.scrollview import ScrollView
        scroll = ScrollView(size_hint=(1, 0.5))
        self.output_text = Label(
            text="Bereit für Aufnahme...",
            text_size=(None, None),
            halign='left',
            valign='top',
            color=(0.9, 0.9, 0.9, 1),
            font_size=dp(14),
            markup=True
        )
        scroll.add_widget(self.output_text)
        panel.add_widget(scroll)
        
        # Buttons row
        button_row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10)
        )
        
        # QR Code button
        qr_button = Button(
            text=f"📱 QR-Code (Port {UPLOAD_PORT})",
            background_normal='',
            background_color=(0.3, 0.5, 0.7, 1),
            color=(1, 1, 1, 1),
            font_size=dp(18)
        )
        qr_button.bind(on_press=self.show_qr_code)
        button_row.add_widget(qr_button)
        
        # Close button
        close_button = Button(
            text="Schließen",
            background_normal='',
            background_color=(0.4, 0.4, 0.45, 1),
            color=(1, 1, 1, 1),
            font_size=dp(20)
        )
        close_button.bind(on_press=self.close_popup)
        button_row.add_widget(close_button)
        
        panel.add_widget(button_row)
        
        self.add_widget(panel)
    
    def _validate_audio_file(self):
        """
        Validate the recorded audio file for existence, size, and basic integrity
        
        Returns:
            tuple: (is_valid, status_message, message_level)
                - is_valid: True if file is considered valid
                - status_message: Description of file status
                - message_level: 'success', 'info', 'warning', or 'error'
        """
        try:
            if not self.audio_file_path.exists():
                return False, "Audiodatei wurde nicht erstellt", "error"
            
            file_size = self.audio_file_path.stat().st_size
            
            # Check if file is too small (less than 1KB indicates likely failure)
            if file_size < 1024:
                return False, f"Audiodatei ist zu klein ({file_size} Bytes) - möglicherweise unvollständig", "warning"
            
            # File exists and has reasonable size
            duration_estimate = ""
            if self.start_time:
                duration = time.time() - self.start_time
                duration_estimate = f" (ca. {duration:.1f}s)"
            
            size_mb = file_size / 1024 / 1024
            status_msg = f"Audiodatei erfolgreich gespeichert: {size_mb:.1f} MB{duration_estimate}"
            
            # Additional check: Try to verify it's a valid audio file by checking header
            try:
                with open(self.audio_file_path, 'rb') as f:
                    header = f.read(12)
                    if len(header) >= 12 and b'RIFF' in header and b'WAVE' in header:
                        return True, status_msg + " ✓ Gültiges WAV-Format", "success"
                    else:
                        return True, status_msg + " ⚠ Format unbekannt, aber Datei vorhanden", "info"
            except Exception:
                # Even if we can't read the header, if file exists and has size, consider it valid
                return True, status_msg, "success"
                
        except Exception as e:
            return False, f"Fehler bei der Dateivalidierung: {e}", "error"
    
    def _validate_audio_file_with_stability_check(self):
        """
        Enhanced validation that includes file stability check to prevent race conditions
        
        This function ensures the audio file is not only valid but also stable (completely written)
        before allowing the workflow to proceed. This prevents race conditions where voiceToGoogle.py
        starts processing an incomplete file.
        
        Returns:
            tuple: (is_valid, status_message, message_level)
        """
        import time
        
        try:
            # First, do the basic validation
            is_basic_valid, basic_msg, basic_level = self._validate_audio_file()
            
            if not is_basic_valid:
                return is_basic_valid, basic_msg, basic_level
            
            debug_logger.info("Basic validation passed, checking file stability...")
            
            # File stability check: ensure file size is not changing
            initial_size = self.audio_file_path.stat().st_size
            time.sleep(0.2)  # Wait 200ms
            
            try:
                final_size = self.audio_file_path.stat().st_size
                if initial_size != final_size:
                    debug_logger.warning(f"File size changed during stability check: {initial_size} -> {final_size}")
                    return False, f"Audiodatei noch nicht stabil (Größe ändert sich: {initial_size} -> {final_size} Bytes)", "warning"
            except Exception as e:
                debug_logger.warning(f"Error during stability check: {e}")
                return False, f"Fehler bei Stabilitätsprüfung: {e}", "error"
            
            # Try to open the file exclusively to ensure no other process is writing to it
            try:
                with open(self.audio_file_path, 'rb') as f:
                    # Try to acquire an exclusive lock (will fail if file is still being written)
                    try:
                        import fcntl
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Immediately release the lock
                        debug_logger.info("File lock test passed - file not being written")
                    except ImportError:
                        # fcntl not available on all systems, skip lock test
                        debug_logger.info("fcntl not available, skipping lock test")
                        pass
                    except OSError:
                        debug_logger.warning("File appears to be locked by another process")
                        return False, "Audiodatei wird noch von anderem Prozess verwendet", "warning"
                    
                    # Try to read the beginning and end of the file to ensure it's complete
                    f.seek(0)
                    header = f.read(12)
                    
                    # For WAV files, try to read the last few bytes
                    f.seek(-4, 2)  # Seek to 4 bytes from end
                    trailer = f.read(4)
                    
                    if not header or len(header) < 12:
                        return False, "Audiodatei-Header unvollständig", "warning"
                        
                    debug_logger.info(f"File stability check passed: header={len(header)} bytes, trailer={len(trailer)} bytes")
                    
            except Exception as e:
                debug_logger.warning(f"Error during file access check: {e}")
                # Don't fail validation just because we can't do advanced checks
                pass
            
            # All checks passed
            debug_logger.info("File stability check completed successfully")
            return True, basic_msg + " ✓ Datei stabil und bereit für Verarbeitung", "success"
            
        except Exception as e:
            debug_logger.error(f"Error during stability validation: {e}")
            return False, f"Fehler bei der erweiterten Dateivalidierung: {e}", "error"
    
    def _add_status_message(self, message, level="info"):
        """
        Add a status message with appropriate color coding
        
        Args:
            message: The message to display
            level: 'success', 'info', 'warning', or 'error'
        """
        color_map = {
            'success': '44ff44',
            'info': '4499ff', 
            'warning': 'ffaa44',
            'error': 'ff4444'
        }
        color = color_map.get(level, 'ffffff')
        self.add_output_text(f"[color={color}]{message}[/color]")

    def _update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
    
    def add_output_text(self, text):
        """Add text to the output display"""
        current = self.output_text.text
        if current == "Bereit für Aufnahme...":
            self.output_text.text = text
        else:
            self.output_text.text = current + "\n" + text
        
        # Update text_size for proper wrapping
        self.output_text.text_size = (dp(550), None)
    
    def toggle_recording(self, instance):
        """Toggle recording start/stop as requested"""
        debug_logger.info(f"toggle_recording called - current state: is_running={self.is_running}, process={self.process is not None}")
        
        if not self.is_running:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Start Aufnahme.py as subprocess"""
        debug_logger.info("start_recording called")
        
        if self.is_running:
            debug_logger.warning("start_recording called but recording already running")
            self.add_output_text("[color=ffaa44]Warnung: Aufnahme läuft bereits[/color]")
            return
            
        try:
            # Reset workflow state for new recording
            self.workflow_triggered = False
            if self.workflow_status_checker:
                Clock.unschedule(self.workflow_status_checker)
                self.workflow_status_checker = None
            debug_logger.info("Reset workflow state for new recording")
            
            aufnahme_path = APP_DIR / "Aufnahme.py"
            if not aufnahme_path.exists():
                error_msg = f"Fehler: Aufnahme.py nicht gefunden bei {aufnahme_path}"
                debug_logger.error(error_msg)
                print(error_msg)
                self.add_output_text(f"[color=ff4444]{error_msg}[/color]")
                return
            
            # Clear previous output
            self.output_text.text = "Starte Aufnahme..."
            debug_logger.info(f"Starting recording process with script: {aufnahme_path}")
            
            # Start the subprocess with output capture
            self.process = subprocess.Popen(
                ["python3", str(aufnahme_path)], 
                cwd=str(APP_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            
            self.is_running = True
            self.button.text = "Stopp"
            self.button.background_color = (0.6, 0.25, 0.25, 1)  # Red for stop
            self.start_time = time.time()
            self.start_timer()
            
            # Schedule output reading
            Clock.schedule_interval(self.read_process_output, 0.1)
            
            success_msg = f"Aufnahme gestartet (PID: {self.process.pid})"
            debug_logger.info(success_msg)
            print(success_msg)
            self.add_output_text(f"[color=44ff44]{success_msg}[/color]")
            
        except Exception as e:
            error_msg = f"Fehler beim Starten der Aufnahme: {e}"
            debug_logger.error(error_msg, exc_info=True)
            print(error_msg)
            self.add_output_text(f"[color=ff4444]{error_msg}[/color]")
            # Reset state on error
            self.is_running = False
            self.button.text = "Start"
            self.button.background_color = (0.25, 0.55, 0.25, 1)
    
    def read_process_output(self, dt):
        """Read output from the recording process with improved termination handling"""
        if not self.process or not self.is_running:
            return False  # Stop scheduling
            
        try:
            # Check if process is still running
            if self.process.poll() is not None:
                # Process ended, read final output
                final_output = self.process.stdout.read()
                if final_output:
                    self.add_output_text(final_output.strip())
                
                # Process ended - handle this gracefully without showing automatic error
                debug_logger.info(f"Recording process ended naturally with exit code: {self.process.returncode}")
                
                # Don't show error message here - let stop_recording handle the validation
                self.is_running = False
                self.button.text = "Start" 
                self.button.background_color = (0.25, 0.55, 0.25, 1)
                self.stop_timer()
                
                # Trigger validation through stop_recording method
                self.stop_recording()
                return False
            
            # Read available output without blocking
            import select
            import sys
            if hasattr(select, 'select'):  # Unix-like systems
                ready, _, _ = select.select([self.process.stdout], [], [], 0)
                if ready:
                    line = self.process.stdout.readline()
                    if line:
                        self.add_output_text(line.strip())
            else:
                # Fallback for systems without select
                try:
                    line = self.process.stdout.readline()
                    if line:
                        self.add_output_text(line.strip())
                except:
                    pass  # No output available
                    
        except Exception as e:
            debug_logger.error(f"Error reading process output: {e}")
            return False
        
        return True  # Continue scheduling
    
    def stop_recording(self):
        """Stop Aufnahme.py subprocess cleanly using SIGTERM with improved error handling"""
        debug_logger.info(f"stop_recording called - is_running: {self.is_running}, process: {self.process is not None}")
        
        # Validate recording state BEFORE attempting to stop
        if not self.is_running:
            debug_logger.warning("stop_recording called but no recording is running")
            self.add_output_text("[color=ffaa44]Warnung: Keine Aufnahme läuft[/color]")
            # Ensure UI state is correct
            self.button.text = "Start"
            self.button.background_color = (0.25, 0.55, 0.25, 1)
            self.stop_timer()
            return
            
        if not self.process:
            debug_logger.warning("stop_recording: is_running=True but process is None")
            # Reset inconsistent state
            self.is_running = False
            self.button.text = "Start"
            self.button.background_color = (0.25, 0.55, 0.25, 1)
            self.stop_timer()
            self.add_output_text("[color=ffaa44]Warnung: Inkonsistenter Zustand korrigiert[/color]")
            return
        
        stop_msg_starting = f"Stoppe Aufnahme (PID: {self.process.pid})..."
        debug_logger.info(stop_msg_starting)
        print(stop_msg_starting)
        self.add_output_text(f"[color=ffff44]{stop_msg_starting}[/color]")
        
        process_exit_code = None
        try:
            # Send SIGTERM for graceful shutdown as required
            debug_logger.info(f"Sending SIGTERM to process {self.process.pid}")
            self.process.terminate()
            
            # Wait for the process and capture final output
            try:
                stdout, stderr = self.process.communicate(timeout=10)
                process_exit_code = self.process.returncode
                
                if stdout:
                    debug_logger.debug(f"Recording stdout: {stdout[:200]}...")
                    self.add_output_text(stdout.strip())
                if stderr:
                    debug_logger.warning(f"Recording stderr: {stderr}")
                    self.add_output_text(f"[color=ffaa44]Warnung: {stderr.strip()}[/color]")
                    
            except subprocess.TimeoutExpired:
                # Force kill if terminate doesn't work within timeout
                timeout_msg = "Erzwinge Beendigung (Timeout)"
                debug_logger.warning(timeout_msg)
                print(timeout_msg)
                self.add_output_text(f"[color=ff4444]{timeout_msg}[/color]")
                self.process.kill()
                self.process.wait()
                process_exit_code = self.process.returncode
                
        except Exception as e:
            error_msg = f"Fehler beim Stoppen: {e}"
            debug_logger.error(error_msg, exc_info=True)
            print(error_msg)
            self.add_output_text(f"[color=ff4444]{error_msg}[/color]")
        finally:
            # Always clean up state
            self.process = None
        
        # Update state
        self.is_running = False
        self.button.text = "Start"
        self.button.background_color = (0.25, 0.55, 0.25, 1)  # Green for start
        self.stop_timer()
        
        # CRITICAL FIX: Wait for recording process to fully complete and ensure file stability
        debug_logger.info("Waiting for recording process to fully complete and file to be stable...")
        self.add_output_text("[color=4499ff]Warte auf vollständige Aufnahme-Beendigung...[/color]")
        
        # Wait a short time to ensure all file operations are complete
        import time
        time.sleep(0.5)  # Give the recording process time to fully close files
        
        # Validate audio file and ensure it's stable before triggering workflow
        debug_logger.info("Validating recorded audio file after completion wait...")
        is_valid, status_message, message_level = self._validate_audio_file_with_stability_check()
        
        if is_valid:
            # Audio file is valid and stable - this is success regardless of exit code
            debug_logger.info("Audio file validation successful - ready for workflow")
            print(f"✓ {status_message}")
            self._add_status_message(f"✓ {status_message}", "success")
            
            # Handle exit code information
            if process_exit_code is not None and process_exit_code != 0:
                # Exit code != 0 but file is valid - this is normal for recording tools stopped via signal
                info_msg = f"Hinweis: Prozess beendet mit Code {process_exit_code}, Audio jedoch erfolgreich gespeichert"
                debug_logger.info(info_msg)
                print(f"ℹ {info_msg}")
                self._add_status_message(f"ℹ {info_msg}", "info")
                self.add_output_text("[color=4499ff]Dies ist normal beim Stoppen von Aufnahme-Tools[/color]")
            else:
                success_msg = "Aufnahme erfolgreich abgeschlossen"
                debug_logger.info(success_msg)
                print(f"✓ {success_msg}")
            
            # CRITICAL FIX: Only create workflow trigger AFTER successful validation and file stability
            if not self.workflow_triggered:
                debug_logger.info("SAFE TO TRIGGER: Audio file validated and stable - creating workflow trigger")
                self.add_output_text("[color=44ff44]✓ Audio validiert und stabil - starte Workflow[/color]")
                self.create_workflow_trigger()
            else:
                debug_logger.info("Workflow already triggered for this recording, skipping")
                
        else:
            # Audio file is not valid - DO NOT trigger workflow
            debug_logger.error(f"Audio file validation failed - NOT triggering workflow: {status_message}")
            print(f"✗ {status_message}")
            self._add_status_message(f"✗ {status_message}", message_level)
            self.add_output_text("[color=ff4444]✗ Workflow NICHT gestartet - Audiodatei ungültig[/color]")
            
            if process_exit_code is not None and process_exit_code != 0:
                error_detail = f"Zusätzlich: Prozess beendet mit Fehlercode {process_exit_code}"
                debug_logger.error(error_detail)
                print(f"✗ {error_detail}")
                self._add_status_message(f"✗ {error_detail}", "error")
    
    def start_timer(self):
        """Start the timer display"""
        self.timer_event = Clock.schedule_interval(self.update_timer, 1)
    
    def stop_timer(self):
        """Stop the timer display"""
        if self.timer_event:
            Clock.unschedule(self.timer_event)
            self.timer_event = None
        self.timer_label.text = "00:00"
    
    def update_timer(self, dt):
        """Update timer display during recording"""
        if self.is_running and self.start_time:
            elapsed = int(time.time() - self.start_time)
            minutes, seconds = divmod(elapsed, 60)
            self.timer_label.text = f"{minutes:02d}:{seconds:02d}"
    
    def create_workflow_trigger(self):
        """Create workflow trigger file to signal background processing - ATOMIC OPERATION"""
        # Use thread lock to prevent race conditions from multiple button clicks
        with self.trigger_creation_lock:
            if self.workflow_triggered:
                warning_msg = "Workflow-Trigger bereits erstellt, überspringe"
                debug_logger.warning(warning_msg)
                print(warning_msg)
                self.add_output_text(f"[color=ffaa44]{warning_msg}[/color]")
                return
            
            try:
                trigger_file = APP_DIR / "workflow_trigger.txt"
                lockfile_path = APP_DIR / "workflow_service.lock"
                
                debug_logger.info(f"Attempting to create trigger file: {trigger_file}")
                
                # Check if workflow service is already running via lockfile
                if lockfile_path.exists():
                    try:
                        lock_stat = lockfile_path.stat()
                        lock_age = time.time() - lock_stat.st_mtime
                        if lock_age < 300:  # Less than 5 minutes old
                            warning_msg = "Workflow-Service läuft bereits (Lockfile aktiv)"
                            debug_logger.warning(f"{warning_msg}, lock age: {lock_age:.1f}s")
                            print(warning_msg)
                            self.add_output_text(f"[color=ffaa44]{warning_msg}[/color]")
                            return
                        else:
                            debug_logger.info(f"Removing stale lockfile (age: {lock_age:.1f}s)")
                            lockfile_path.unlink()
                    except Exception as e:
                        debug_logger.warning(f"Error checking lockfile: {e}")
                
                # Check if trigger file already exists and handle appropriately
                if trigger_file.exists():
                    try:
                        trigger_stat = trigger_file.stat()
                        trigger_age = time.time() - trigger_stat.st_mtime
                        if trigger_age < 60:  # Less than 1 minute old - probably still processing
                            warning_msg = "Workflow-Trigger-Datei existiert bereits und ist aktuell"
                            debug_logger.warning(f"{warning_msg}, age: {trigger_age:.1f}s")
                            print(warning_msg)
                            self.add_output_text(f"[color=ffaa44]{warning_msg}[/color]")
                            return
                        else:
                            # Old trigger file - remove it
                            debug_logger.info(f"Removing stale trigger file (age: {trigger_age:.1f}s)")
                            trigger_file.unlink()
                    except Exception as e:
                        debug_logger.warning(f"Error checking existing trigger file: {e}")
                        # Try to remove it anyway
                        try:
                            trigger_file.unlink()
                        except Exception:
                            pass
                
                # Atomic trigger file creation with exclusive lock
                trigger_created = False
                try:
                    # Use exclusive creation (fails if exists)
                    with open(trigger_file, "x", encoding="utf-8") as f:
                        # Get exclusive lock on the file
                        try:
                            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                            f.write("run")
                            f.flush()
                            os.fsync(f.fileno())  # Ensure data is written to disk
                            trigger_created = True
                            debug_logger.info("Trigger file created atomically with lock")
                        except (OSError, IOError) as lock_err:
                            debug_logger.error(f"Failed to lock trigger file: {lock_err}")
                            raise
                        finally:
                            # Lock is automatically released when file is closed
                            pass
                            
                except FileExistsError:
                    warning_msg = "Workflow-Trigger-Datei existiert bereits (von anderem Prozess erstellt)"
                    debug_logger.warning(warning_msg)
                    print(warning_msg)
                    self.add_output_text(f"[color=ffaa44]{warning_msg}[/color]")
                    return
                
                if not trigger_created:
                    raise Exception("Failed to create trigger file atomically")
                
                # Mark as triggered ONLY after successful creation
                self.workflow_triggered = True
                
                trigger_msg = "Workflow-Trigger erstellt"
                debug_logger.info(trigger_msg)
                print(trigger_msg)
                self.add_output_text(f"[color=44ff44]{trigger_msg}[/color]")
                
                # Start workflow service ONCE using the existing script
                self._start_workflow_service()
                
                # Start checking for workflow status (but stop any existing checker first)
                if self.workflow_status_checker:
                    Clock.unschedule(self.workflow_status_checker)
                
                self.workflow_status_checker = Clock.schedule_interval(self.check_workflow_status, 2.0)
                debug_logger.info("Started workflow status checking")
                
            except Exception as e:
                error_msg = f"Fehler beim Erstellen des Workflow-Triggers: {e}"
                debug_logger.error(error_msg, exc_info=True)
                print(error_msg)
                self.add_output_text(f"[color=ff4444]{error_msg}[/color]")
                # Reset trigger state on error
                self.workflow_triggered = False
    
    def _start_workflow_service(self):
        """Start the workflow service using the existing start_workflow_service.py script"""
        try:
            service_script = APP_DIR / "start_workflow_service.py"
            if not service_script.exists():
                debug_logger.error(f"Workflow service script not found: {service_script}")
                return
            
            debug_logger.info("Starting workflow service via start_workflow_service.py")
            
            # Start the service script with --auto flag for non-interactive mode
            service_process = subprocess.Popen(
                ["python3", str(service_script), "--auto"],
                cwd=str(APP_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Wait briefly to see if it starts successfully
            try:
                stdout, stderr = service_process.communicate(timeout=5)
                if service_process.returncode == 0:
                    service_msg = "Workflow-Service erfolgreich gestartet"
                    debug_logger.info(service_msg)
                    print(service_msg)
                    self.add_output_text(f"[color=44ff44]{service_msg}[/color]")
                else:
                    error_msg = f"Workflow-Service Start-Fehler (Code: {service_process.returncode})"
                    debug_logger.warning(f"{error_msg}\nSTDOUT: {stdout}\nSTDERR: {stderr}")
                    print(error_msg)
                    self.add_output_text(f"[color=ffaa44]{error_msg}[/color]")
                    if stdout:
                        self.add_output_text(f"[color=cccccc]Output: {stdout.strip()}[/color]")
            except subprocess.TimeoutExpired:
                # Service is still running, which is normal
                service_msg = f"Workflow-Service gestartet (läuft im Hintergrund)"
                debug_logger.info(service_msg)
                print(service_msg)
                self.add_output_text(f"[color=44ff44]{service_msg}[/color]")
            
        except Exception as e:
            error_msg = f"Fehler beim Starten des Workflow-Service: {e}"
            debug_logger.error(error_msg, exc_info=True)
            print(error_msg)
            self.add_output_text(f"[color=ff4444]{error_msg}[/color]")
    
    def check_workflow_status(self, dt):
        """Check workflow status from log file"""
        try:
            status_file = APP_DIR / "workflow_status.log"
            if status_file.exists():
                with open(status_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    # Show last few lines of status
                    lines = content.split('\n')
                    for line in lines[-3:]:  # Show last 3 lines
                        if line.strip():
                            workflow_status_msg = f"[Workflow] {line.strip()}"
                            print(workflow_status_msg)
                            self.add_output_text(f"[color=aaaaff]{workflow_status_msg}[/color]")
                    
                    # Check if workflow completed
                    if "WORKFLOW_COMPLETE" in content or "WORKFLOW_ERROR" in content:
                        Clock.unschedule(self.check_workflow_status)
                        self.workflow_status_checker = None  # Clear reference
                        
                        # Clean up trigger file after workflow completion
                        trigger_file = APP_DIR / "workflow_trigger.txt"
                        if trigger_file.exists():
                            try:
                                trigger_file.unlink()
                                cleanup_msg = "Workflow-Trigger-Datei nach Abschluss gelöscht"
                                debug_logger.info(cleanup_msg)
                                print(cleanup_msg)
                                self.add_output_text(f"[color=44ff44]{cleanup_msg}[/color]")
                            except Exception as cleanup_err:
                                cleanup_warning = f"Warnung: Trigger-Datei konnte nicht gelöscht werden: {cleanup_err}"
                                debug_logger.warning(cleanup_warning)
                                print(cleanup_warning)
                                self.add_output_text(f"[color=ffaa44]{cleanup_warning}[/color]")
                        
                        # Reset workflow triggered flag for next recording
                        self.workflow_triggered = False
                        debug_logger.info("Reset workflow state for next recording")
                        
                        workflow_complete_msg = "Workflow abgeschlossen"
                        print(workflow_complete_msg)
                        self.add_output_text(f"[color=44ff44]{workflow_complete_msg}[/color]")
                        return False  # Stop scheduling
                        
        except Exception as e:
            print(f"Fehler beim Lesen der Workflow-Status: {e}")
            
        return True  # Continue scheduling
    
    def close_popup(self, instance):
        """Close the popup window"""
        debug_logger.info("close_popup called")
        
        # Stop recording if running
        if self.is_running:
            debug_logger.info("Stopping recording before closing popup")
            self.stop_recording()
        
        # Stop status checking
        if self.workflow_status_checker:
            Clock.unschedule(self.workflow_status_checker)
            self.workflow_status_checker = None
            debug_logger.info("Stopped workflow status checking")
        
        # Remove from parent
        if self.parent:
            self.parent.remove_widget(self)
            debug_logger.info("Removed popup from parent widget")
    
    def show_qr_code(self, instance):
        """Show QR code popup for upload server"""
        debug_logger.info("show_qr_code called")
        
        # Check if upload server is running
        if not upload_server.running:
            self.add_output_text("[color=ffaa44]⚠ Upload-Server ist nicht aktiv[/color]")
            return
        
        # Create QR code popup
        qr_popup = QRCodePopup(upload_server)
        if self.parent:
            self.parent.add_widget(qr_popup)

class QRCodePopup(FloatLayout):
    """Popup window to display QR code for upload server"""
    
    def __init__(self, upload_server_instance, **kwargs):
        super().__init__(**kwargs)
        self.upload_server = upload_server_instance
        
        # Background
        with self.canvas.before:
            Color(0, 0, 0, 0.8)
            self.bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        
        # Main panel
        panel = BoxLayout(
            orientation='vertical',
            size_hint=(None, None),
            size=(dp(400), dp(500)),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            padding=dp(20),
            spacing=dp(15)
        )
        
        with panel.canvas.before:
            Color(0.16, 0.16, 0.20, 0.95)
            panel._bg = Rectangle(pos=panel.pos, size=panel.size)
        panel.bind(pos=lambda *a: setattr(panel._bg, 'pos', panel.pos),
                  size=lambda *a: setattr(panel._bg, 'size', panel.size))
        
        # Title
        title = Label(
            text="📱 Upload QR-Code",
            size_hint_y=None,
            height=dp(40),
            font_size=dp(24),
            color=(1, 1, 1, 1)
        )
        panel.add_widget(title)
        
        # Server info
        url = self.upload_server.get_qr_url()
        info_text = f"Server läuft auf Port {self.upload_server.port}\n{url}"
        info_label = Label(
            text=info_text,
            size_hint_y=None,
            height=dp(60),
            font_size=dp(16),
            color=(0.9, 0.9, 0.9, 1),
            halign='center'
        )
        info_label.bind(size=lambda inst, *args: setattr(inst, 'text_size', (inst.width, None)))
        panel.add_widget(info_label)
        
        # QR Code image area
        qr_image_widget = Label(
            text="🔄 QR-Code wird generiert...",
            size_hint_y=None,
            height=dp(200),
            font_size=dp(18),
            color=(0.8, 0.8, 0.8, 1)
        )
        
        # Try to generate and display QR code
        if QR_CODE_AVAILABLE:
            try:
                qr_path = self.upload_server.generate_qr_code()
                if qr_path:
                    # Replace label with actual QR code image
                    qr_image_widget = Image(
                        source=qr_path,
                        size_hint_y=None,
                        height=dp(200)
                    )
                else:
                    qr_image_widget.text = "❌ QR-Code konnte nicht generiert werden"
            except Exception as e:
                debug_logger.error(f"Error creating QR code widget: {e}")
                qr_image_widget.text = f"❌ Fehler: {str(e)}"
        else:
            qr_image_widget.text = "❌ QR-Code Bibliothek nicht verfügbar\nURL manuell eingeben:\n" + url
            qr_image_widget.height = dp(100)
        
        panel.add_widget(qr_image_widget)
        
        # Instructions
        instructions = Label(
            text="📲 QR-Code mit Handy scannen\noder URL im Browser öffnen",
            size_hint_y=None,
            height=dp(50),
            font_size=dp(14),
            color=(0.8, 0.8, 0.8, 1),
            halign='center'
        )
        instructions.bind(size=lambda inst, *args: setattr(inst, 'text_size', (inst.width, None)))
        panel.add_widget(instructions)
        
        # Close button
        close_button = Button(
            text="Schließen",
            size_hint_y=None,
            height=dp(50),
            background_normal='',
            background_color=(0.4, 0.4, 0.45, 1),
            color=(1, 1, 1, 1),
            font_size=dp(20)
        )
        close_button.bind(on_press=self.close_popup)
        panel.add_widget(close_button)
        
        self.add_widget(panel)
    
    def _update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
    
    def close_popup(self, instance):
        """Close the QR code popup"""
        if self.parent:
            self.parent.remove_widget(self)
class GeneralSettingsPopup(FloatLayout):
    def __init__(self, slideshow, **kw):
        super().__init__(**kw)
        self.slideshow=slideshow
        with self.canvas.before:
            Color(0,0,0,0.55); self.bg=Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=self._upd,size=self._upd)
        panel=BoxLayout(orientation='vertical',size_hint=(None,None),
                        size=(dp(520),dp(420)),
                        pos_hint={'center_x':0.5,'center_y':0.5},
                        padding=dp(22),spacing=dp(16))
        with panel.canvas.before:
            Color(0.18,0.18,0.22,0.97); panel._bg=Rectangle(pos=panel.pos,size=panel.size)
        panel.bind(pos=lambda *a:setattr(panel._bg,'pos',panel.pos),
                   size=lambda *a:setattr(panel._bg,'size',panel.size))
        panel.add_widget(Label(text="Allgemein",size_hint_y=None,height=dp(54),
                               font_size=dp(30),color=(1,1,1,1)))
        # Globale Helligkeit
        panel.add_widget(Label(text="Globale Helligkeit (50% - 150%):",size_hint_y=None,height=dp(28),
                               font_size=dp(16),color=(1,1,1,0.9)))
        cur = self.slideshow.global_brightness_override or 1.0
        self.b_slider=Slider(min=0.5,max=1.5,value=cur,step=0.01,size_hint_y=None,height=dp(42))
        self.b_label=Label(text=f"{cur*100:.0f}%",size_hint_y=None,height=dp(24),
                           font_size=dp(16),color=(0.9,0.9,1,1))
        self.b_slider.bind(value=lambda inst,val:self.b_label.__setattr__('text',f"{float(val)*100:.0f}%"))
        panel.add_widget(self.b_slider)
        panel.add_widget(self.b_label)
        # Buttons
        row=BoxLayout(size_hint_y=None,height=dp(60),spacing=dp(14))
        save=Button(text="Speichern",background_normal='',background_color=(0.25,0.55,0.25,1),
                    color=(1,1,1,1),font_size=dp(20))
        back=Button(text="Zurück",background_normal='',background_color=(0.4,0.4,0.5,1),
                    color=(1,1,1,1),font_size=dp(20))
        save.bind(on_release=lambda *_: self._save())
        back.bind(on_release=lambda *_: self._back())
        row.add_widget(save); row.add_widget(back)
        panel.add_widget(row)
        self.add_widget(panel)
    def _upd(self,*a):
        self.bg.pos=self.pos; self.bg.size=self.size
    def _save(self):
        val=float(self.b_slider.value)
        if abs(val-1.0)<0.001:
            self.slideshow.global_brightness_override=None
        else:
            self.slideshow.global_brightness_override=val
        self.slideshow.persist_meta()
        self.slideshow._apply_current_brightness()
        self._back()
    def _back(self):
        self.slideshow.open_single(SettingsRootPopup(self.slideshow))

class GlobalDurationPopup(FloatLayout):
    def __init__(self, slideshow, **kw):
        super().__init__(**kw)
        self.slideshow=slideshow
        with self.canvas.before:
            Color(0,0,0,0.55); self.bg=Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=self._upd,size=self._upd)
        panel=BoxLayout(orientation='vertical',size_hint=(None,None),
                        size=(dp(520),dp(380)),
                        pos_hint={'center_x':0.5,'center_y':0.5},
                        padding=dp(22),spacing=dp(16))
        with panel.canvas.before:
            Color(0.18,0.18,0.22,0.97); panel._bg=Rectangle(pos=panel.pos,size=panel.size)
        panel.bind(pos=lambda *a:setattr(panel._bg,'pos',panel.pos),
                   size=lambda *a:setattr(panel._bg,'size',panel.size))
        panel.add_widget(Label(text="Bilddauer",size_hint_y=None,height=dp(54),
                               font_size=dp(30),color=(1,1,1,1)))
        panel.add_widget(Label(text="Globale Bilddauer (Sek, 0 = deaktiviert):",size_hint_y=None,height=dp(30),
                               font_size=dp(16),color=(1,1,1,0.9)))
        cur = self.slideshow.global_interval_override or 0
        self.gl_slider=Slider(min=0,max=120,value=cur,step=1,size_hint_y=None,height=dp(42))
        self.gl_label=Label(text=f"{cur}s" if cur>0 else "Deaktiviert",
                            size_hint_y=None,height=dp(24),
                            font_size=dp(16),color=(0.9,0.9,1,1))
        self.gl_slider.bind(value=lambda inst,val:self.gl_label.__setattr__('text', f"{int(val)}s" if int(val)>0 else "Deaktiviert"))
        panel.add_widget(self.gl_slider); panel.add_widget(self.gl_label)
        row=BoxLayout(size_hint_y=None,height=dp(60),spacing=dp(14))
        save=Button(text="Speichern",background_normal='',background_color=(0.25,0.55,0.25,1),
                    color=(1,1,1,1),font_size=dp(20))
        back=Button(text="Zurück",background_normal='',background_color=(0.4,0.4,0.5,1),
                    color=(1,1,1,1),font_size=dp(20))
        save.bind(on_release=lambda *_: self._save())
        back.bind(on_release=lambda *_: self._back())
        row.add_widget(save); row.add_widget(back)
        panel.add_widget(row)
        self.add_widget(panel)
    def _upd(self,*a):
        self.bg.pos=self.pos; self.bg.size=self.size
    def _save(self):
        v=int(self.gl_slider.value)
        self.slideshow.global_interval_override = v if v>0 else None
        self.slideshow.persist_meta()
        self.slideshow._reschedule_for_current()
        self._back()
    def _back(self):
        self.slideshow.open_single(SettingsRootPopup(self.slideshow))

# ---- Gallery Editor / Tiles (angepasst) ----
class ImageTile(BoxLayout):
    def __init__(self, path, on_toggle, is_selected_fn, open_settings, **kw):
        super().__init__(orientation="vertical",
                         size_hint=(None,None), width=THUMB_SIZE,
                         height=THUMB_SIZE+dp(60), spacing=dp(4), **kw)
        self.path=path
        self.on_toggle=on_toggle
        self.open_settings=open_settings
        self.is_selected_fn=is_selected_fn
        with self.canvas.before:
            Color(0.18,0.18,0.20,1)
            self.bg_rect=Rectangle(pos=self.pos,size=self.size)
            self.sel_color=Color(0,0.7,0,0)
            self.sel_line=Line(rectangle=(self.x,self.y,self.width,self.height),width=2)
        self.bind(pos=self._upd,size=self._upd)
        self.img=Image(source=path,size_hint=(1,None),height=THUMB_SIZE)
        self.add_widget(self.img)
        name=os.path.basename(path)
        self.lbl=Label(text=self._short(name),size_hint=(1,None),height=dp(26),
                       halign='center',valign='middle',color=(1,1,1,1),font_size=dp(13))
        self.lbl.bind(size=lambda inst,*a:setattr(inst,'text_size',inst.size))
        self.add_widget(self.lbl)
        row=BoxLayout(size_hint=(1,None),height=dp(30),spacing=dp(4))
        self.toggle_btn=Button(text="Auswählen",background_normal='',
                               background_color=(0.25,0.35,0.55,1),
                               color=(1,1,1,1),font_size=dp(12))
        self.toggle_btn.bind(on_release=lambda *_: self.on_toggle(self.path))
        gear=Button(text="⚙",size_hint=(None,1),width=dp(36),
                    background_normal='',background_color=(0.35,0.35,0.5,1),
                    color=(1,1,1,1),font_size=dp(16))
        gear.bind(on_release=lambda *_: self.open_settings(self.path))
        row.add_widget(self.toggle_btn); row.add_widget(gear)
        self.add_widget(row)
        self.refresh_state()
    def _short(self,name,maxlen=18):
        return name if len(name)<=maxlen else name[:maxlen-3]+"..."
    def _upd(self,*a):
        self.bg_rect.pos=self.pos; self.bg_rect.size=self.size
        self.sel_line.rectangle=(self.x,self.y,self.width,self.height)
    def refresh_state(self):
        sel=self.is_selected_fn(self.path)
        if sel:
            self.sel_color.rgba=(0.1,0.8,0.1,1)
            self.toggle_btn.text="Entfernen"
            self.toggle_btn.background_color=(0.4,0.25,0.25,1)
        else:
            self.sel_color.rgba=(0,0.7,0,0)
            self.toggle_btn.text="Auswählen"
            self.toggle_btn.background_color=(0.25,0.35,0.55,1)

class GalleryEditor(FloatLayout):
    def __init__(self, slideshow, **kw):
        super().__init__(**kw)
        self.slideshow=slideshow
        self.manager=slideshow.mode_manager
        self.target_mode=None
        self.filter_selected_only=False
        self.has_changes=False
        with self.canvas.before:
            Color(0,0,0,0.7)
            self.bg=Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=lambda *a:(setattr(self.bg,'pos',self.pos),setattr(self.bg,'size',self.size)))
        root=BoxLayout(orientation="horizontal",size_hint=(0.95,0.92),
                       pos_hint={"center_x":0.5,"center_y":0.5},spacing=dp(18))
        with root.canvas.before:
            Color(0.14,0.14,0.17,0.95)
            self.inner_bg=Rectangle(pos=root.pos,size=root.size)
        root.bind(pos=lambda *a:setattr(self.inner_bg,'pos',root.pos),
                  size=lambda *a:setattr(self.inner_bg,'size',root.size))
        left=BoxLayout(orientation="vertical",size_hint=(0.22,1),spacing=dp(12),padding=dp(6))
        left.add_widget(Label(text="Modi",size_hint_y=None,height=dp(40),
                              font_size=dp(24),color=(1,1,1,1)))
        self.mode_box=BoxLayout(orientation="vertical",spacing=dp(8),size_hint_y=None)
        ms=ScrollView(); ms.add_widget(self.mode_box); left.add_widget(ms)
        self.status_lbl=Label(text="Modus wählen",size_hint_y=None,height=dp(40),
                              font_size=dp(16),color=(1,1,1,0.85))
        left.add_widget(self.status_lbl)
        
        # Save button (initially hidden)
        self.save_btn=Button(text="Speichern",size_hint_y=None,height=dp(60),
                            font_size=dp(22),background_normal='',
                            background_color=(0.25,0.55,0.25,1),color=(1,1,1,1),
                            opacity=0,disabled=True)
        self.save_btn.bind(on_release=lambda *_: self.save_changes())
        left.add_widget(self.save_btn)
        
        # Feedback label (initially hidden)
        self.feedback_lbl=Label(text="",size_hint_y=None,height=dp(30),
                               font_size=dp(16),color=(0.2,0.8,0.2,1),
                               opacity=0)
        left.add_widget(self.feedback_lbl)
        
        close_btn=Button(text="Schließen",size_hint_y=None,height=dp(60),
                         font_size=dp(22),background_normal='',
                         background_color=(0.4,0.4,0.45,1),color=(1,1,1,1))
        close_btn.bind(on_release=lambda *_: self.close())
        left.add_widget(close_btn)
        right=BoxLayout(orientation="vertical",size_hint=(0.78,1),spacing=dp(10),padding=[0,6,6,6])
        header=BoxLayout(size_hint_y=None,height=dp(46),spacing=dp(12))
        header.add_widget(Label(text="Alle Bilder im Ordner",font_size=dp(24),color=(1,1,1,1)))
        self.filter_btn=Button(text="Nur Modus-Bilder: AUS",size_hint=(None,1),width=dp(260),
                               background_normal='',background_color=(0.25,0.35,0.55,1),
                               color=(1,1,1,1),font_size=dp(16))
        self.filter_btn.bind(on_release=self.toggle_filter)
        header.add_widget(self.filter_btn)
        right.add_widget(header)
        from kivy.uix.gridlayout import GridLayout
        self.gallery_grid=GridLayout(cols=4,spacing=dp(14),padding=dp(6),size_hint_y=None)
        self.gallery_grid.bind(minimum_height=lambda inst,val:setattr(inst,'height',val))
        gs=ScrollView(); gs.add_widget(self.gallery_grid); right.add_widget(gs)
        root.add_widget(left); root.add_widget(right)
        self.add_widget(root)
        self.all_images_cache=[]
        self._build_modes()
        self._reload_all_images()
        self._populate()
    def _build_modes(self):
        self.mode_box.clear_widgets(); h=0
        for m in self.manager.modes:
            if m.name in ("Alle Bilder","Standard"): continue
            btn=Button(text=m.name,size_hint_y=None,height=dp(70),
                       background_normal='',background_color=(0.25,0.28,0.33,1),
                       color=(1,1,1,1),font_size=dp(20))
            btn.bind(on_release=lambda inst,mm=m:self.select_mode(mm))
            self.mode_box.add_widget(btn); h+=btn.height+dp(8)
        self.mode_box.height=h if h>10 else 10
    def select_mode(self,mode):
        # Reset changes when switching modes
        self.has_changes=False
        self._hide_save_button()
        
        self.target_mode=mode
        self.status_lbl.text=f"Modus: {mode.name}"
        self._populate()
    def toggle_filter(self,*_):
        self.filter_selected_only=not self.filter_selected_only
        self.filter_btn.text="Nur Modus-Bilder: AN" if self.filter_selected_only else "Nur Modus-Bilder: AUS"
        self._populate()
    def _reload_all_images(self):
        if IMAGE_DIR.exists():
            files=[str(p) for p in IMAGE_DIR.iterdir()
                   if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
            files.sort()
        else: files=[]
        if len(files)>MAX_IMAGES_DISPLAY: files=files[:MAX_IMAGES_DISPLAY]
        self.all_images_cache=files
        
    def _sync_image_lists_with_folder(self):
        """Remove non-existing images from all modes and provide feedback"""
        if not IMAGE_DIR.exists():
            return
        
        existing_files = set(self.all_images_cache)
        total_removed = 0
        
        # Check and clean all modes
        for mode in self.manager.modes:
            if not mode.images:
                continue
            
            removed_from_mode = []
            for img_path in mode.images[:]:  # Copy list to iterate safely
                if img_path not in existing_files:
                    mode.images.remove(img_path)
                    removed_from_mode.append(img_path)
            
            total_removed += len(removed_from_mode)
        
        # Save changes if any images were removed
        if total_removed > 0:
            self.manager.save()
            # Show feedback about removed images
            feedback_msg = f"{total_removed} nicht existierende Bilder entfernt"
            self._show_feedback(feedback_msg)
        
        return total_removed
    def _is_selected(self,path):
        return self.target_mode and path in self.target_mode.images
    def _toggle(self,path):
        if not self.target_mode:
            self.status_lbl.text="Bitte Modus links wählen."; return
        if path in self.target_mode.images:
            self.target_mode.images.remove(path)
        else:
            self.target_mode.images.append(path)
        
        # Track changes and show save button
        self.has_changes=True
        self._show_save_button()
        
        for tile in self.gallery_grid.children:
            if isinstance(tile,ImageTile) and tile.path==path: tile.refresh_state()
        self._update_count()
    def _open_settings(self,path):
        popup=ImageSettingsPopup(path,self.slideshow,
                                 on_close=None,
                                 on_deleted=lambda p: self._after_delete_refresh())
        self.add_widget(popup)
    def _after_delete_refresh(self):
        self._reload_all_images()
        self._populate()
        if self.slideshow.current_mode:
            self.slideshow.set_mode(self.slideshow.current_mode.name, manual=True)
    def _update_count(self):
        if self.target_mode:
            self.status_lbl.text=f"Modus: {self.target_mode.name} | {len(self.target_mode.images)} Bild(er)"
    
    def _show_save_button(self):
        """Show the save button with animation"""
        if self.save_btn.opacity == 0:
            self.save_btn.disabled=False
            from kivy.animation import Animation
            Animation(opacity=1, d=0.3).start(self.save_btn)
    
    def _hide_save_button(self):
        """Hide the save button with animation"""
        from kivy.animation import Animation
        def _disable(*_):
            self.save_btn.disabled=True
        anim = Animation(opacity=0, d=0.3)
        anim.bind(on_complete=_disable)
        anim.start(self.save_btn)
    
    def save_changes(self):
        """Save all changes and refresh the slideshow"""
        if not self.has_changes or not self.target_mode:
            return
        
        # Save to file
        self.manager.save()
        
        # Sync image lists after save to remove any non-existing files
        self._sync_image_lists_with_folder()
        
        # Update slideshow if current mode matches target mode
        if self.slideshow.current_mode and self.slideshow.current_mode.name==self.target_mode.name:
            self.slideshow.set_mode(self.target_mode.name, manual=True)
        
        # Reset changes flag and hide save button
        self.has_changes=False
        self._hide_save_button()
        
        # Show feedback
        self._show_feedback("Gespeichert!")
    
    def _show_feedback(self, message):
        """Show temporary feedback message"""
        self.feedback_lbl.text=message
        from kivy.animation import Animation
        from kivy.clock import Clock
        
        # Show feedback
        Animation(opacity=1, d=0.3).start(self.feedback_lbl)
        
        # Hide after 2 seconds
        def hide_feedback(dt):
            Animation(opacity=0, d=0.3).start(self.feedback_lbl)
        Clock.schedule_once(hide_feedback, 2.0)
    def _populate(self):
        self.gallery_grid.clear_widgets()
        if not self.all_images_cache: self._reload_all_images()
        imgs=self.all_images_cache
        if self.filter_selected_only and self.target_mode:
            imgs=[p for p in imgs if p in self.target_mode.images]
        for p in imgs:
            self.gallery_grid.add_widget(ImageTile(p,self._toggle,self._is_selected,self._open_settings))
        self._update_count()
    
    
    def close(self):
        if self.parent: self.parent.remove_widget(self)
        if self.slideshow.current_overlay is self:
            self.slideshow.current_overlay=None

# ---- TimePicker & ScheduleEditor (wie zuvor) ----
class TimePickerPopup(FloatLayout):
    def __init__(self,title,sh,sm,eh,em,on_save,on_cancel,**kw):
        super().__init__(**kw)
        self.on_save=on_save; self.on_cancel=on_cancel
        with self.canvas.before:
            Color(0,0,0,0.65); self.bg=Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=lambda *a:(setattr(self.bg,'pos',self.pos),setattr(self.bg,'size',self.size)))
        panel=BoxLayout(orientation='vertical',size_hint=(0.75,0.7),
                        pos_hint={'center_x':0.5,'center_y':0.5},
                        spacing=dp(14),padding=dp(18))
        with panel.canvas.before:
            Color(0.16,0.16,0.2,0.97); self.pbg=Rectangle(pos=panel.pos,size=panel.size)
        panel.bind(pos=lambda *a:setattr(self.pbg,'pos',panel.pos),
                   size=lambda *a:setattr(self.pbg,'size',panel.size))
        panel.add_widget(Label(text=title,size_hint_y=None,height=dp(48),
                               font_size=dp(30),color=(1,1,1,1)))
        self.start_h=Slider(min=0,max=23,value=sh,step=1)
        self.start_m=Slider(min=0,max=59,value=sm,step=1)
        self.end_h=Slider(min=0,max=23,value=eh,step=1)
        self.end_m=Slider(min=0,max=59,value=em,step=1)
        def row(lbl,s):
            b=BoxLayout(orientation='vertical',size_hint_y=None,height=dp(90))
            b.add_widget(Label(text=lbl,size_hint_y=None,height=dp(28),
                               font_size=dp(20),color=(1,1,1,1)))
            b.add_widget(s)
            val=Label(text=str(int(s.value)),size_hint_y=None,height=dp(28),
                      font_size=dp(18),color=(0.8,0.8,0.9,1))
            s.bind(value=lambda inst,value,val_label=val:setattr(val_label,'text',str(int(value))))
            b.add_widget(val); return b
        for lab,sl in [("Start Stunde",self.start_h),("Start Minute",self.start_m),
                       ("Ende Stunde",self.end_h),("Ende Minute",self.end_m)]:
            panel.add_widget(row(lab,sl))
        self.preview=Label(text="",size_hint_y=None,height=dp(40),
                           font_size=dp(20),color=(0.9,0.9,1,1))
        panel.add_widget(self.preview)
        def upd(*_):
            self.preview.text=f"{int(self.start_h.value):02d}:{int(self.start_m.value):02d}  ->  {int(self.end_h.value):02d}:{int(self.end_m.value):02d}"
        for s in [self.start_h,self.start_m,self.end_h,self.end_m]:
            s.bind(value=lambda inst,val:upd())
        upd()
        btn_row=BoxLayout(size_hint_y=None,height=dp(70),spacing=dp(16))
        ok=Button(text="Übernehmen",background_normal='',background_color=(0.25,0.45,0.25,1),
                  color=(1,1,1,1),font_size=dp(22))
        cancel=Button(text="Abbrechen",background_normal='',background_color=(0.4,0.35,0.35,1),
                      color=(1,1,1,1),font_size=dp(22))
        ok.bind(on_release=lambda *_: self._save())
        cancel.bind(on_release=lambda *_: self._cancel())
        btn_row.add_widget(ok); btn_row.add_widget(cancel); panel.add_widget(btn_row)
        self.add_widget(panel)
    def _save(self):
        sh,sm=int(self.start_h.value),int(self.start_m.value)
        eh,em=int(self.end_h.value),int(self.end_m.value)
        self.on_save(f"{sh:02d}:{sm:02d}", f"{eh:02d}:{em:02d}")
        if self.parent: self.parent.remove_widget(self)
    def _cancel(self):
        self.on_cancel()
        if self.parent: self.parent.remove_widget(self)

class ScheduleEditor(FloatLayout):
    def __init__(self, slideshow, **kw):
        super().__init__(**kw)
        self.slideshow=slideshow
        self.manager=slideshow.mode_manager
        self.mode_rows={}
        with self.canvas.before:
            Color(0,0,0,0.65); self.bg=Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=lambda *a:(setattr(self.bg,'pos',self.pos),setattr(self.bg,'size',self.size)))
        panel=BoxLayout(orientation="vertical",size_hint=(0.7,0.6),
                        pos_hint={"center_x":0.5,"center_y":0.5},
                        spacing=dp(16),padding=dp(20))
        with panel.canvas.before:
            Color(0.16,0.16,0.2,0.97); self.pbg=Rectangle(pos=panel.pos,size=panel.size)
        panel.bind(pos=lambda *a:setattr(self.pbg,'pos',panel.pos),
                   size=lambda *a:setattr(self.pbg,'size',panel.size))
        panel.add_widget(Label(text="Zeitplan Tag / Nacht",
                               size_hint_y=None,height=dp(50),
                               font_size=dp(30),color=(1,1,1,1)))
        for name in ("Tag","Nacht"): panel.add_widget(self._row(name))
        self.status_lbl=Label(text="",size_hint_y=None,height=dp(40),
                              font_size=dp(18),color=(1,0.7,0.4,1))
        panel.add_widget(self.status_lbl)
        buttons=BoxLayout(size_hint_y=None,height=dp(70),spacing=dp(20))
        save=Button(text="Speichern & Schließen",font_size=dp(22),
                    background_normal='',background_color=(0.25,0.45,0.25,1),
                    color=(1,1,1,1))
        cancel=Button(text="Abbrechen",font_size=dp(22),
                      background_normal='',background_color=(0.35,0.35,0.4,1),
                      color=(1,1,1,1))
        save.bind(on_release=self.save_all); cancel.bind(on_release=lambda *_: self.close())
        buttons.add_widget(save); buttons.add_widget(cancel); panel.add_widget(buttons)
        self.add_widget(panel)
    def _row(self,name):
        m=self.manager.get(name)
        if m and m.windows:
            w=m.windows[0]
            start=w.get("start","06:00" if name=="Tag" else "21:00")
            end=w.get("end","21:00" if name=="Tag" else "05:30")
        else:
            start="06:00" if name=="Tag" else "21:00"
            end="21:00" if name=="Tag" else "05:30"
        row=BoxLayout(size_hint_y=None,height=dp(90),spacing=dp(12))
        lbl=Label(text=name,size_hint_x=0.2,font_size=dp(24),color=(1,1,1,1))
        s_lbl=Label(text=start,size_hint_x=0.18,font_size=dp(22),color=(0.8,0.9,1,1))
        e_lbl=Label(text=end,size_hint_x=0.18,font_size=dp(22),color=(0.8,0.9,1,1))
        edit=Button(text="Bearbeiten",size_hint_x=0.25,
                    background_normal='',background_color=(0.3,0.4,0.6,1),
                    color=(1,1,1,1),font_size=dp(18))
        def open_pick(*_):
            sh,sm=[int(x) for x in s_lbl.text.split(":")]
            eh,em=[int(x) for x in e_lbl.text.split(":")]
            picker=TimePickerPopup(f"{name} Zeitfenster",sh,sm,eh,em,
                                   on_save=lambda s,e:self._apply(name,s,e),
                                   on_cancel=lambda:None)
            self.add_widget(picker)
        edit.bind(on_release=open_pick)
        row.add_widget(lbl); row.add_widget(s_lbl); row.add_widget(e_lbl); row.add_widget(edit)
        self.mode_rows[name]={'start':s_lbl,'end':e_lbl}
        return row
    def _apply(self,name,start,end):
        self.mode_rows[name]['start'].text=start
        self.mode_rows[name]['end'].text=end
    def save_all(self,*_):
        for name,data in self.mode_rows.items():
            m=self.manager.get(name)
            if not m: continue
            s=data['start'].text; e=data['end'].text
            if parse_time(s) is None or parse_time(e) is None:
                self.status_lbl.text=f"Ungültige Zeit: {name}"; return
            m.windows=[{"start":s,"end":e}]; m.auto=True
        self.manager.save()
        self.slideshow.manual_override=False
        self.slideshow.force_reschedule()
        self.status_lbl.text="Gespeichert."
        Clock.schedule_once(lambda dt:self.close(),0.7)
    def close(self):
        if self.parent: self.parent.remove_widget(self)
        if self.slideshow.current_overlay is self:
            self.slideshow.current_overlay=None

# ---- Slideshow ----
class Slideshow(FloatLayout):
    def __init__(self, mode_manager: ModeManager, **kw):
        super().__init__(**kw)
        self.mode_manager=mode_manager
        self.current_mode=None
        self.images=[]
        self.index=0
        self.event=None
        self.scheduler_event=None
        self.manual_override=False

        self.selected_effects = set(DEFAULT_EFFECTS)
        self.randomize_effects = False
        self.effect_state_seed = 0

        meta = load_image_meta()
        self.image_effect_overrides = meta.get("effects", {})
        self.image_interval_overrides = meta.get("intervals", {})
        self.image_priority_weights = meta.get("weights", {})
        self.image_brightness_overrides = meta.get("brightness", {})
        self.global_interval_override = meta.get("global_interval", None)
        self.global_brightness_override = meta.get("global_brightness", None)

        self._toolbar_timer=None
        self._toolbar_anim=None
        self.current_overlay=None

        self.debug_label=None
        self.current_original_path=None
        self.current_display_path=None



        with self.canvas.before:
            Color(0.02,0.02,0.03,1)
            self.bg=Rectangle(pos=self.pos,size=self.size)
        self.bind(pos=lambda *a:(setattr(self.bg,'pos',self.pos),setattr(self.bg,'size',self.size)),
                  size=lambda *a:(setattr(self.bg,'pos',self.pos),setattr(self.bg,'size',self.size)))

        self.img_a = Image(opacity=1, color=(1,1,1,1))
        self.img_b = Image(opacity=0, color=(1,1,1,1))
        self.active_img = self.img_a
        self.back_img = self.img_b
        self.add_widget(self.img_a)
        self.add_widget(self.img_b)

        self.img_a.bind(texture=lambda *_: (self._resize_image(self.img_a), self._update_debug_overlay()))
        self.img_b.bind(texture=lambda *_: (self._resize_image(self.img_b), self._update_debug_overlay()))
        self.bind(size=lambda *_: (self._resize_image(self.img_a), self._resize_image(self.img_b)))

        self.toolbar=self._create_toolbar()
        self.add_widget(self.toolbar)

        self.placeholder=Label(text="",color=(1,1,1,0.7),font_size=dp(26),opacity=0)
        self.add_widget(self.placeholder)

        if SHOW_INFO_LABEL:
            self.info_label=Label(text="",color=(1,1,1,0.85),
                                  size_hint=(1,None),height=dp(36),
                                  font_size=dp(20),
                                  pos_hint={'center_x':0.5,'y':0.01})
            self.add_widget(self.info_label)

        if SHOW_DEBUG_OVERLAY:
            self.debug_label=Label(text="",color=(0.9,0.95,1,0.85),
                                   size_hint=(None,None),
                                   font_size=DEBUG_OVERLAY_FONT_SIZE,
                                   pos=(dp(8), self.height - dp(40)))
            self.add_widget(self.debug_label)
            self.bind(size=lambda *_: self._reposition_debug())
        
        if SHOW_FAB_GALLERY: self.add_gallery_fab()

        self._new_files_timer=Clock.schedule_interval(lambda dt:self._check_new_files(), INTERVAL_NEW_FILES)

        # Recording functionality moved to popup (no bottom widget)

        self.auto_select_initial_mode()
        self.start_slideshow()
        self.scheduler_event=Clock.schedule_interval(lambda dt:self.auto_scheduler(), SCHEDULER_INTERVAL_SEC)
        self._show_toolbar_immediate()

    # Persistenz
    def persist_meta(self):
        meta = {
            "effects": self.image_effect_overrides,
            "intervals": self.image_interval_overrides,
            "weights": self.image_priority_weights,
            "brightness": self.image_brightness_overrides,
            "global_interval": self.global_interval_override,
            "global_brightness": self.global_brightness_override
        }
        save_image_meta(meta)

    # Overlay Manager
    def open_single(self, widget):
        if self.current_overlay and self.current_overlay.parent:
            self.remove_widget(self.current_overlay)
        self.current_overlay = widget
        self.add_widget(widget)

    # Upscaling / Resize
    def _resize_image(self,img_widget):
        if not img_widget.texture: return
        win_w,win_h=self.width,self.height
        tex_w,tex_h=img_widget.texture.size
        if tex_w==0 or tex_h==0: return
        if IMAGE_SCALE_MODE=="stretch":
            # For stretch mode, fill entire window
            img_widget.size=(win_w,win_h); img_widget.pos=(0,0); return
        # For other modes, calculate manual scaling
        ratio_w=win_w/tex_w; ratio_h=win_h/tex_h
        scale=max(ratio_w,ratio_h) if IMAGE_SCALE_MODE=="cover" else min(ratio_w,ratio_h)
        new_w=tex_w*scale; new_h=tex_h*scale
        img_widget.size=(new_w,new_h)
        img_widget.pos=((win_w-new_w)/2,(win_h-new_h)/2)

    def _create_toolbar(self):
        if AppBarClass:
            bar=AppBarClass(title=("" if HIDE_TOOLBAR_TITLE else "Slideshow"),
                            elevation=8,pos_hint={"top":1})
            self._update_md_toolbar_buttons(bar)
            def md_fade_in(self_,duration=TOOLBAR_FADE_DURATION):
                self_.disabled=False
                Animation.cancel_all(self_,'opacity')
                Animation(opacity=1,d=duration,t='out_quad').start(self_)
            def md_fade_out(self_,duration=TOOLBAR_FADE_DURATION):
                Animation.cancel_all(self_,'opacity')
                def _dis(*_): self_.disabled=True
                a=Animation(opacity=0,d=duration,t='in_quad'); a.bind(on_complete=_dis); a.start(self_)
            bar.fade_in=types.MethodType(md_fade_in,bar)
            bar.fade_out=types.MethodType(md_fade_out,bar)
            return bar
        bar=CustomAppBar(title=("Slideshow" if not HIDE_TOOLBAR_TITLE else ""))
        self._update_toolbar_buttons(bar)
        return bar
    
    def _update_md_toolbar_buttons(self, bar):
        """Update KivyMD toolbar buttons"""
        bar.right_action_items=[
            ["calendar",lambda x:self.open_schedule_editor()],
            ["record",lambda x:self.open_aufnahme_popup()],
            ["image-multiple",lambda x:self.open_gallery()],
            ["cog",lambda x:self.open_settings_root()],
            ["logout",lambda x:self.logout()],
            ["power",lambda x:self.exit_app()],
        ]
    
    def _update_toolbar_buttons(self, bar):
        """Update toolbar buttons"""
        bar.set_right_actions([
            ("Zeiten", self.open_schedule_editor),
            ("Aufnahme", self.open_aufnahme_popup),
            ("Galerie", self.open_gallery),
            ("Einstellungen", self.open_settings_root),
            ("Logout", self.logout),
            ("Exit", self.exit_app),
        ])

    def _bring_toolbar_to_front(self):
        if self.toolbar in self.children:
            self.remove_widget(self.toolbar); self.add_widget(self.toolbar)

    def open_gallery(self): self.open_single(GalleryEditor(self))
    def open_schedule_editor(self): self.open_single(ScheduleEditor(self))
    def open_settings_root(self): self.open_single(SettingsRootPopup(self))
    def open_aufnahme_popup(self): self.open_single(AufnahmePopup())

    def force_reschedule(self):
        scheduled=self.mode_manager.scheduled_mode()
        target=scheduled.name if scheduled else "Alle Bilder"
        self.set_mode(target, manual=False)

    def exit_app(self): 
        App.get_running_app().stop()
    def logout(self):
        app=App.get_running_app()
        if hasattr(app,'show_login'): app.show_login()

    # Interval & Brightness
    def _get_interval_for_path(self, path):
        if path in self.image_interval_overrides:
            return max(1, self.image_interval_overrides[path])
        if self.global_interval_override is not None:
            return max(1, self.global_interval_override)
        if self.current_mode:
            return max(1, self.current_mode.interval)
        return max(1, DEFAULT_INTERVAL)

    def _apply_current_brightness(self):
        b_global = self.global_brightness_override or 1.0
        b_image = self.image_brightness_overrides.get(self.current_original_path, 1.0)
        b = max(0.1, min(2.0, b_global * b_image))
        for w in (self.img_a, self.img_b):
            r,g,bl,_ = w.color
            w.color = (b, b, b, 1)

    def _reschedule_for_current(self):
        if self.event: Clock.unschedule(self.event)
        interval = self._get_interval_for_path(self.current_original_path)
        self.event = Clock.schedule_once(lambda dt:self.next_image(), interval)

    def auto_select_initial_mode(self):
        scheduled=self.mode_manager.scheduled_mode()
        if scheduled: self.set_mode(scheduled.name, manual=False)
        else: self.set_mode("Alle Bilder", manual=False)

    def auto_scheduler(self):
        if self.manual_override: return
        scheduled=self.mode_manager.scheduled_mode()
        target=scheduled.name if scheduled else "Alle Bilder"
        if not self.current_mode or self.current_mode.name!=target:
            self.set_mode(target, manual=False)

    def _scan_global(self):
        if IMAGE_DIR.exists():
            files=[str(p) for p in IMAGE_DIR.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
            files.sort(); return files
        return []

    def _check_new_files(self):
        if not self.current_mode:
            return
        
        # Update images for all modes - especially important for Tag/Nacht mode switching
        if self.current_mode.name in ("Alle Bilder","Standard"):
            cur=self._scan_global()
        else:
            # For Tag/Nacht and other specific modes, check their assigned images
            cur=self.current_mode.existing_images()
            
        if cur!=self.images:
            self.images=cur
            self.index=min(self.index,len(self.images)-1) if self.images else 0
            self.show_current_image(initial=True)
            self.update_info()

    def set_mode(self,name,manual=False):
        mode=self.mode_manager.get(name)
        if not mode: return
        self.current_mode=mode
        if manual: self.manual_override=True
        if mode.name in ("Alle Bilder","Standard"):
            self.images=self._scan_global()
        else:
            self.images=mode.existing_images()
        if mode.randomize: shuffle(self.images)
        self.index=0
        self.show_current_image(initial=True)
        self.update_info()
        if hasattr(self.toolbar,'title'):
            self.toolbar.title = "" if HIDE_TOOLBAR_TITLE else mode.name
        self._bring_toolbar_to_front()
        self._reschedule_for_current()

    def start_slideshow(self):
        self.show_current_image(initial=True)
        self._reschedule_for_current()

    def _choose_effect(self):
        avail=list(self.selected_effects)
        if len(avail)==1: return avail[0]
        if "none" in avail and len(avail)>1:
            avail=[e for e in avail if e!="none"]
        if self.randomize_effects:
            return choice(avail)
        return sorted(avail)[0]

    def _weighted_next_index(self):
        weights=[]
        total=0
        for p in self.images:
            w=self.image_priority_weights.get(p,1)
            if w<1: w=1
            weights.append(w); total+=w
        if total<=len(self.images):
            return (self.index+1)%len(self.images)
        r=random()*total
        acc=0
        for i,w in enumerate(weights):
            acc+=w
            if r<=acc:
                return i
        return (self.index+1)%len(self.images)

    def show_current_image(self, initial=False):
        self._bring_toolbar_to_front()
        if not self.images:
            self.img_a.source=""; self.img_b.source=""
            self.placeholder.text=f"Keine Bilder im Modus '{self.current_mode.name}'." if self.current_mode else "Keine Bilder."
            self.placeholder.opacity=1
            self.update_info(empty=True)
            return
        self.placeholder.opacity=0
        path=self.images[self.index % len(self.images)]
        self.current_original_path=path
        self.current_display_path=path
        self.back_img.source=path
        self.back_img.opacity=0
        self.back_img.reload()
        Clock.schedule_once(lambda dt:(self._resize_image(self.back_img), self._update_debug_overlay(), self._apply_current_brightness()))
        if initial:
            self.active_img.opacity=0
            self.back_img.opacity=1
            self.active_img,self.back_img=self.back_img,self.active_img
            self._apply_current_brightness()
            self._update_debug_overlay()
            return
        effect_override=self.image_effect_overrides.get(path)
        effect=effect_override if effect_override else self._choose_effect()
        mapping={
            "fade":self._apply_fade,
            "slide_left":lambda nw,ow:self._apply_slide(nw,ow,'left'),
            "slide_right":lambda nw,ow:self._apply_slide(nw,ow,'right'),
            "zoom_in":self._apply_zoom_in,
            "zoom_pan":self._apply_zoom_pan,
            "rotate":self._apply_rotate,
            "blitz":self._apply_blitz,
            "none":self._apply_none
        }
        mapping.get(effect,self._apply_fade)(self.back_img,self.active_img)

    # Effekte
    def _apply_slide(self,new_widget,old_widget,direction='left'):
        if not new_widget.texture: return self._apply_none(new_widget,old_widget)
        self._resize_image(new_widget)
        if direction=='left':
            new_widget.x=self.width; target_old=-self.width
        else:
            new_widget.x=-self.width; target_old=self.width
        new_widget.opacity=1
        new_widget.y=(self.height-new_widget.height)/2
        old_widget.y=(self.height-old_widget.height)/2
        a_old=Animation(x=target_old,d=0.6,t='out_quad')
        a_new=Animation(x=(self.width-new_widget.width)/2,d=0.6,t='out_quad')
        def finish(*_):
            old_widget.opacity=0; self._transition_done()
        a_old.start(old_widget); a_new.bind(on_complete=finish); a_new.start(new_widget)
    def _apply_fade(self,new_widget,old_widget):
        self._resize_image(new_widget)
        new_widget.opacity=0
        a_out=Animation(opacity=0,d=FADE_OUT_DUR,t="in_quad")
        a_in=Animation(opacity=1,d=FADE_IN_DUR,t="out_quad")
        def after_out(*_):
            a_in.bind(on_complete=lambda *_: self._transition_done()); a_in.start(new_widget)
        a_out.bind(on_complete=after_out); a_out.start(old_widget)
    def _apply_none(self,new_widget,old_widget):
        self._resize_image(new_widget)
        old_widget.opacity=0; new_widget.opacity=1
        self._transition_done()
    def _apply_zoom_in(self,new_widget,old_widget):
        self._resize_image(new_widget)
        bw,bh=new_widget.width,new_widget.height
        new_widget.width=bw*1.1; new_widget.height=bh*1.1
        new_widget.x=(self.width-new_widget.width)/2
        new_widget.y=(self.height-new_widget.height)/2
        new_widget.opacity=0
        a_out=Animation(opacity=0,d=0.4)
        def do_new(*_):
            a_new=Animation(opacity=1,width=bw,height=bh,
                            x=(self.width-bw)/2,y=(self.height-bh)/2,
                            d=1.2,t='out_quad')
            a_new.bind(on_complete=lambda *_: self._transition_done()); a_new.start(new_widget)
        a_out.bind(on_complete=lambda *_: do_new()); a_out.start(old_widget)
    def _apply_zoom_pan(self,new_widget,old_widget):
        self._resize_image(new_widget)
        bw,bh=new_widget.width,new_widget.height
        new_widget.width=bw*1.08; new_widget.height=bh*1.08
        dx=uniform(-0.05,0.05)*self.width; dy=uniform(-0.05,0.05)*self.height
        new_widget.x=(self.width-new_widget.width)/2+dx
        new_widget.y=(self.height-new_widget.height)/2+dy
        new_widget.opacity=0
        a_out=Animation(opacity=0,d=0.45)
        def anim_new(*_):
            a_new=Animation(opacity=1,width=bw,height=bh,
                            x=(self.width-bw)/2,y=(self.height-bh)/2,
                            d=1.8,t='out_quad')
            a_new.bind(on_complete=lambda *_: self._transition_done()); a_new.start(new_widget)
        a_out.bind(on_complete=lambda *_: anim_new()); a_out.start(old_widget)
    def _apply_rotate(self,new_widget,old_widget):
        self._resize_image(new_widget)
        bw,bh=new_widget.width,new_widget.height
        new_widget.width=bw*1.02; new_widget.height=bh*1.02
        new_widget.x=(self.width-new_widget.width)/2 + uniform(-self.width*0.02,self.width*0.02)
        new_widget.y=(self.height-new_widget.height)/2 + uniform(-self.height*0.02,self.height*0.02)
        new_widget.opacity=0
        a_out=Animation(opacity=0,d=0.4)
        def fin(*_):
            a_new=Animation(opacity=1,width=bw,height=bh,
                            x=(self.width-bw)/2,y=(self.height-bh)/2,
                            d=1.0,t='out_quad')
            a_new.bind(on_complete=lambda *_: self._transition_done()); a_new.start(new_widget)
        a_out.bind(on_complete=lambda *_: fin()); a_out.start(old_widget)
    
    def _apply_blitz(self, new_widget, old_widget):
        # Blitz effect: fast, intense transition with white flash
        self._resize_image(new_widget)
        new_widget.opacity=0
        
        # First flash old widget to white then fade out
        old_widget.color = (3, 3, 3, 1)  # Bright white
        a_flash = Animation(color=(1, 1, 1, 1), opacity=0, d=0.1, t='out_quad')
        
        def show_new(*_):
            # Show new image with brief white flash
            new_widget.color = (2, 2, 2, 1)  # Brief bright
            new_widget.opacity = 1
            a_new = Animation(color=(1, 1, 1, 1), d=0.15, t='out_quad')
            a_new.bind(on_complete=lambda *_: self._transition_done())
            a_new.start(new_widget)
        
        a_flash.bind(on_complete=show_new)
        a_flash.start(old_widget)
    def _transition_done(self):
        self.active_img.opacity=0
        self.active_img,self.back_img=self.back_img,self.active_img
        self.back_img.opacity=0
        self._apply_current_brightness()
        self._update_debug_overlay()
        self._reschedule_for_current()

    def next_image(self, *args):
        if not self.images: return
        if any(w>1 for w in self.image_priority_weights.values() if w):
            self.index=self._weighted_next_index()
        else:
            self.index=(self.index+1)%len(self.images)
        self.show_current_image()
        self.update_info()
    def prev_image(self):
        if not self.images: return
        self.index=(self.index-1)%len(self.images)
        self.show_current_image()
        self.update_info()

    def update_info(self, empty=False):
        if not SHOW_INFO_LABEL or not self.info_label: return
        if not self.current_mode:
            self.info_label.text="Kein Modus"; return
        img_info=f"{self.index+1}/{len(self.images)}" if self.images else "0/0"
        auto_flag="Auto" if self.current_mode.auto else "Manuell"
        ov=" Override" if self.manual_override else ""
        rnd=" Zufall" if self.current_mode.randomize else ""
        if empty:
            self.info_label.text=f"[{self.current_mode.name}] Keine Bilder | {auto_flag}{ov}{rnd}"
        else:
            self.info_label.text=f"[{self.current_mode.name}] {img_info} | {auto_flag}{ov}{rnd}"

    def _show_toolbar_immediate(self):
        if hasattr(self.toolbar,'fade_in'): self.toolbar.fade_in(0)
        else:
            self.toolbar.opacity=1; self.toolbar.disabled=False
        self._schedule_toolbar_hide()
    def _schedule_toolbar_hide(self):
        if self._toolbar_timer: Clock.unschedule(self._toolbar_timer)
        self._toolbar_timer=Clock.schedule_once(lambda dt:self._hide_toolbar(), TOOLBAR_VISIBLE_SECS)
    def _hide_toolbar(self):
        if hasattr(self.toolbar,'fade_out'): self.toolbar.fade_out()
        else: Animation(opacity=0,d=TOOLBAR_FADE_DURATION).start(self.toolbar)
    def _bring_up_toolbar(self):
        if hasattr(self.toolbar,'fade_in'): self.toolbar.fade_in()
        else:
            if self._toolbar_anim: self._toolbar_anim.stop(self.toolbar)
            self.toolbar.disabled=False; self.toolbar.opacity=1
        self._bring_toolbar_to_front()
        self._schedule_toolbar_hide()

    def _reposition_debug(self):
        if not self.debug_label: return
        self.debug_label.pos=(dp(8), self.height - dp(40))
    def _update_debug_overlay(self):
        if not SHOW_DEBUG_OVERLAY or not self.debug_label: return
        orig=self.current_original_path or "-"
        tw,th=(0,0)
        if self.active_img.texture: tw,th=self.active_img.texture.size
        aw,ah=self.active_img.size
        self.debug_label.text=f"Original | File: {Path(orig).name if orig!='-' else '-'} | Tex: {tw}x{th} -> Display: {aw:.0f}x{ah:.0f}"

    def on_touch_down(self,touch):
        self._bring_up_toolbar()
        self._start_x=touch.x
        return super().on_touch_down(touch)
    def on_touch_up(self,touch):
        self._bring_up_toolbar()
        if hasattr(self,'_start_x'):
            dx=touch.x-self._start_x
            if abs(dx)>50:
                if dx<0: self.next_image()
                else: self.prev_image()
            del self._start_x
        return super().on_touch_up(touch)
    def on_mouse_down(self, window, x, y, button, modifiers):
        self._bring_up_toolbar()

    def cleanup_on_exit(self):
        """Clean up resources when app is closing to fix recording restart issue"""
        debug_logger.info("Slideshow cleanup: stopping timers and processes")
        
        # Stop all timers
        if self.event: 
            Clock.unschedule(self.event)
            self.event = None
        if self.scheduler_event: 
            Clock.unschedule(self.scheduler_event)
            self.scheduler_event = None
        if self._new_files_timer: 
            Clock.unschedule(self._new_files_timer)
            self._new_files_timer = None
        if self._toolbar_timer: 
            Clock.unschedule(self._toolbar_timer)
            self._toolbar_timer = None
            
        # Stop any active recording processes
        for child in self.children[:]:  # Copy list to avoid modification during iteration
            if hasattr(child, 'is_running') and child.is_running:
                debug_logger.info("Found running recording, stopping it")
                if hasattr(child, 'stop_recording'):
                    child.stop_recording()
                    
        debug_logger.info("Slideshow cleanup completed")

# ---- App Klassen ----
if KIVYMD_OK:
    class KioskMDApp(MDApp):
        def build(self):
            self.theme_cls.theme_style="Dark"
            self.theme_cls.primary_palette="Blue"
            self.mode_manager=ModeManager(MODES_PATH)
            self.root_widget=FloatLayout()
            self.slideshow=None
            
            # Start upload server early in app initialization
            self._start_upload_server()
            
            self.show_login()
            return self.root_widget
        def clear_root(self): self.root_widget.clear_widgets()
        def show_login(self):
            self.clear_root(); self.root_widget.add_widget(LoginScreen(self.on_login_success,self.show_register))
        def show_register(self):
            self.clear_root(); self.root_widget.add_widget(RegisterScreen(self.show_login))
        def on_login_success(self):
            self.clear_root()
            self.slideshow=Slideshow(self.mode_manager)
            self.root_widget.add_widget(self.slideshow)
        def on_stop(self):
            """Clean up resources when app is closing to fix recording restart issue"""
            debug_logger.info("App is stopping - performing cleanup")
            if self.slideshow:
                self.slideshow.cleanup_on_exit()
            
            # Stop upload server
            if upload_server.running:
                upload_server.stop_server()
                
            return True
        
        def _start_upload_server(self):
            """Start the upload server with proper error handling and logging"""
            debug_logger.info(f"Starting upload server on port {UPLOAD_PORT}...")
            
            try:
                success = upload_server.start_server()
                if success:
                    debug_logger.info(f"✅ Upload-Server erfolgreich gestartet auf Port {UPLOAD_PORT}")
                    debug_logger.info(f"📱 Upload-URL: {upload_server.get_qr_url()}")
                    print(f"Upload-Server läuft auf: {upload_server.get_qr_url()}")
                else:
                    debug_logger.error(f"❌ Upload-Server konnte nicht gestartet werden")
                    debug_logger.info("💡 Lösung: Ändern Sie UPLOAD_PORT in main.py (Zeile ~75) auf einen anderen Wert")
                    debug_logger.info("💡 Beispiel: UPLOAD_PORT = 8000  # oder 8001, 9000, etc.")
                    print(f"⚠ Upload-Server nicht verfügbar - Port {UPLOAD_PORT} bereits belegt")
                    
            except Exception as e:
                debug_logger.error(f"❌ Fehler beim Starten des Upload-Servers: {e}", exc_info=True)
                print(f"⚠ Upload-Server Fehler: {e}")
else:
    class KioskMDApp(App):
        def build(self):
            self.mode_manager=ModeManager(MODES_PATH)
            self.root_widget=FloatLayout()
            self.slideshow=None
            
            # Start upload server early in app initialization
            self._start_upload_server()
            
            self.show_login()
            return self.root_widget
        def clear_root(self): self.root_widget.clear_widgets()
        def show_login(self):
            self.clear_root(); self.root_widget.add_widget(LoginScreen(self.on_login_success,self.show_register))
        def show_register(self):
            self.clear_root(); self.root_widget.add_widget(RegisterScreen(self.show_login))
        def on_login_success(self):
            self.clear_root()
            self.slideshow=Slideshow(self.mode_manager)
            self.root_widget.add_widget(self.slideshow)
        def on_stop(self):
            """Clean up resources when app is closing to fix recording restart issue"""
            debug_logger.info("App is stopping - performing cleanup")
            if self.slideshow:
                self.slideshow.cleanup_on_exit()
            
            # Stop upload server
            if upload_server.running:
                upload_server.stop_server()
                
            return True
        
        def _start_upload_server(self):
            """Start the upload server with proper error handling and logging"""
            debug_logger.info(f"Starting upload server on port {UPLOAD_PORT}...")
            
            try:
                success = upload_server.start_server()
                if success:
                    debug_logger.info(f"✅ Upload-Server erfolgreich gestartet auf Port {UPLOAD_PORT}")
                    debug_logger.info(f"📱 Upload-URL: {upload_server.get_qr_url()}")
                    print(f"Upload-Server läuft auf: {upload_server.get_qr_url()}")
                else:
                    debug_logger.error(f"❌ Upload-Server konnte nicht gestartet werden")
                    debug_logger.info("💡 Lösung: Ändern Sie UPLOAD_PORT in main.py (Zeile ~75) auf einen anderen Wert")
                    debug_logger.info("💡 Beispiel: UPLOAD_PORT = 8000  # oder 8001, 9000, etc.")
                    print(f"⚠ Upload-Server nicht verfügbar - Port {UPLOAD_PORT} bereits belegt")
                    
            except Exception as e:
                debug_logger.error(f"❌ Fehler beim Starten des Upload-Servers: {e}", exc_info=True)
                print(f"⚠ Upload-Server Fehler: {e}")

if __name__ == "__main__":
    app = KioskMDApp()
    Window.bind(on_mouse_down=lambda w,x,y,b,m:
                hasattr(app,'root_widget') and app.root_widget.children and
                hasattr(app.root_widget.children[-1],'on_mouse_down') and
                app.root_widget.children[-1].on_mouse_down(w,x,y,b,m))
    app.run()
