import pygame, sys, os, json, random, subprocess, threading, time
import numpy as np
import soundfile as sf
import sounddevice as sd
from scipy.signal import sosfilt
import pystray
from PIL import Image, ImageDraw
import win32gui, win32con
import winreg
from pywinauto import mouse as win_mouse

pygame.init()

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _get_base_dir()
MUSIC_DIR = os.path.join(BASE_DIR, "music")
LAYOUT_FILE = os.path.join(BASE_DIR, "layout.json")
PLAYLISTS_FILE = os.path.join(BASE_DIR, "playlists.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
os.makedirs(MUSIC_DIR, exist_ok=True)
AUDIO_EXTS = (".mp3", ".m4a", ".opus", ".ogg", ".wav", ".flac")
MIN_W, MIN_H = 380, 480
APP_NAME = "Livermorium"

def _safe_int(v, default, lo, hi):
    try:
        return max(lo, min(hi, int(v)))
    except Exception:
        return default

def _safe_float(v, default, lo, hi):
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return default

def _peek_window_size():
    if os.path.exists(LAYOUT_FILE):
        try:
            with open(LAYOUT_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            w = _safe_int(d.get("window", {}).get("w", MIN_W), MIN_W, MIN_W, 4000)
            h = _safe_int(d.get("window", {}).get("h", MIN_H), MIN_H, MIN_H, 4000)
            return (w, h)
        except Exception:
            pass
    return (MIN_W, MIN_H)

WIDTH, HEIGHT = _peek_window_size()
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption(APP_NAME)

def find_ffmpeg():
    local = os.path.join(BASE_DIR, "ffmpeg.exe")
    if os.path.exists(local):
        return local
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            return "ffmpeg"
    except Exception:
        pass
    return None

def find_ytdlp():
    local = os.path.join(BASE_DIR, "yt-dlp.exe")
    if os.path.exists(local):
        return local
    return None

FFMPEG_PATH = find_ffmpeg()
YTDLP_PATH = find_ytdlp()

def check_ffmpeg():
    if FFMPEG_PATH:
        print(f"[OK] ffmpeg: {FFMPEG_PATH}")
        return True
    print("[!] ffmpeg не найден")
    return False

def check_ytdlp():
    if YTDLP_PATH:
        print(f"[OK] yt-dlp: {YTDLP_PATH}")
        return True
    if getattr(sys, 'frozen', False):
        print("[!] yt-dlp.exe не найден рядом с .exe")
        return False
    try:
        r = subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            print(f"[OK] yt-dlp: {r.stdout.strip()}")
            return True
    except Exception:
        pass
    print("[!] yt-dlp не найден")
    return False

FFMPEG_OK = check_ffmpeg()
YTDLP_OK = check_ytdlp()

def bring_to_front():
    try:
        hwnd = pygame.display.get_wm_info()["window"]
        try:
            win_mouse.move(coords=(-10000, 500))
        except Exception:
            pass
        time.sleep(0.05)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        try:
            win_mouse.move(coords=(WIDTH // 2, HEIGHT // 2))
        except Exception:
            pass
    except Exception as e:
        print(f"Ошибка вывода окна: {e}")
bring_to_front()

BLACK = (10, 10, 10)
WHITE = (255, 255, 255)
GREEN = (80, 200, 120)
RED = (220, 80, 80)
FONT_SMALL = pygame.font.SysFont("Courier New", 11, bold=True)
FONT_MED = pygame.font.SysFont("Courier New", 13, bold=True)
FONT_BIG = pygame.font.SysFont("Courier New", 22, bold=True)
TOP_H = 56
PAD = 10

COLOR_PALETTE = [
    ("Синий",     (25, 30, 40),    (100, 180, 255), (120, 140, 180), (25, 25, 30)),
    ("Голубой",   (20, 35, 45),    (120, 220, 255), (100, 170, 200), (20, 30, 40)),
    ("Фиолет",    (30, 22, 45),    (180, 120, 255), (140, 110, 200), (28, 20, 42)),
    ("Зелёный",   (22, 38, 28),    (120, 255, 160), (90, 170, 110),  (20, 35, 25)),
    ("Красный",   (45, 20, 20),    (255, 120, 120), (200, 110, 110), (42, 18, 18)),
    ("Оранжевый", (45, 32, 18),    (255, 180, 80),  (200, 150, 90),  (42, 30, 16)),
    ("Розовый",   (45, 22, 35),    (255, 140, 200), (200, 130, 170), (42, 20, 32)),
    ("Серый",     (35, 35, 35),    (200, 200, 200), (170, 170, 170), (30, 30, 30)),
]

background_path = ""
background_surface = None

AUTOSTART_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def get_startup_command():
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    else:
        script = os.path.abspath(__file__)
        return f'"{sys.executable}" "{script}"'

def is_autostart_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False

def set_autostart(enable):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_REG_PATH, 0, winreg.KEY_SET_VALUE)
        try:
            if enable:
                cmd = get_startup_command()
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                print(f"[OK] Автозапуск: {cmd}")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    print("[OK] Автозапуск выключен")
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        print(f"Ошибка автозапуска: {e}")

def load_settings():
    defaults = {
        "volume": 0.6, "shuffle": False, "repeat": False,
        "color_virt": 0, "color_panel": 0, "color_btn": 0, "color_top": 0,
        "panel_alpha": 255, "top_alpha": 255, "background": "",
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            if not isinstance(d, dict):
                return defaults
            defaults["volume"] = _safe_float(d.get("volume", 0.6), 0.6, 0.0, 1.0)
            defaults["shuffle"] = bool(d.get("shuffle", False))
            defaults["repeat"] = bool(d.get("repeat", False))
            defaults["color_virt"] = _safe_int(d.get("color_virt", 0), 0, 0, len(COLOR_PALETTE) - 1)
            defaults["color_panel"] = _safe_int(d.get("color_panel", 0), 0, 0, len(COLOR_PALETTE) - 1)
            defaults["color_btn"] = _safe_int(d.get("color_btn", 0), 0, 0, len(COLOR_PALETTE) - 1)
            defaults["color_top"] = _safe_int(d.get("color_top", 0), 0, 0, len(COLOR_PALETTE) - 1)
            defaults["panel_alpha"] = _safe_int(d.get("panel_alpha", 255), 255, 0, 255)
            defaults["top_alpha"] = _safe_int(d.get("top_alpha", 255), 255, 0, 255)
            bg = d.get("background", "")
            if isinstance(bg, str) and bg:
                defaults["background"] = bg
        except Exception as e:
            print(f"Ошибка чтения settings.json: {e}")
    return defaults

def save_settings():
    try:
        data = {
            "volume": float(volume_value),
            "shuffle": bool(shuffle),
            "repeat": bool(repeat),
            "color_virt": int(color_virt_idx),
            "color_panel": int(color_panel_idx),
            "color_btn": int(color_btn_idx),
            "color_top": int(color_top_idx),
            "panel_alpha": int(panel_alpha),
            "top_alpha": int(top_alpha),
            "background": str(background_path) if background_path else "",
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

def load_playlists():
    if os.path.exists(PLAYLISTS_FILE):
        try:
            with open(PLAYLISTS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict) and "playlists" in d and isinstance(d["playlists"], dict):
                return d["playlists"]
        except Exception:
            pass
    return {"Одиночные": []}

def save_playlists():
    try:
        with open(PLAYLISTS_FILE, "w", encoding="utf-8") as f:
            json.dump({"playlists": playlists}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка: {e}")

playlists = load_playlists()

def add_track_to_playlist(name, filename):
    if name not in playlists:
        playlists[name] = []
    if filename not in playlists[name]:
        playlists[name].append(filename)
    save_playlists()

def default_layout(w, h):
    y = TOP_H + 8
    seek_h = 24
    virt_y = y + seek_h + 4
    virt_h = 35
    mix_y = virt_y + virt_h + PAD
    mix_h = 90
    pl_y = mix_y + mix_h + PAD
    pl_h = h - pl_y - PAD
    return {
        "spectrum": {"x": PAD, "y": virt_y, "w": w - PAD * 2, "h": virt_h},
        "mixer":    {"x": PAD, "y": mix_y, "w": w - PAD * 2, "h": mix_h},
        "playlist": {"x": PAD, "y": pl_y, "w": w - PAD * 2, "h": pl_h},
    }

def load_layout():
    return default_layout(WIDTH, HEIGHT)

def save_layout():
    try:
        d = {k: dict(v) for k, v in layout.items()}
        d["window"] = {"w": WIDTH, "h": HEIGHT}
        with open(LAYOUT_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка: {e}")

layout = load_layout()

def relayout_for_window(old_w, old_h, new_w, new_h):
    y = TOP_H + 8
    seek_h = 24
    virt_y = y + seek_h + 4
    virt_h = 35
    mix_y = virt_y + virt_h + PAD
    mix_h = 90
    pl_y = mix_y + mix_h + PAD
    pl_h = new_h - pl_y - PAD
    layout["spectrum"] = {"x": PAD, "y": virt_y, "w": new_w - PAD * 2, "h": virt_h}
    layout["mixer"]    = {"x": PAD, "y": mix_y,  "w": new_w - PAD * 2, "h": mix_h}
    layout["playlist"] = {"x": PAD, "y": pl_y,   "w": new_w - PAD * 2, "h": pl_h}

class AudioEngine:
    SAMPLE_RATE = 44100
    BLOCK_SIZE = 4096
    EQ_BANDS = [60, 170, 310, 600, 1000, 3000, 6000, 12000, 16000]

    def __init__(self):
        self.audio = None
        self.sr = self.SAMPLE_RATE
        self.position = 0
        self.playing = False
        self.stream = None
        self.volume = 0.6
        self.eq_gains_db = [0.0] * len(self.EQ_BANDS)
        self.eq_filters = [self._make_sos(f, 0.0) for f in self.EQ_BANDS]
        self.filter_states = [[np.zeros((1, 2), dtype=np.float64) for _ in range(2)]
                              for _ in self.eq_filters]
        self.spectrum_buffer = np.zeros(2048, dtype=np.float32)
        self.spectrum_lock = threading.Lock()
        self.smoothed_spectrum = np.zeros(24, dtype=np.float32)
        self.visual_gate = 0.0
        self.seek_request = None
        self.just_finished = False
        self.stream_lock = threading.Lock()

    def _make_sos(self, freq, gain_db):
        nyq = self.SAMPLE_RATE / 2.0
        f0 = min(freq / nyq, 0.99)
        Q = 1.0
        A = 10 ** (gain_db / 40.0)
        w0 = 2 * np.pi * f0
        alpha = np.sin(w0) / (2 * Q)
        b0 = 1 + alpha * A
        b1 = -2 * np.cos(w0)
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * np.cos(w0)
        a2 = 1 - alpha / A
        return np.array([[b0/a0, b1/a0, b2/a0, 1.0, a1/a0, a2/a0]])

    def set_eq_gain(self, idx, gain_db):
        self.eq_gains_db[idx] = float(gain_db)
        self.eq_filters[idx] = self._make_sos(self.EQ_BANDS[idx], gain_db)
        self.filter_states[idx] = [np.zeros((1, 2), dtype=np.float64) for _ in range(2)]

    def load(self, path):
        try:
            data, sr = sf.read(path, dtype="float32", always_2d=True)
        except Exception as e:
            print(f"Ошибка чтения {path}: {e}")
            return False
        if data.shape[1] == 1:
            data = np.repeat(data, 2, axis=1)
        self.audio = data
        self.sr = sr
        self.position = 0
        self.just_finished = False
        self.filter_states = [[np.zeros((1, 2), dtype=np.float64) for _ in range(2)]
                              for _ in self.eq_filters]
        return True

    def _start_stream_locked(self):
        if self.stream is not None:
            return
        try:
            self.stream = sd.OutputStream(
                samplerate=self.sr, blocksize=self.BLOCK_SIZE,
                channels=2, dtype="float32", callback=self._callback)
            self.stream.start()
        except Exception as e:
            print(f"Ошибка старта: {e}")
            self.stream = None

    def play(self):
        if self.audio is None:
            return
        self.playing = True
        with self.stream_lock:
            self._start_stream_locked()

    def pause(self):
        self.playing = False

    def stop(self):
        self.playing = False
        self.position = 0

    def seek(self, seconds):
        if self.audio is None:
            return
        sec = max(0.0, min(seconds, len(self.audio) / self.sr - 0.05))
        self.seek_request = int(sec * self.sr)

    def _callback(self, outdata, frames, time_info, status):
        if self.seek_request is not None:
            self.position = self.seek_request
            self.seek_request = None
            for i in range(len(self.eq_filters)):
                self.filter_states[i] = [np.zeros((1, 2), dtype=np.float64) for _ in range(2)]
        if not self.playing or self.audio is None:
            outdata.fill(0)
            return
        end = self.position + frames
        if end > len(self.audio):
            chunk = self.audio[self.position:]
            pad = frames - len(chunk)
            chunk = np.vstack([chunk, np.zeros((pad, 2), dtype=np.float32)])
            self.playing = False
            self.just_finished = True
        else:
            chunk = self.audio[self.position:end]
        processed = chunk.astype(np.float64, copy=True)
        for i, sos in enumerate(self.eq_filters):
            if abs(self.eq_gains_db[i]) < 0.05:
                continue
            for ch in range(2):
                out, zi_new = sosfilt(sos, processed[:, ch], zi=self.filter_states[i][ch])
                processed[:, ch] = out
                self.filter_states[i][ch] = zi_new
        processed *= self.volume
        processed = np.clip(processed, -1.0, 1.0).astype(np.float32)
        outdata[:] = processed
        self.position = end
        mono = processed.mean(axis=1)
        with self.spectrum_lock:
            if len(mono) >= 2048:
                self.spectrum_buffer = mono[-2048:].copy()
            else:
                self.spectrum_buffer = np.pad(mono, (2048 - len(mono), 0))

    def get_spectrum(self):
        with self.spectrum_lock:
            buf = self.spectrum_buffer.copy()
        if len(buf) < 2048:
            target = 1.0 if self.playing else 0.0
            if target > self.visual_gate:
                self.visual_gate += 0.08
            else:
                self.visual_gate -= 0.04
            self.visual_gate = max(0.0, min(1.0, self.visual_gate))
            return self.smoothed_spectrum.copy() * self.visual_gate
        window = np.hanning(2048)
        fft = np.abs(np.fft.rfft(buf * window))
        n_bars = 24
        n_fft = len(fft)
        freqs = np.linspace(0, self.sr / 2, n_fft)
        edges = np.logspace(np.log10(40), np.log10(min(16000, self.sr/2 - 1)), n_bars + 1)
        vals = np.zeros(n_bars, dtype=np.float32)
        for i in range(n_bars):
            mask = (freqs >= edges[i]) & (freqs < edges[i+1])
            if mask.any():
                vals[i] = fft[mask].mean()
        m = vals.max()
        if m > 0:
            vals = vals / m
        for i in range(n_bars):
            if vals[i] > self.smoothed_spectrum[i]:
                self.smoothed_spectrum[i] = vals[i]
            else:
                self.smoothed_spectrum[i] = self.smoothed_spectrum[i] * 0.85 + vals[i] * 0.15
        target = 1.0 if self.playing else 0.0
        if target > self.visual_gate:
            self.visual_gate += 0.08
        else:
            self.visual_gate -= 0.04
        self.visual_gate = max(0.0, min(1.0, self.visual_gate))
        return self.smoothed_spectrum.copy() * self.visual_gate

    def get_position_seconds(self):
        return self.position / self.sr if self.sr else 0.0

    def get_duration_seconds(self):
        return len(self.audio) / self.sr if self.audio is not None else 0.0

engine = AudioEngine()

playlist = []
current_track_index = None
dragging_index = None
drag_offset_y = 0
eq_values = [0.0] * 9
dragging_seek = False
dragging_volume = False
edit_mode = False
dragging_block = None
drag_block_offset = (0, 0)
resize_block = None
resize_start = None
menu_open = False
playlist_scroll = 0
view_mode = "tracks"
active_playlist_name = None
playlists_scroll = 0
add_mode = False
add_selected = set()
add_scroll = 0
shuffle_order = []
shuffle_pos = 0
shuffle_sig = None
download_progress = 0.0
download_active = False
download_status = ""
progress_lock = threading.Lock()
tray_icon = None
app_should_quit = False

# Флаги для запросов из трея (обрабатываются в главном потоке)
tray_restore_request = False
tray_hide_request = False

search_open = False
search_text = ""
color_picker_target = None
transparency_open = False
transparency_target = "panel"
dragging_transparency = False

_settings = load_settings()
volume_value = _settings["volume"]
shuffle = _settings["shuffle"]
repeat = _settings["repeat"]
color_virt_idx = _settings["color_virt"]
color_panel_idx = _settings["color_panel"]
color_btn_idx = _settings["color_btn"]
color_top_idx = _settings["color_top"]
panel_alpha = _settings["panel_alpha"]
top_alpha = _settings["top_alpha"]
engine.volume = volume_value

background_path = _settings.get("background", "")
if background_path and os.path.exists(background_path):
    try:
        img = pygame.image.load(background_path)
        background_surface = pygame.transform.scale(img, (WIDTH, HEIGHT))
        print(f"[OK] Фон загружен: {background_path}")
    except Exception as e:
        print(f"Ошибка загрузки фона: {e}")
        background_path = ""
        background_surface = None

def cleanup_music_dir():
    if not os.path.isdir(MUSIC_DIR):
        return
    for f in os.listdir(MUSIC_DIR):
        if f.endswith((".part", ".ytdl", ".temp")):
            try:
                os.remove(os.path.join(MUSIC_DIR, f))
            except Exception:
                pass

def refresh_library():
    global playlist
    items = []
    if os.path.isdir(MUSIC_DIR):
        for f in sorted(os.listdir(MUSIC_DIR)):
            if f.lower().endswith(AUDIO_EXTS):
                path = os.path.join(MUSIC_DIR, f)
                try:
                    info = sf.info(path)
                    dur = int(info.duration)
                    dur_str = f"{dur // 60}:{dur % 60:02d}"
                except Exception:
                    dur_str = "?:??"
                items.append((os.path.splitext(f)[0], dur_str, path, f))
    playlist = items

def filter_tracks(tracks):
    if not search_text:
        return tracks
    q = search_text.lower()
    return [t for t in tracks if q in t[0].lower()]

def get_tracks_for_current_view():
    if view_mode == "playlists":
        return []
    if view_mode == "inside_playlist" and active_playlist_name:
        names = playlists.get(active_playlist_name, [])
        result = []
        for f in names:
            path = os.path.join(MUSIC_DIR, f)
            if not os.path.exists(path):
                continue
            try:
                info = sf.info(path)
                dur = int(info.duration)
                dur_str = f"{dur // 60}:{dur % 60:02d}"
            except Exception:
                dur_str = "?:??"
            result.append((os.path.splitext(f)[0], dur_str, path, f))
        return filter_tracks(result)
    return filter_tracks(playlist)

def load_background_image(filepath):
    global background_surface, background_path
    try:
        img = pygame.image.load(filepath)
        background_surface = pygame.transform.scale(img, (WIDTH, HEIGHT))
        background_path = filepath
        save_settings()
        print(f"[OK] Фон сохранён: {filepath}")
    except Exception as e:
        print(f"Ошибка фона: {e}")

def make_shuffle_signature():
    return tuple(t[3] for t in get_tracks_for_current_view())

def rebuild_shuffle_order(start_filename=None):
    global shuffle_order, shuffle_pos, shuffle_sig
    tracks = get_tracks_for_current_view()
    if not tracks:
        shuffle_order = []
        shuffle_pos = 0
        shuffle_sig = None
        return
    indices = list(range(len(tracks)))
    random.shuffle(indices)
    if start_filename is not None:
        for j, idx in enumerate(indices):
            if tracks[idx][3] == start_filename:
                indices[0], indices[j] = indices[j], indices[0]
                break
    shuffle_order = indices
    shuffle_pos = 0
    shuffle_sig = make_shuffle_signature()

def ensure_shuffle_valid():
    global shuffle_sig
    if make_shuffle_signature() != shuffle_sig:
        rebuild_shuffle_order()

def parse_playlist_name(url):
    try:
        if "/sets/" in url:
            part = url.split("/sets/")[1].split("?")[0].split("/")[0]
            return part if part else "SoundCloud"
    except Exception:
        pass
    return "Одиночные"

def download_url(url, target_playlist=None):
    global download_progress, download_active, download_status
    with progress_lock:
        download_active = True
        download_progress = 0.0
        download_status = "Запуск..."

    if not FFMPEG_OK:
        with progress_lock:
            download_status = "Нет ffmpeg"
            download_active = False
        print("[!] ffmpeg не найден")
        return

    if not YTDLP_OK:
        with progress_lock:
            download_status = "yt-dlp.exe не найден"
            download_active = False
        print("[!] yt-dlp.exe не найден рядом с программой")
        return

    if target_playlist is None:
        target_playlist = parse_playlist_name(url)

    before = set(os.listdir(MUSIC_DIR)) if os.path.isdir(MUSIC_DIR) else set()

    if YTDLP_PATH:
        base_cmd = [YTDLP_PATH]
    else:
        base_cmd = [sys.executable, "-m", "yt_dlp"]

    ffmpeg_args = []
    if FFMPEG_PATH and FFMPEG_PATH != "ffmpeg":
        ffmpeg_args = ["--ffmpeg-location", os.path.dirname(FFMPEG_PATH)]

    cmd = base_cmd + ["-x", "--audio-format", "mp3",
           "--audio-quality", "5", "--embed-metadata", "--yes-playlist",
           "--newline", "--no-warnings"] + ffmpeg_args + [
           "-P", MUSIC_DIR, "-P", f"temp:{MUSIC_DIR}", "-P", f"home:{MUSIC_DIR}",
           "-o", "%(title)s.%(ext)s", url]

    print(f"[yt_dlp] {target_playlist}")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True, encoding="utf-8", errors="replace",
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            if "[download]" in line and "%" in line:
                try:
                    pct = float(line.split("%")[0].split()[-1])
                    with progress_lock:
                        download_progress = pct
                        download_status = f"Скачивание: {pct:.1f}%"
                except Exception:
                    pass
            elif "Destination" in line:
                with progress_lock:
                    download_status = "Конвертация..."
            elif line.startswith("ERROR"):
                with progress_lock:
                    download_status = f"Ошибка: {line[:40]}"
        proc.wait()
        after = set(os.listdir(MUSIC_DIR)) if os.path.isdir(MUSIC_DIR) else set()
        new_files = list(after - before)
        if new_files:
            for f in new_files:
                if f.lower().endswith(AUDIO_EXTS):
                    add_track_to_playlist(target_playlist, f)
        with progress_lock:
            download_status = "Обновление..."
        refresh_library()
    except Exception as e:
        with progress_lock:
            download_status = f"Ошибка: {e}"
        print(f"[yt_dlp] {e}")
    finally:
        with progress_lock:
            download_active = False
            download_status = "Готово"

def add_from_url_async(url, target_playlist=None):
    threading.Thread(target=download_url, args=(url, target_playlist), daemon=True).start()

def open_url_dialog():
    from tkinter import Tk, simpledialog
    root = Tk(); root.withdraw(); root.attributes("-topmost", True)
    url = simpledialog.askstring("SoundCloud", "Ссылка:", parent=root)
    root.destroy()
    if url:
        add_from_url_async(url.strip())

def rename_playlist_dialog(old_name):
    from tkinter import Tk, simpledialog
    root = Tk(); root.withdraw(); root.attributes("-topmost", True)
    new_name = simpledialog.askstring("Переименовать", "Новое имя:", initialvalue=old_name, parent=root)
    root.destroy()
    if new_name and new_name.strip() and new_name != old_name:
        new_name = new_name.strip()
        if new_name in playlists:
            return
        playlists[new_name] = playlists.pop(old_name)
        save_playlists()
        global active_playlist_name
        if active_playlist_name == old_name:
            active_playlist_name = new_name

def new_playlist_dialog():
    from tkinter import Tk, simpledialog
    root = Tk(); root.withdraw(); root.attributes("-topmost", True)
    name = simpledialog.askstring("Новый плейлист", "Имя:", parent=root)
    root.destroy()
    if name and name.strip():
        name = name.strip()
        if name not in playlists:
            playlists[name] = []
            save_playlists()

def get_hwnd():
    try:
        return pygame.display.get_wm_info()["window"]
    except Exception:
        return None

def make_tray_image():
    img = Image.new("RGB", (64, 64), (25, 25, 30))
    d = ImageDraw.Draw(img)
    d.polygon([(22, 16), (22, 48), (48, 32)], fill=(120, 140, 180))
    return img

def tray_restore(icon, item):
    """Ставит флаг — обработка в главном потоке."""
    global tray_restore_request
    tray_restore_request = True

def tray_quit(icon, item):
    global app_should_quit
    app_should_quit = True
    save_settings()
    try:
        icon.stop()
    except Exception:
        pass
    pygame.event.post(pygame.event.Event(pygame.QUIT))

def hide_to_tray():
    """Ставит флаг — обработка в главном потоке."""
    global tray_hide_request
    tray_hide_request = True

def start_tray():
    global tray_icon
    menu = pystray.Menu(
        pystray.MenuItem("Развернуть", tray_restore, default=True),
        pystray.MenuItem("Закрыть", tray_quit))
    tray_icon = pystray.Icon(APP_NAME, make_tray_image(), APP_NAME, menu)
    threading.Thread(target=tray_icon.run, daemon=True).start()

def process_tray_requests():
    """Обработка запросов трея в главном потоке."""
    global tray_restore_request, tray_hide_request
    if tray_restore_request:
        tray_restore_request = False
        try:
            hwnd = get_hwnd()
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                pygame.display.set_caption(APP_NAME)
                print("[tray] Окно восстановлено")
        except Exception as e:
            print(f"[tray] Ошибка восстановления: {e}")
    if tray_hide_request:
        tray_hide_request = False
        try:
            hwnd = get_hwnd()
            if hwnd:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                print("[tray] Окно скрыто")
        except Exception as e:
            print(f"[tray] Ошибка скрытия: {e}")

def play_index_by_filename(filename):
    global current_track_index
    for i, (_, _, _, f) in enumerate(playlist):
        if f == filename:
            current_track_index = i
            path = playlist[i][2]
            if engine.load(path):
                engine.play()
            return

def play_current_view_index(idx):
    tracks = get_tracks_for_current_view()
    if not tracks or idx < 0 or idx >= len(tracks):
        return
    play_index_by_filename(tracks[idx][3])

def next_track():
    global shuffle_pos
    tracks = get_tracks_for_current_view()
    if not tracks:
        return
    if shuffle:
        ensure_shuffle_valid()
        if not shuffle_order:
            rebuild_shuffle_order()
        shuffle_pos += 1
        if shuffle_pos >= len(shuffle_order):
            rebuild_shuffle_order()
        play_current_view_index(shuffle_order[shuffle_pos])
        return
    if current_track_index is None:
        play_current_view_index(0)
        return
    current_file = playlist[current_track_index][3] if current_track_index < len(playlist) else None
    for i, (_, _, _, f) in enumerate(tracks):
        if f == current_file:
            play_current_view_index((i + 1) % len(tracks))
            return
    play_current_view_index(0)

def prev_track():
    global shuffle_pos
    tracks = get_tracks_for_current_view()
    if not tracks:
        return
    if shuffle:
        ensure_shuffle_valid()
        if not shuffle_order:
            rebuild_shuffle_order()
        shuffle_pos -= 1
        if shuffle_pos < 0:
            shuffle_pos = len(shuffle_order) - 1
        play_current_view_index(shuffle_order[shuffle_pos])
        return
    if current_track_index is None:
        play_current_view_index(0)
        return
    current_file = playlist[current_track_index][3] if current_track_index < len(playlist) else None
    for i, (_, _, _, f) in enumerate(tracks):
        if f == current_file:
            play_current_view_index((i - 1) % len(tracks))
            return
    play_current_view_index(0)

def toggle_play_pause():
    if engine.playing:
        engine.pause()
    else:
        if engine.audio is not None:
            engine.play()
        else:
            tracks = get_tracks_for_current_view()
            if tracks:
                play_current_view_index(0)

def draw_text(text, font, color, x, y):
    screen.blit(font.render(text, True, color), (x, y))

def fmt_time(sec):
    sec = int(sec)
    return f"{sec // 60:02d}:{sec % 60:02d}"

def search_icon_rect():
    return pygame.Rect(WIDTH - 60, 18, 18, 18)

def search_field_rect():
    return pygame.Rect(PAD, TOP_H + 2, WIDTH - PAD * 2, 24)

def draw_search_icon():
    r = search_icon_rect()
    col = COLOR_PALETTE[color_btn_idx][2] if search_open else COLOR_PALETTE[color_btn_idx][3]
    cx = r.x + 7
    cy = r.y + 7
    pygame.draw.circle(screen, col, (cx, cy), 5, 2)
    pygame.draw.line(screen, col, (cx + 4, cy + 4), (cx + 8, cy + 8), 2)

def draw_search_field():
    if not search_open:
        return
    r = search_field_rect()
    pygame.draw.rect(screen, (25, 25, 30), r)
    pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], r, 1)
    text = search_text if search_text else "Поиск..."
    col = WHITE if search_text else (120, 120, 120)
    draw_text(text, FONT_MED, col, r.x + 8, r.y + 5)
    x_rect = pygame.Rect(r.right - 22, r.y + 4, 18, 18)
    pygame.draw.rect(screen, (80, 30, 30), x_rect)
    draw_text("X", FONT_SMALL, WHITE, x_rect.x + 5, x_rect.y + 3)

def draw_top_bar():
    top_col = COLOR_PALETTE[color_top_idx][3]
    surf = pygame.Surface((WIDTH, TOP_H), pygame.SRCALPHA)
    surf.fill((top_col[0], top_col[1], top_col[2], top_alpha))
    screen.blit(surf, (0, 0))
    btn_col = COLOR_PALETTE[color_btn_idx][3]
    y_mid = TOP_H // 2
    btn_gap = 26
    px = 14
    for off in (0, 7):
        pygame.draw.polygon(screen, btn_col, [
            (px + off + 4, y_mid - 6), (px + off + 4, y_mid + 6), (px + off - 3, y_mid)])
    cx = px + btn_gap + 8
    if engine.playing:
        pygame.draw.rect(screen, WHITE, (cx - 4, y_mid - 7, 4, 14))
        pygame.draw.rect(screen, WHITE, (cx + 2, y_mid - 7, 4, 14))
    else:
        pygame.draw.polygon(screen, WHITE, [(cx - 4, y_mid - 8), (cx - 4, y_mid + 8), (cx + 6, y_mid)])
    nx = cx + btn_gap + 8
    for off in (0, -7):
        pygame.draw.polygon(screen, btn_col, [
            (nx + off - 4, y_mid - 6), (nx + off - 4, y_mid + 6), (nx + off + 3, y_mid)])
    sx = nx + btn_gap
    col = COLOR_PALETTE[color_btn_idx][2] if shuffle else btn_col
    pygame.draw.line(screen, col, (sx - 6, y_mid - 5), (sx + 6, y_mid + 5), 2)
    pygame.draw.line(screen, col, (sx - 6, y_mid + 5), (sx + 6, y_mid - 5), 2)
    pygame.draw.polygon(screen, col, [(sx + 6, y_mid + 5), (sx + 2, y_mid + 5), (sx + 6, y_mid + 1)])
    plx = sx + btn_gap
    pl_col = COLOR_PALETTE[color_btn_idx][2] if view_mode in ("playlists", "inside_playlist") else btn_col
    line_w = 14; line_h = 2; gap = 5
    start_y = y_mid - (line_h * 3 + gap * 2) // 2
    for k in range(3):
        pygame.draw.rect(screen, pl_col, (plx - line_w // 2, start_y + k * (line_h + gap), line_w, line_h))
    pos = engine.get_position_seconds()
    time_surf = FONT_BIG.render(fmt_time(pos), True, COLOR_PALETTE[color_btn_idx][2])
    time_x = plx + 22
    time_y = (TOP_H - time_surf.get_height()) // 2
    screen.blit(time_surf, (time_x, time_y))

    dots_x = WIDTH - 18
    search_r = search_icon_rect()
    title_x = time_x + time_surf.get_width() + 10
    avail_w = max(40, search_r.x - 8 - title_x)
    if current_track_index is not None and current_track_index < len(playlist):
        title = playlist[current_track_index][0]
        shown = title
        while FONT_MED.size(shown)[0] > avail_w and len(shown) > 3:
            shown = shown[:-1]
        if shown != title:
            shown = shown[:-1] + "…"
        draw_text(shown, FONT_MED, WHITE, title_x, 10)
        draw_text(f"({playlist[current_track_index][1]})", FONT_SMALL, COLOR_PALETTE[color_btn_idx][2], title_x, 28)
    else:
        draw_text("Нет", FONT_MED, (120, 120, 120), title_x, 8)
        draw_text("трека", FONT_MED, (120, 120, 120), title_x, 26)

    draw_search_icon()
    for i in range(3):
        pygame.draw.circle(screen, WHITE, (dots_x, 14 + i * 6), 2)

def draw_seek_bar():
    y = TOP_H + 10
    if search_open:
        y += 26
    x1, x2 = PAD, WIDTH - PAD
    pygame.draw.rect(screen, (45, 45, 55), (x1, y, x2 - x1, 6))
    dur = engine.get_duration_seconds()
    pos = engine.get_position_seconds()
    frac = (pos / dur) if dur > 0 else 0
    frac = max(0.0, min(1.0, frac))
    fill_w = int((x2 - x1) * frac)
    pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], (x1, y, fill_w, 6))
    hx = x1 + fill_w
    pygame.draw.circle(screen, WHITE, (hx, y + 3), 7)
    pygame.draw.circle(screen, COLOR_PALETTE[color_btn_idx][2], (hx, y + 3), 7, 1)

def draw_spectrum():
    r = layout["spectrum"]
    rect = pygame.Rect(r["x"], r["y"], r["w"], r["h"])
    if search_open:
        rect.y += 26
    panel_col = COLOR_PALETTE[color_panel_idx][1]
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    surf.fill((panel_col[0], panel_col[1], panel_col[2], panel_alpha))
    screen.blit(surf, (rect.x, rect.y))
    vals = engine.get_spectrum()
    n = len(vals)
    bar_w = max(2, rect.width // max(1, n))
    c1, c2 = COLOR_PALETTE[color_virt_idx][1], COLOR_PALETTE[color_virt_idx][2]
    for i, v in enumerate(vals):
        h = int(v * (rect.height - 2))
        x = rect.x + i * bar_w
        y = rect.bottom - h
        for k in range(h):
            t = k / max(1, h)
            col = (int(c1[0] + (c2[0] - c1[0]) * t),
                   int(c1[1] + (c2[1] - c1[1]) * t),
                   int(c1[2] + (c2[2] - c1[2]) * t))
            pygame.draw.line(screen, col, (x + 1, y + k), (x + bar_w - 2, y + k))
    if edit_mode:
        pygame.draw.rect(screen, RED, rect, 2)
        draw_resize_handle(rect)

def draw_mixer():
    r = layout["mixer"]
    rect = pygame.Rect(r["x"], r["y"], r["w"], r["h"])
    if search_open:
        rect.y += 26
    panel_col = COLOR_PALETTE[color_panel_idx][1]
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    surf.fill((panel_col[0], panel_col[1], panel_col[2], panel_alpha))
    screen.blit(surf, (rect.x, rect.y))
    if edit_mode:
        pygame.draw.rect(screen, RED, rect, 2)
        draw_resize_handle(rect)
    vol_y = rect.y + 14
    vol_x1 = rect.x + 30
    vol_x2 = rect.right - 14
    dx = rect.x + 10
    dy = vol_y
    pygame.draw.polygon(screen, COLOR_PALETTE[color_btn_idx][3], [
        (dx, dy - 3), (dx + 3, dy - 3), (dx + 6, dy - 6),
        (dx + 6, dy + 6), (dx + 3, dy + 3), (dx, dy + 3)])
    pygame.draw.rect(screen, (60, 60, 70), (vol_x1, vol_y - 2, vol_x2 - vol_x1, 4))
    fill_w = int((vol_x2 - vol_x1) * volume_value)
    pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], (vol_x1, vol_y - 2, fill_w, 4))
    pygame.draw.circle(screen, WHITE, (vol_x1 + fill_w, vol_y), 5)
    eq_top = rect.y + 30
    eq_bot = rect.bottom - 6
    track_h = eq_bot - eq_top
    n = len(engine.EQ_BANDS)
    step = rect.width / n
    for i, value in enumerate(eq_values):
        cx = rect.x + int(step * i) + int(step / 2)
        pygame.draw.rect(screen, (60, 60, 70), (cx - 1, eq_top, 3, track_h))
        handle_y = eq_top + int((1 - (value + 20) / 40) * track_h)
        pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], (cx - 9, handle_y - 2, 18, 4))

def mixer_handle_rects():
    r = layout["mixer"]
    rect = pygame.Rect(r["x"], r["y"], r["w"], r["h"])
    if search_open:
        rect.y += 26
    eq_top = rect.y + 30
    eq_bot = rect.bottom - 6
    track_h = eq_bot - eq_top
    n = len(engine.EQ_BANDS)
    step = rect.width / n
    result = []
    for i, value in enumerate(eq_values):
        cx = rect.x + int(step * i) + int(step / 2)
        handle_y = eq_top + int((1 - (value + 20) / 40) * track_h)
        result.append((i, pygame.Rect(cx - 14, handle_y - 10, 28, 20)))
    return result

def mixer_value_from_y(mouse_y):
    r = layout["mixer"]
    rect = pygame.Rect(r["x"], r["y"], r["w"], r["h"])
    if search_open:
        rect.y += 26
    eq_top = rect.y + 30
    eq_bot = rect.bottom - 6
    track_h = eq_bot - eq_top
    rel_y = mouse_y - eq_top
    rel_y = max(0, min(track_h, rel_y))
    return round(((1 - rel_y / track_h) * 40) - 20, 1)

def volume_bar_rect():
    r = layout["mixer"]
    rect = pygame.Rect(r["x"] + 30, r["y"] + 6, r["w"] - 44, 16)
    if search_open:
        rect.y += 26
    return rect

def draw_playlist_panel():
    r = layout["playlist"]
    rect = pygame.Rect(r["x"], r["y"], r["w"], r["h"])
    if search_open:
        rect.y += 26
    panel_col = COLOR_PALETTE[color_panel_idx][1]
    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    surf.fill((panel_col[0], panel_col[1], panel_col[2], panel_alpha))
    screen.blit(surf, (rect.x, rect.y))
    if edit_mode:
        pygame.draw.rect(screen, RED, rect, 2)
        draw_resize_handle(rect)
    if add_mode:
        draw_add_mode_list(rect)
    elif view_mode == "playlists":
        draw_playlists_list(rect)
    else:
        draw_tracks_list(rect)

def draw_playlists_list(rect):
    global playlists_scroll
    row_h = 26
    btn_rect = pygame.Rect(rect.x + 6, rect.y + 6, rect.w - 12, 22)
    pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], btn_rect)
    draw_text("+ Новый плейлист", FONT_SMALL, WHITE, btn_rect.x + 8, btn_rect.y + 5)
    names = list(playlists.keys())
    y0 = rect.y + 34
    visible_rows = max(1, (rect.bottom - y0 - 6) // row_h)
    max_scroll = max(0, len(names) - visible_rows)
    if playlists_scroll > max_scroll:
        playlists_scroll = max_scroll
    if playlists_scroll < 0:
        playlists_scroll = 0
    for i in range(visible_rows):
        idx = i + playlists_scroll
        if idx >= len(names):
            break
        name = names[idx]
        count = len(playlists[name])
        y = y0 + i * row_h
        row_rect = pygame.Rect(rect.x + 4, y, rect.w - 8, row_h - 2)
        pygame.draw.rect(screen, (25, 25, 32), row_rect)
        draw_text(f"{name[:22]}  ({count})", FONT_MED, WHITE, row_rect.x + 6, row_rect.y + 5)
        edit_rect = pygame.Rect(row_rect.right - 40, row_rect.y + 2, 18, 18)
        pygame.draw.rect(screen, (50, 50, 60), edit_rect)
        draw_text("R", FONT_SMALL, WHITE, edit_rect.x + 5, edit_rect.y + 3)
        del_rect = pygame.Rect(row_rect.right - 20, row_rect.y + 2, 18, 18)
        pygame.draw.rect(screen, (80, 30, 30), del_rect)
        draw_text("X", FONT_SMALL, WHITE, del_rect.x + 5, del_rect.y + 3)
    if len(names) > visible_rows:
        sb_x = rect.right - 6
        sb_y = y0
        sb_h = rect.bottom - y0 - 6
        pygame.draw.rect(screen, (40, 40, 50), (sb_x, sb_y, 4, sb_h))
        handle_h = max(20, int(sb_h * visible_rows / len(names)))
        handle_y = sb_y + int((sb_h - handle_h) * playlists_scroll / max(1, max_scroll))
        pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], (sb_x, handle_y, 4, handle_h))

def draw_add_mode_list(rect):
    global add_scroll
    save_rect = pygame.Rect(rect.x + 6, rect.y + 6, (rect.w - 18) // 2, 22)
    cancel_rect = pygame.Rect(rect.x + 12 + (rect.w - 18) // 2, rect.y + 6, (rect.w - 18) // 2, 22)
    pygame.draw.rect(screen, (30, 80, 40), save_rect)
    draw_text("Сохранить", FONT_SMALL, WHITE, save_rect.x + 6, save_rect.y + 5)
    pygame.draw.rect(screen, (80, 30, 30), cancel_rect)
    draw_text("Отмена", FONT_SMALL, WHITE, cancel_rect.x + 6, cancel_rect.y + 5)
    if not playlist:
        draw_text("Библиотека пуста", FONT_SMALL, (120, 120, 120), rect.x + 8, rect.y + 40)
        return
    row_h = 22
    y0 = rect.y + 34
    visible_rows = max(1, (rect.bottom - y0 - 6) // row_h)
    max_scroll = max(0, len(playlist) - visible_rows)
    if add_scroll > max_scroll:
        add_scroll = max_scroll
    if add_scroll < 0:
        add_scroll = 0
    for i in range(visible_rows):
        idx = i + add_scroll
        if idx >= len(playlist):
            break
        title, dur_str, path, filename = playlist[idx]
        y = y0 + i * row_h
        row_rect = pygame.Rect(rect.x + 4, y, rect.w - 8, row_h - 1)
        if idx in add_selected:
            pygame.draw.rect(screen, (40, 70, 100), row_rect)
        else:
            pygame.draw.rect(screen, (20, 20, 25), row_rect)
        check_x = row_rect.x + 4
        check_y = row_rect.y + 3
        pygame.draw.rect(screen, WHITE, (check_x, check_y, 14, 14), 1)
        if idx in add_selected:
            pygame.draw.line(screen, GREEN, (check_x + 3, check_y + 7), (check_x + 6, check_y + 10), 2)
            pygame.draw.line(screen, GREEN, (check_x + 6, check_y + 10), (check_x + 11, check_y + 4), 2)
        draw_text(title[:24], FONT_SMALL, WHITE, check_x + 20, row_rect.y + 4)
        draw_text(dur_str, FONT_SMALL, COLOR_PALETTE[color_btn_idx][2], row_rect.right - 38, row_rect.y + 4)
    if len(playlist) > visible_rows:
        sb_x = rect.right - 6
        sb_y = y0
        sb_h = rect.bottom - y0 - 6
        pygame.draw.rect(screen, (40, 40, 50), (sb_x, sb_y, 4, sb_h))
        handle_h = max(20, int(sb_h * visible_rows / len(playlist)))
        handle_y = sb_y + int((sb_h - handle_h) * add_scroll / max(1, max_scroll))
        pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], (sb_x, handle_y, 4, handle_h))

def draw_tracks_list(rect):
    global playlist_scroll
    tracks = get_tracks_for_current_view()
    offset_y = 0
    if view_mode == "inside_playlist":
        add_btn = pygame.Rect(rect.x + 6, rect.y + 6, (rect.w - 18) // 2, 22)
        play_btn = pygame.Rect(rect.x + 12 + (rect.w - 18) // 2, rect.y + 6, (rect.w - 18) // 2, 22)
        pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], add_btn)
        draw_text("+ Добавить", FONT_SMALL, WHITE, add_btn.x + 6, add_btn.y + 5)
        pygame.draw.rect(screen, (30, 80, 40), play_btn)
        draw_text("> Играть все", FONT_SMALL, WHITE, play_btn.x + 6, play_btn.y + 5)
        offset_y = 26
    if not tracks:
        draw_text("Пусто. ... -> ADD.", FONT_SMALL, (100, 100, 100), rect.x + 8, rect.y + 8 + offset_y)
        return
    row_h = 20
    visible_rows = max(1, (rect.height - 12 - offset_y) // row_h)
    total_rows = len(tracks)
    max_scroll = max(0, total_rows - visible_rows)
    if playlist_scroll > max_scroll:
        playlist_scroll = max_scroll
    if playlist_scroll < 0:
        playlist_scroll = 0
    for i in range(visible_rows):
        idx = i + playlist_scroll
        if idx >= total_rows:
            break
        title, dur_str, path, filename = tracks[idx]
        y = rect.y + 6 + offset_y + i * row_h
        is_current = False
        if current_track_index is not None and current_track_index < len(playlist):
            is_current = (playlist[current_track_index][3] == filename)
        color = COLOR_PALETTE[color_btn_idx][2] if is_current else WHITE
        draw_text(f"{idx+1}.", FONT_SMALL, color, rect.x + 6, y)
        draw_text(title[:24], FONT_SMALL, color, rect.x + 24, y)
        if view_mode == "inside_playlist":
            del_rect = pygame.Rect(rect.right - 20, y + 1, 16, 16)
            pygame.draw.rect(screen, (80, 30, 30), del_rect)
            draw_text("X", FONT_SMALL, WHITE, del_rect.x + 4, del_rect.y + 2)
            draw_text(dur_str, FONT_SMALL, color, rect.x + rect.width - 60, y)
        else:
            draw_text(dur_str, FONT_SMALL, color, rect.x + rect.width - 38, y)
    if total_rows > visible_rows:
        sb_x = rect.right - 6
        sb_y = rect.y + 4 + offset_y
        sb_h = rect.height - 8 - offset_y
        pygame.draw.rect(screen, (40, 40, 50), (sb_x, sb_y, 4, sb_h))
        handle_h = max(20, int(sb_h * visible_rows / total_rows))
        handle_y = sb_y + int((sb_h - handle_h) * playlist_scroll / max(1, max_scroll))
        pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], (sb_x, handle_y, 4, handle_h))

def draw_resize_handle(rect):
    pygame.draw.rect(screen, RED, (rect.right - 10, rect.bottom - 10, 8, 8))

def menu_item_rects():
    items = ["ADD", "BACKGROUND", "EDIT", "TRANSPARENCY",
             "COLOR VIRT", "COLOR PANEL", "COLOR TOP", "COLOR BTN",
             "AUTOSTART", "RESET", "EXIT"]
    menu_w = 170
    item_h = 24
    menu_h = item_h * len(items) + 8
    mx = WIDTH - menu_w - PAD
    my = 40
    result = []
    for i, item in enumerate(items):
        y = my + 4 + i * item_h
        result.append((item, pygame.Rect(mx, y, menu_w, item_h)))
    return result, mx, my, menu_w, menu_h

def draw_menu():
    if not menu_open:
        return
    item_rects, mx, my, menu_w, menu_h = menu_item_rects()
    bg = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
    bg.fill((20, 20, 25, 240))
    screen.blit(bg, (mx, my))
    pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], (mx, my, menu_w, menu_h), 1)
    for item, rect in item_rects:
        color = COLOR_PALETTE[color_btn_idx][2] if (item == "EDIT" and edit_mode) else WHITE
        if item == "COLOR VIRT":
            pygame.draw.rect(screen, COLOR_PALETTE[color_virt_idx][2], (rect.right - 18, rect.y + 7, 10, 10))
        if item == "COLOR PANEL":
            pygame.draw.rect(screen, COLOR_PALETTE[color_panel_idx][1], (rect.right - 18, rect.y + 7, 10, 10))
        if item == "COLOR TOP":
            pygame.draw.rect(screen, COLOR_PALETTE[color_top_idx][3], (rect.right - 18, rect.y + 7, 10, 10))
        if item == "COLOR BTN":
            pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], (rect.right - 18, rect.y + 7, 10, 10))
        if item == "AUTOSTART":
            st = "ON" if is_autostart_enabled() else "OFF"
            st_col = GREEN if st == "ON" else (150, 150, 150)
            draw_text(st, FONT_SMALL, st_col, rect.right - 32, rect.y + 6)
        draw_text(item, FONT_SMALL, color, rect.x + 8, rect.y + 5)

def color_picker_rects():
    n = len(COLOR_PALETTE)
    sw = 30
    sh = 30
    gap = 4
    total_w = n * sw + (n - 1) * gap
    mx = WIDTH // 2 - total_w // 2
    my = HEIGHT // 2 - sh // 2
    result = []
    for i in range(n):
        x = mx + i * (sw + gap)
        result.append((i, pygame.Rect(x, my, sw, sh)))
    return result, mx - 8, my - 28, total_w + 16, sh + 36

def draw_color_picker():
    if color_picker_target is None:
        return
    rects, bx, by, bw, bh = color_picker_rects()
    bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
    bg.fill((20, 20, 25, 245))
    screen.blit(bg, (bx, by))
    pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], (bx, by, bw, bh), 1)
    title = f"Цвет: {color_picker_target.upper()}"
    draw_text(title, FONT_SMALL, WHITE, bx + 8, by + 4)
    cur_idx = {"virt": color_virt_idx, "panel": color_panel_idx,
               "btn": color_btn_idx, "top": color_top_idx}.get(color_picker_target, 0)
    for i, rect in rects:
        if color_picker_target == "top":
            col = COLOR_PALETTE[i][3]
        elif color_picker_target == "panel":
            col = COLOR_PALETTE[i][1]
        else:
            col = COLOR_PALETTE[i][2]
        pygame.draw.rect(screen, col, rect)
        border = WHITE if i == cur_idx else (80, 80, 80)
        pygame.draw.rect(screen, border, rect, 2)
        bright = COLOR_PALETTE[i][2]
        pygame.draw.circle(screen, bright, (rect.x + rect.w // 2, rect.y + rect.h // 2), 8)

def transparency_slider_rect():
    bw = 260
    bh = 70
    bx = WIDTH // 2 - bw // 2
    by = HEIGHT // 2 - bh // 2
    track = pygame.Rect(bx + 16, by + 36, bw - 32, 8)
    return track, bx, by, bw, bh

def draw_transparency_slider():
    if not transparency_open:
        return
    track, bx, by, bw, bh = transparency_slider_rect()
    bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
    bg.fill((20, 20, 25, 245))
    screen.blit(bg, (bx, by))
    pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], (bx, by, bw, bh), 1)
    title = "Прозрачность ВЕРХ" if transparency_target == "top" else "Прозрачность ПАНЕЛЕЙ"
    draw_text(title, FONT_SMALL, WHITE, bx + 10, by + 6)
    pygame.draw.rect(screen, (60, 60, 70), track)
    cur_alpha = top_alpha if transparency_target == "top" else panel_alpha
    frac = cur_alpha / 255.0
    fill_w = int(track.w * frac)
    pygame.draw.rect(screen, COLOR_PALETTE[color_btn_idx][2], (track.x, track.y, fill_w, track.h))
    hx = track.x + fill_w
    pygame.draw.circle(screen, WHITE, (hx, track.y + track.h // 2), 8)
    draw_text(f"{int(frac*100)}%", FONT_MED, WHITE, bx + bw - 55, by + 6)
    tg_rect = pygame.Rect(bx + bw - 120, by + 4, 60, 18)
    pygame.draw.rect(screen, (40, 40, 50), tg_rect)
    draw_text("ВЕРХ", FONT_SMALL, WHITE, tg_rect.x + 4, tg_rect.y + 3)
    tg2_rect = pygame.Rect(bx + bw - 60, by + 4, 55, 18)
    pygame.draw.rect(screen, (40, 40, 50), tg2_rect)
    draw_text("ПАНЕЛЬ", FONT_SMALL, WHITE, tg2_rect.x + 4, tg2_rect.y + 3)

def draw_download_status():
    with progress_lock:
        active = download_active
        status = download_status
    if active:
        y = layout["playlist"]["y"] - 14
        if search_open:
            y += 26
        draw_text(status[:60], FONT_SMALL, GREEN, PAD, y)

def draw_ui():
    screen.fill(BLACK)
    if background_surface:
        bg = pygame.transform.scale(background_surface, (WIDTH, HEIGHT))
        screen.blit(bg, (0, 0))
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        screen.blit(ov, (0, 0))
    draw_top_bar()
    if search_open:
        draw_search_field()
    draw_seek_bar()
    draw_spectrum()
    draw_mixer()
    draw_playlist_panel()
    draw_download_status()
    draw_menu()
    draw_color_picker()
    draw_transparency_slider()
    pygame.display.flip()

def block_rect(name):
    r = layout[name]
    return pygame.Rect(r["x"], r["y"], r["w"], r["h"])

def hit_block(pos):
    for name in ("spectrum", "mixer", "playlist"):
        if block_rect(name).collidepoint(pos):
            return name
    return None

def hit_resize_handle(pos):
    for name in ("spectrum", "mixer", "playlist"):
        r = layout[name]
        hx = r["x"] + r["w"] - 12
        hy = r["y"] + r["h"] - 12
        if hx <= pos[0] <= hx + 12 and hy <= pos[1] <= hy + 12:
            return name
    return None

def hit_menu_region(pos):
    return (WIDTH - 32 <= pos[0] <= WIDTH - 4) and (4 <= pos[1] <= 38)

def hit_menu_item(pos):
    if not menu_open:
        return None
    item_rects, _, _, _, _ = menu_item_rects()
    for item, rect in item_rects:
        if rect.collidepoint(pos):
            return item
    return None

def seek_bar_rect():
    y = TOP_H + 8
    if search_open:
        y += 26
    return pygame.Rect(PAD, y, WIDTH - PAD * 2, 22)

def handle_playlist_panel_click(x, y):
    global view_mode, active_playlist_name, playlists_scroll, playlist_scroll
    global add_mode, add_selected, add_scroll
    r = layout["playlist"]
    rect = pygame.Rect(r["x"], r["y"], r["w"], r["h"])
    if search_open:
        rect.y += 26
    if not rect.collidepoint((x, y)):
        return False
    if add_mode:
        save_rect = pygame.Rect(rect.x + 6, rect.y + 6, (rect.w - 18) // 2, 22)
        cancel_rect = pygame.Rect(rect.x + 12 + (rect.w - 18) // 2, rect.y + 6, (rect.w - 18) // 2, 22)
        if save_rect.collidepoint((x, y)):
            if active_playlist_name:
                if active_playlist_name not in playlists:
                    playlists[active_playlist_name] = []
                for i in add_selected:
                    if 0 <= i < len(playlist):
                        fname = playlist[i][3]
                        if fname not in playlists[active_playlist_name]:
                            playlists[active_playlist_name].append(fname)
                save_playlists()
            add_mode = False
            add_selected = set()
            add_scroll = 0
            return True
        if cancel_rect.collidepoint((x, y)):
            add_mode = False
            add_selected = set()
            add_scroll = 0
            return True
        row_h = 22
        y0 = rect.y + 34
        visible_rows = max(1, (rect.bottom - y0 - 6) // row_h)
        for i in range(visible_rows):
            idx = i + add_scroll
            if idx >= len(playlist):
                break
            row_y = y0 + i * row_h
            if row_y <= y < row_y + row_h:
                if idx in add_selected:
                    add_selected.discard(idx)
                else:
                    add_selected.add(idx)
                return True
        return True
    if view_mode == "playlists":
        btn_rect = pygame.Rect(rect.x + 6, rect.y + 6, rect.w - 12, 22)
        if btn_rect.collidepoint((x, y)):
            new_playlist_dialog()
            return True
        names = list(playlists.keys())
        y0 = rect.y + 34
        row_h = 26
        visible_rows = max(1, (rect.bottom - y0 - 6) // row_h)
        for i in range(visible_rows):
            idx = i + playlists_scroll
            if idx >= len(names):
                break
            name = names[idx]
            row_y = y0 + i * row_h
            row_rect = pygame.Rect(rect.x + 4, row_y, rect.w - 8, row_h - 2)
            if not row_rect.collidepoint((x, y)):
                continue
            edit_rect = pygame.Rect(row_rect.right - 40, row_rect.y + 2, 18, 18)
            if edit_rect.collidepoint((x, y)):
                rename_playlist_dialog(name)
                return True
            del_rect = pygame.Rect(row_rect.right - 20, row_rect.y + 2, 18, 18)
            if del_rect.collidepoint((x, y)):
                if name != "Одиночные":
                    del playlists[name]
                    save_playlists()
                return True
            active_playlist_name = name
            view_mode = "inside_playlist"
            playlist_scroll = 0
            return True
        return True
    elif view_mode == "inside_playlist":
        add_btn = pygame.Rect(rect.x + 6, rect.y + 6, (rect.w - 18) // 2, 22)
        play_btn = pygame.Rect(rect.x + 12 + (rect.w - 18) // 2, rect.y + 6, (rect.w - 18) // 2, 22)
        if add_btn.collidepoint((x, y)):
            add_mode = True
            add_selected = set()
            add_scroll = 0
            return True
        if play_btn.collidepoint((x, y)):
            playlist_scroll = 0
            play_current_view_index(0)
            return True
        tracks = get_tracks_for_current_view()
        if not tracks:
            return True
        y0 = rect.y + 6 + 26
        row_h = 20
        visible_rows = max(1, (rect.bottom - y0 - 6) // row_h)
        for i in range(visible_rows):
            idx = i + playlist_scroll
            if idx >= len(tracks):
                break
            row_y = y0 + i * row_h
            if row_y <= y < row_y + row_h:
                del_rect = pygame.Rect(rect.right - 20, row_y + 1, 16, 16)
                if del_rect.collidepoint((x, y)):
                    fname = tracks[idx][3]
                    if active_playlist_name and fname in playlists.get(active_playlist_name, []):
                        playlists[active_playlist_name].remove(fname)
                        save_playlists()
                    return True
                play_current_view_index(idx)
                return True
        return True
    elif view_mode == "tracks":
        tracks = get_tracks_for_current_view()
        if not tracks:
            return True
        y0 = rect.y + 6
        row_h = 20
        visible_rows = max(1, (rect.bottom - y0 - 6) // row_h)
        for i in range(visible_rows):
            idx = i + playlist_scroll
            if idx >= len(tracks):
                break
            row_y = y0 + i * row_h
            if row_y <= y < row_y + row_h:
                play_current_view_index(idx)
                return True
        return True
    return False

def handle_mouse_down(pos, button=1):
    global dragging_index, drag_offset_y, current_track_index
    global dragging_block, drag_block_offset
    global edit_mode, resize_block, resize_start, dragging_seek
    global menu_open, shuffle, dragging_volume
    global view_mode, active_playlist_name
    global add_mode, add_selected, add_scroll
    global panel_alpha, top_alpha
    global color_virt_idx, color_panel_idx, color_btn_idx, color_top_idx
    global volume_value
    global search_open, search_text
    global color_picker_target
    global transparency_open, transparency_target, dragging_transparency

    if button != 1:
        return
    x, y = pos

    if color_picker_target is not None:
        rects, bx, by, bw, bh = color_picker_rects()
        for i, rect in rects:
            if rect.collidepoint((x, y)):
                if color_picker_target == "virt":
                    color_virt_idx = i
                elif color_picker_target == "panel":
                    color_panel_idx = i
                elif color_picker_target == "btn":
                    color_btn_idx = i
                elif color_picker_target == "top":
                    color_top_idx = i
                save_settings()
                color_picker_target = None
                return
        if not (bx <= x <= bx + bw and by <= y <= by + bh):
            color_picker_target = None
        return

    if transparency_open:
        track, bx, by, bw, bh = transparency_slider_rect()
        tg_top = pygame.Rect(bx + bw - 120, by + 4, 60, 18)
        tg_panel = pygame.Rect(bx + bw - 60, by + 4, 55, 18)
        if tg_top.collidepoint((x, y)):
            transparency_target = "top"
            return
        if tg_panel.collidepoint((x, y)):
            transparency_target = "panel"
            return
        if track.collidepoint((x, y)) or (track.x - 10 <= x <= track.right + 10 and track.y - 10 <= y <= track.bottom + 10):
            dragging_transparency = True
            frac = (x - track.x) / max(1, track.w)
            frac = max(0.0, min(1.0, frac))
            val = int(frac * 255)
            if transparency_target == "top":
                top_alpha = val
            else:
                panel_alpha = val
            save_settings()
            return
        if not (bx <= x <= bx + bw and by <= y <= by + bh):
            transparency_open = False
        return

    if search_open:
        fr = search_field_rect()
        x_rect = pygame.Rect(fr.right - 22, fr.y + 4, 18, 18)
        if x_rect.collidepoint((x, y)):
            search_text = ""
            return
        if fr.collidepoint((x, y)):
            return

    if search_icon_rect().collidepoint((x, y)):
        search_open = not search_open
        if not search_open:
            search_text = ""
        return

    item = hit_menu_item(pos)
    if item:
        if item == "ADD":
            open_url_dialog()
        elif item == "BACKGROUND":
            from tkinter import Tk, filedialog
            root = Tk(); root.withdraw(); root.attributes("-topmost", True)
            fp = filedialog.askopenfilename(title="Фон",
                filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
            root.destroy()
            if fp:
                load_background_image(fp)
        elif item == "EDIT":
            edit_mode = not edit_mode
        elif item == "TRANSPARENCY":
            transparency_open = True
            transparency_target = "panel"
        elif item == "COLOR VIRT":
            color_picker_target = "virt"
        elif item == "COLOR PANEL":
            color_picker_target = "panel"
        elif item == "COLOR TOP":
            color_picker_target = "top"
        elif item == "COLOR BTN":
            color_picker_target = "btn"
        elif item == "AUTOSTART":
            set_autostart(not is_autostart_enabled())
        elif item == "RESET":
            layout.clear()
            layout.update(default_layout(WIDTH, HEIGHT))
            save_layout()
        elif item == "EXIT":
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        menu_open = False
        return
    if hit_menu_region(pos):
        menu_open = not menu_open
        return
    if menu_open:
        menu_open = False
    if y < TOP_H:
        btn_gap = 26
        px = 14
        cx = px + btn_gap + 8
        nx = cx + btn_gap + 8
        sx = nx + btn_gap
        plx = sx + btn_gap
        if abs(x - px) <= 14:
            prev_track()
        elif abs(x - cx) <= 14:
            toggle_play_pause()
        elif abs(x - nx) <= 14:
            next_track()
        elif abs(x - sx) <= 14:
            shuffle = not shuffle
            if shuffle:
                current_file = None
                if current_track_index is not None and current_track_index < len(playlist):
                    current_file = playlist[current_track_index][3]
                rebuild_shuffle_order(start_filename=current_file)
            save_settings()
        elif abs(x - plx) <= 16:
            if view_mode == "tracks":
                view_mode = "playlists"
                active_playlist_name = None
                playlists_scroll = 0
            else:
                view_mode = "tracks"
                active_playlist_name = None
                playlist_scroll = 0
        return
    if seek_bar_rect().collidepoint(pos):
        dragging_seek = True
        frac = (x - PAD) / max(1, WIDTH - PAD * 2)
        dur = engine.get_duration_seconds()
        engine.seek(frac * dur)
        return
    if volume_bar_rect().collidepoint(pos):
        dragging_volume = True
        vbr = volume_bar_rect()
        frac = (x - (vbr.x + 4)) / max(1, vbr.w - 8)
        volume_value = max(0.0, min(1.0, frac))
        engine.volume = volume_value
        save_settings()
        return
    if handle_playlist_panel_click(x, y):
        return
    if edit_mode:
        name = hit_resize_handle(pos)
        if name:
            resize_block = name
            r = layout[name]
            resize_start = (x, y, r["w"], r["h"])
            return
        name = hit_block(pos)
        if name:
            dragging_block = name
            r = layout[name]
            drag_block_offset = (x - r["x"], y - r["y"])
            return
        return
    mr = layout["mixer"]
    mr_y = mr["y"] + (26 if search_open else 0)
    if mr["x"] <= x <= mr["x"] + mr["w"] and mr_y <= y <= mr_y + mr["h"]:
        for i, hit_rect in mixer_handle_rects():
            if hit_rect.collidepoint((x, y)):
                dragging_index = i
                drag_offset_y = y - (hit_rect.y + hit_rect.h // 2)
                return
        return

def handle_mouse_motion(pos):
    global dragging_index, dragging_block, resize_block, dragging_seek, dragging_volume
    global volume_value, dragging_transparency
    global panel_alpha, top_alpha
    x, y = pos
    if dragging_transparency:
        track, bx, by, bw, bh = transparency_slider_rect()
        frac = max(0.0, min(1.0, (x - track.x) / max(1, track.w)))
        val = int(frac * 255)
        if transparency_target == "top":
            top_alpha = val
        else:
            panel_alpha = val
        return
    if dragging_seek:
        dur = engine.get_duration_seconds()
        frac = max(0.0, min(1.0, (x - PAD) / max(1, WIDTH - PAD * 2)))
        engine.seek(frac * dur)
        return
    if dragging_volume:
        vbr = volume_bar_rect()
        frac = max(0.0, min(1.0, (x - (vbr.x + 4)) / max(1, vbr.w - 8)))
        volume_value = frac
        engine.volume = frac
        return
    if resize_block:
        r = layout[resize_block]
        sw, sh = resize_start[2], resize_start[3]
        r["w"] = max(60, sw + (x - resize_start[0]))
        r["h"] = max(30, sh + (y - resize_start[1]))
        r["w"] = min(r["w"], WIDTH - r["x"] - PAD)
        r["h"] = min(r["h"], HEIGHT - PAD - r["y"])
        return
    if dragging_block:
        r = layout[dragging_block]
        r["x"] = max(PAD, min(WIDTH - r["w"] - PAD, x - drag_block_offset[0]))
        r["y"] = max(TOP_H, min(HEIGHT - r["h"] - PAD, y - drag_block_offset[1]))
        return
    if dragging_index is not None:
        value = mixer_value_from_y(y)
        eq_values[dragging_index] = value
        engine.set_eq_gain(dragging_index, value)

def handle_mouse_up():
    global dragging_index, dragging_block, resize_block, resize_start
    global dragging_seek, dragging_volume, dragging_transparency
    if dragging_block or resize_block:
        save_layout()
    if dragging_volume or dragging_transparency:
        save_settings()
    dragging_index = None
    dragging_block = None
    resize_block = None
    resize_start = None
    dragging_seek = False
    dragging_volume = False
    dragging_transparency = False

def handle_wheel(pos, dy):
    global volume_value, playlist_scroll, playlists_scroll, add_scroll
    if volume_bar_rect().collidepoint(pos):
        volume_value = max(0.0, min(1.0, volume_value + dy * 0.01))
        engine.volume = volume_value
        save_settings()
        return
    pr = layout["playlist"]
    pr_y = pr["y"] + (26 if search_open else 0)
    if (pr["x"] <= pos[0] <= pr["x"] + pr["w"] and
        pr_y <= pos[1] <= pr_y + pr["h"]):
        if add_mode:
            add_scroll = max(0, add_scroll - dy)
        elif view_mode == "playlists":
            playlists_scroll = max(0, playlists_scroll - dy)
        else:
            playlist_scroll = max(0, playlist_scroll - dy)

def handle_text_input(event):
    global search_text
    if not search_open:
        return
    if event.key == pygame.K_BACKSPACE:
        search_text = search_text[:-1]
    elif event.key == pygame.K_ESCAPE:
        search_text = ""
    elif event.key == pygame.K_RETURN:
        pass
    elif event.unicode and event.unicode.isprintable():
        search_text += event.unicode

cleanup_music_dir()
start_tray()
refresh_library()
engine.volume = volume_value
if shuffle:
    rebuild_shuffle_order()
clock = pygame.time.Clock()
last_refresh = time.time()
running = True
while running:
    # Обработка запросов из трея в ГЛАВНОМ потоке
    process_tray_requests()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if app_should_quit:
                running = False
            else:
                hide_to_tray()
        elif event.type == pygame.VIDEORESIZE:
            old_w, old_h = WIDTH, HEIGHT
            WIDTH, HEIGHT = max(MIN_W, event.w), max(MIN_H, event.h)
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
            relayout_for_window(old_w, old_h, WIDTH, HEIGHT)
            if background_surface:
                background_surface = pygame.transform.scale(background_surface, (WIDTH, HEIGHT))
        elif event.type == pygame.MOUSEBUTTONDOWN:
            handle_mouse_down(event.pos, event.button)
        elif event.type == pygame.MOUSEMOTION:
            handle_mouse_motion(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP:
            handle_mouse_up()
        elif event.type == pygame.MOUSEWHEEL:
            handle_wheel(pygame.mouse.get_pos(), event.y)
        elif event.type == pygame.KEYDOWN:
            if search_open and event.key != pygame.K_ESCAPE:
                handle_text_input(event)
                continue
            if event.key == pygame.K_F11:
                pygame.display.toggle_fullscreen()
            elif event.key == pygame.K_ESCAPE:
                if color_picker_target is not None:
                    color_picker_target = None
                elif transparency_open:
                    transparency_open = False
                elif search_open:
                    search_open = False
                    search_text = ""
                elif add_mode:
                    add_mode = False
                    add_selected = set()
                    add_scroll = 0
                elif view_mode != "tracks":
                    view_mode = "tracks"
                    active_playlist_name = None
                else:
                    running = False
    if engine.just_finished:
        engine.just_finished = False
        if repeat:
            if current_track_index is not None:
                path = playlist[current_track_index][2]
                engine.load(path)
                engine.play()
        else:
            next_track()
    if time.time() - last_refresh > 1.0:
        refresh_library()
        last_refresh = time.time()
    draw_ui()
    clock.tick(60)
save_settings()
if tray_icon is not None:
    try:
        tray_icon.stop()
    except Exception:
        pass
if engine.stream:
    engine.stream.stop()
    engine.stream.close()
pygame.quit()
sys.exit()
