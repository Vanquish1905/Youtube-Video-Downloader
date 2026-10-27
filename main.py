#!/usr/bin/env python3
"""
Vanquish Pro Video Downloader (Windows and Linux)
Requirements:  pip install -r requirements.txt (see the file for OS-specific steps)
Recommended:   FFmpeg (needed for 720p+ merged video, MP3 export and audio/video merging)
"""
import json
import os
import platform
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled
from yt_dlp.version import __version__ as YTDLP_VERSION

CONFIG_PATH = Path.home() / ".vanquish_downloader.json"
DEFAULT_CONFIG = {
    "download_path": str(Path.home() / "Downloads" / "VanquishDownloads"),
    "format": "MP4",
    "quality": "1080p",
    "merge": True,
    "playlist": False,
    "concurrent": 3,
    "speed_limit": 0.0,      # MB/s, 0 = unlimited
    "retries": 5,
    "theme": "Midnight Blue",
    "language": "English",
    "ffmpeg_path": "",
}

QUALITY_HEIGHT = {"Best": None, "8K": 4320, "4K": 2160, "1080p": 1080,
                  "720p": 720, "480p": 480, "360p": 360}

THEMES = {
    "Midnight Blue": {"main": "#0ea5e9", "hover": "#0284c7", "bg": "#0f172a", "side": "#1e293b", "card": "#1e293b", "accent": "#38bdf8"},
    "Emerald": {"main": "#10b981", "hover": "#059669", "bg": "#0f1f1a", "side": "#134e4a", "card": "#1a3a36", "accent": "#34d399"},
    "Crimson": {"main": "#ef4444", "hover": "#dc2626", "bg": "#1a0f0f", "side": "#2d1f1f", "card": "#2a1a1a", "accent": "#f87171"},
    "Violet": {"main": "#8b5cf6", "hover": "#7c3aed", "bg": "#1a1625", "side": "#2e2447", "card": "#2a1f42", "accent": "#a78bfa"},
    "Amber": {"main": "#f59e0b", "hover": "#d97706", "bg": "#1a1608", "side": "#2d2812", "card": "#2a2410", "accent": "#fbbf24"},
    "Rose": {"main": "#f43f5e", "hover": "#e11d48", "bg": "#1a0f14", "side": "#2d1f27", "card": "#2a1a22", "accent": "#fb7185"},
}

LANG_KEYS = ("downloader", "queue", "settings", "diagnostics", "url_label", "add_queue", "quick",
             "paste", "start_all", "theme", "language", "location", "cancel", "retry", "remove",
             "open_folder", "start")
_LANG_VALUES = {
    "English": ("Downloader", "Queue", "Settings", "Diagnostics", "Paste YouTube URL(s), one per line:",
                "➕ Add to Queue", "⚡ Quick Download", "📋 Paste", "▶ Start All", "Theme:", "Language:",
                "Download Location", "Cancel", "Retry", "Remove", "Open folder", "Start"),
    "German": ("Downloader", "Warteschlange", "Einstellungen", "Diagnose", "YouTube-URL(s) eingeben, eine pro Zeile:",
               "➕ Zur Warteschlange", "⚡ Schnell-Download", "📋 Einfügen", "▶ Alle starten", "Design:", "Sprache:",
               "Speicherort", "Abbrechen", "Wiederholen", "Entfernen", "Ordner öffnen", "Starten"),
    "French": ("Téléchargeur", "File d'attente", "Paramètres", "Diagnostic", "Collez les URL YouTube, une par ligne :",
               "➕ Ajouter à la file", "⚡ Téléchargement rapide", "📋 Coller", "▶ Tout démarrer", "Thème :", "Langue :",
               "Emplacement", "Annuler", "Réessayer", "Retirer", "Ouvrir le dossier", "Démarrer"),
    "Spanish": ("Descargador", "Cola", "Ajustes", "Diagnóstico", "Pegue URL de YouTube, una por línea:",
                "➕ Agregar a la cola", "⚡ Descarga rápida", "📋 Pegar", "▶ Iniciar todo", "Tema:", "Idioma:",
                "Ubicación", "Cancelar", "Reintentar", "Quitar", "Abrir carpeta", "Iniciar"),
    "Japanese": ("ダウンロード", "キュー", "設定", "診断", "YouTube URLを1行ずつ入力:",
                 "➕ キューに追加", "⚡ クイックダウンロード", "📋 貼り付け", "▶ すべて開始", "テーマ:", "言語:",
                 "保存場所", "キャンセル", "再試行", "削除", "フォルダを開く", "開始"),
    "Chinese": ("下载器", "下载队列", "设置", "诊断", "输入YouTube链接（每行一个）:",
                "➕ 添加到队列", "⚡ 快速下载", "📋 粘贴", "▶ 全部开始", "主题:", "语言:",
                "下载位置", "取消", "重试", "移除", "打开文件夹", "开始"),
    "Korean": ("다운로더", "다운로드 대기열", "설정", "진단", "YouTube URL 입력 (한 줄에 하나):",
               "➕ 대기열에 추가", "⚡ 빠른 다운로드", "📋 붙여넣기", "▶ 모두 시작", "테마:", "언어:",
               "저장 위치", "취소", "재시도", "제거", "폴더 열기", "시작"),
    "Russian": ("Загрузчик", "Очередь", "Настройки", "Диагностика", "Введите URL YouTube (по одному в строке):",
                "➕ В очередь", "⚡ Быстрая загрузка", "📋 Вставить", "▶ Начать все", "Тема:", "Язык:",
                "Папка загрузки", "Отмена", "Повторить", "Удалить", "Открыть папку", "Начать"),
    "Portuguese": ("Downloader", "Fila", "Configurações", "Diagnósticos", "Insira URLs do YouTube, uma por linha:",
                   "➕ Adicionar à fila", "⚡ Download rápido", "📋 Colar", "▶ Iniciar tudo", "Tema:", "Idioma:",
                   "Local de download", "Cancelar", "Tentar novamente", "Remover", "Abrir pasta", "Iniciar"),
    "Arabic": ("المُنزِّل", "قائمة التنزيل", "الإعدادات", "التشخيصات", "أدخل روابط YouTube، واحدًا في كل سطر:",
               "➕ إضافة إلى القائمة", "⚡ تنزيل سريع", "📋 لصق", "▶ بدء الكل", "السمة:", "اللغة:",
               "موقع التنزيل", "إلغاء", "إعادة المحاولة", "إزالة", "فتح المجلد", "بدء"),
}
LANGUAGES = {name: dict(zip(LANG_KEYS, vals)) for name, vals in _LANG_VALUES.items()}

PLACEHOLDER = "https://www.youtube.com/watch?v=...   (one link per line)"
MONO_FONT = "Consolas" if platform.system() == "Windows" else "DejaVu Sans Mono"
ACTIVE_STATES = ("queued", "downloading", "paused")


# ----------------------------------------------------------------------------
# Config and helpers
# ----------------------------------------------------------------------------
def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def find_ffmpeg(custom=""):
    if custom and os.path.isfile(custom):
        return custom
    base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    name = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
    for candidate in (os.path.join(base, "ffmpeg", name), os.path.join(base, name)):
        if os.path.isfile(candidate):
            return candidate
    return shutil.which("ffmpeg")


def ffmpeg_version(path):
    if not path:
        return ""
    try:
        out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=5)
        return out.stdout.split("\n")[0][:80]
    except (OSError, subprocess.SubprocessError):
        return "Unknown version"


def is_youtube(url):
    return "youtube.com" in url or "youtu.be" in url


def shorten(text, n):
    text = text or ""
    return text if len(text) <= n else text[: n - 1] + "…"


def fmt_speed(bps):
    if not bps:
        return ""
    for unit in ("B/s", "KB/s", "MB/s"):
        if bps < 1024:
            return f"{bps:.0f} {unit}"
        bps /= 1024
    return f"{bps:.1f} GB/s"


def fmt_eta(seconds):
    if seconds is None:
        return ""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def open_path(path):
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except OSError:
        pass


def check_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True, "Internet connection: OK"
    except OSError:
        return False, "Internet connection: FAILED"


def check_dns():
    try:
        socket.gethostbyname("www.youtube.com")
        return True, "DNS resolution: OK"
    except socket.gaierror:
        return False, "DNS resolution: FAILED"


def check_youtube():
    try:
        urllib.request.urlopen("https://www.youtube.com", timeout=5)
        return True, "YouTube access: OK"
    except Exception as e:
        return False, f"YouTube access: FAILED ({str(e)[:60]})"


# ----------------------------------------------------------------------------
# Download logic
# ----------------------------------------------------------------------------
def build_format(quality, fmt, can_merge):
    """Build a yt-dlp format selector that honours the chosen quality cap."""
    if fmt == "MP3":
        return "bestaudio/best"
    h = QUALITY_HEIGHT.get(quality)
    cap = f"[height<={h}]" if h else ""
    if can_merge:
        if fmt == "MP4":
            # Prefer MP4/M4A streams so the merged file is MP4 without re-encoding.
            return (f"bestvideo{cap}[ext=mp4]+bestaudio[ext=m4a]/"
                    f"bestvideo{cap}+bestaudio/best{cap}/best")
        return f"bestvideo{cap}+bestaudio/best{cap}/best"
    # Without merging, only single files that already contain video + audio are possible
    # (on YouTube these top out around 720p).
    return f"best{cap}[ext=mp4]/best{cap}/best"


class YTLogger:
    def __init__(self, app):
        self.app = app

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        self.app.add_log("WARN", msg)

    def error(self, msg):
        self.app.add_log("ERROR", msg)


def make_ydl_opts(cfg, ffmpeg_path, hook, logger):
    fmt = cfg["format"]
    can_merge = bool(ffmpeg_path) and cfg["merge"]
    opts = {
        "format": build_format(cfg["quality"], fmt, can_merge),
        "outtmpl": os.path.join(cfg["download_path"], "%(title)s [%(id)s].%(ext)s"),
        "noplaylist": not cfg["playlist"],
        "progress_hooks": [hook],
        "logger": logger,
        "quiet": True,
        "no_warnings": True,
        "retries": cfg["retries"],
        "fragment_retries": cfg["retries"],
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 4,
        "continuedl": True,
    }
    if cfg["speed_limit"] > 0:
        opts["ratelimit"] = int(cfg["speed_limit"] * 1024 * 1024)
    if ffmpeg_path:
        opts["ffmpeg_location"] = ffmpeg_path
    if fmt == "MP3":
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio",
                                   "preferredcodec": "mp3", "preferredquality": "320"}]
    elif can_merge:
        opts["merge_output_format"] = "mp4" if fmt == "MP4" else "mkv"
    return opts


class Task:
    _counter = 0

    def __init__(self, url, settings):
        Task._counter += 1
        self.id = Task._counter
        self.url = url
        self.settings = settings          # snapshot of quality/format/etc. at the moment of adding
        self.title = url
        self.status = "pending"           # pending, queued, downloading, paused, done, error, cancelled
        self.percent = 0.0
        self.speed = ""
        self.eta = ""
        self.message = ""
        self.outfile = None
        self.cancel = threading.Event()
        self.last_ui = 0.0


# ----------------------------------------------------------------------------
# UI widgets
# ----------------------------------------------------------------------------
class TaskCard(ctk.CTkFrame):
    STATUS_COLORS = {"done": "#4CAF50", "error": "#F44336", "cancelled": "gray", "paused": "#FFB300"}

    def __init__(self, master, app, task):
        super().__init__(master, corner_radius=12, fg_color=app.colors["card"])
        self.app = app
        self.task = task
        app.cards.append(self)
        self.grid_columnconfigure(0, weight=1)

        self.title_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
        self.title_lbl.grid(row=0, column=0, sticky="ew", padx=18, pady=(12, 2))
        self.status_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.status_lbl.grid(row=0, column=1, sticky="e", padx=18, pady=(12, 2))
        self.bar = ctk.CTkProgressBar(self, height=10, corner_radius=5, progress_color=app.colors["main"])
        self.bar.set(0)
        self.bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=4)
        self.info_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
        self.info_lbl.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        self.btns = ctk.CTkFrame(self, fg_color="transparent")
        self.btns.grid(row=2, column=1, sticky="e", padx=18, pady=(0, 12))
        self.render()

    def render(self):
        t, c = self.task, self.app.colors
        self.title_lbl.configure(text=shorten(t.title, 80))
        self.status_lbl.configure(text=t.status.upper(),
                                  text_color=self.STATUS_COLORS.get(t.status, c["accent"]))
        self.bar.set(min(t.percent, 100) / 100)

        if t.status in ("downloading", "paused"):
            info = f"{t.percent:.1f}%   ·   {t.speed or '—'}   ·   ETA {t.eta or '—'}"
        elif t.status in ("error", "cancelled"):
            info = t.message
        elif t.status == "done":
            info = os.path.basename(t.outfile) if t.outfile else "Completed"
        else:
            info = t.url
        self.info_lbl.configure(text=shorten(info, 110))

        for w in self.btns.winfo_children():
            w.destroy()
        actions = []
        if t.status == "pending":
            actions.append(("start", self.app.start_task))
        if t.status in ACTIVE_STATES:
            actions.append(("cancel", self.app.cancel_task))
        if t.status in ("error", "cancelled"):
            actions.append(("retry", self.app.start_task))
        if t.status == "done":
            actions.append(("open_folder", self.app.open_folder))
        actions.append(("remove", self.app.remove_task))
        for i, (key, fn) in enumerate(actions):
            ctk.CTkButton(self.btns, text=self.app.tr(key), width=100, height=28, corner_radius=8,
                          fg_color=c["main"], hover_color=c["hover"],
                          command=lambda fn=fn: fn(t)).grid(row=0, column=i, padx=3)


class VanquishDownloaderPro(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.colors = THEMES.get(self.cfg["theme"], THEMES["Midnight Blue"])
        self.lang = self.cfg["language"] if self.cfg["language"] in LANGUAGES else "English"

        self.title("Vanquish Pro Video Downloader")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        ctk.set_appearance_mode("Dark")

        self.ffmpeg_path = find_ffmpeg(self.cfg.get("ffmpeg_path", ""))
        self.tasks = []
        self.cards_by_task = {}
        self.cards = []
        self.accent_buttons = []
        self.accent_menus = []
        self.i18n = []
        self.nav_buttons = {}
        self.logs = []
        self.placeholder_on = False
        self.current_view = None
        self.ui_queue = queue.Queue()
        self.running = threading.Event()
        self.running.set()
        self.executor = ThreadPoolExecutor(max_workers=self.cfg["concurrent"])
        self.ydl_logger = YTLogger(self)

        self.format_var = tk.StringVar(value=self.cfg["format"])
        self.quality_var = tk.StringVar(value=self.cfg["quality"])
        self.merge_var = tk.BooleanVar(value=self.cfg["merge"])
        self.playlist_var = tk.BooleanVar(value=self.cfg["playlist"])
        self.path_var = tk.StringVar(value=self.cfg["download_path"])
        self.concurrent_var = tk.StringVar(value=str(self.cfg["concurrent"]))
        self.theme_var = tk.StringVar(value=self.cfg["theme"])
        self.language_var = tk.StringVar(value=self.lang)
        self.ffmpeg_var = tk.StringVar(value=self.cfg.get("ffmpeg_path", ""))

        self._build_ui()
        self.apply_colors()
        self.apply_language()
        self._refresh_ffmpeg_labels()
        self._update_counts()

        self.bind("<Control-Return>", lambda e: self._add_to_queue())
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._poll_ui)
        self.select_view("download")
        self.add_log("INFO", f"yt-dlp {YTDLP_VERSION} · FFmpeg: {self.ffmpeg_path or 'not found'}")

    # ---------------- layout ----------------
    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        ctk.CTkLabel(self.sidebar, text="⚡ VANQUISH", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=(30, 0))
        ctk.CTkLabel(self.sidebar, text="PRO DOWNLOADER", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(0, 25))

        for view, key, icon in [("download", "downloader", "📥"), ("queue", "queue", "📋"),
                                ("settings", "settings", "⚙️"), ("diagnostics", "diagnostics", "🔍")]:
            btn = ctk.CTkButton(self.sidebar, text=f"{icon}  {self.tr(key)}", height=45, anchor="w",
                                font=ctk.CTkFont(size=14), corner_radius=10,
                                command=lambda v=view: self.select_view(v))
            btn.pack(fill="x", padx=15, pady=5)
            self._register(btn, key, prefix=f"{icon}  ")
            self.nav_buttons[view] = btn

        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=15, pady=20)
        self.ffmpeg_label = ctk.CTkLabel(bottom, text="", font=ctk.CTkFont(size=11))
        self.ffmpeg_label.pack(pady=4)
        ctk.CTkLabel(bottom, text="Version 3.0 Pro", font=ctk.CTkFont(size=11), text_color="gray").pack(pady=4)

        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(0, weight=1)

        self.views = {
            "download": self._build_download_view(),
            "queue": self._build_queue_view(),
            "settings": self._build_settings_view(),
            "diagnostics": self._build_diagnostics_view(),
        }
        for frame in self.views.values():
            frame.grid(row=0, column=0, sticky="nsew")

        self.status_label = ctk.CTkLabel(self.main, text="Ready", font=ctk.CTkFont(size=12),
                                         text_color="gray", anchor="w")
        self.status_label.grid(row=1, column=0, sticky="ew", padx=40, pady=(0, 12))

    def _build_download_view(self):
        f = ctk.CTkFrame(self.main, fg_color="transparent")
        head = ctk.CTkFrame(f, fg_color="transparent")
        head.pack(fill="x", padx=40, pady=(30, 5))
        ctk.CTkLabel(head, text="Download Videos", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(head, text="Paste YouTube links, choose a quality, and download.",
                     font=ctk.CTkFont(size=14), text_color="gray").pack(anchor="w", pady=(4, 0))

        card = self._card(f)
        card.pack(fill="x", padx=40, pady=15)
        lbl = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(anchor="w", padx=25, pady=(20, 8))
        self._register(lbl, "url_label")

        self.url_box = ctk.CTkTextbox(card, height=110, corner_radius=10, font=ctk.CTkFont(size=13))
        self.url_box.pack(fill="x", padx=25)
        self.url_box.bind("<FocusIn>", self._on_url_focus)
        self.url_box.bind("<FocusOut>", self._on_url_blur)
        self._show_placeholder()

        opts = ctk.CTkFrame(card, fg_color="transparent")
        opts.pack(fill="x", padx=25, pady=(12, 8))
        self._labeled_menu(opts, "Format", ["MP4", "MKV", "MP3"], self.format_var)
        self._labeled_menu(opts, "Quality", list(QUALITY_HEIGHT), self.quality_var)
        box = ctk.CTkFrame(opts, fg_color="transparent")
        box.pack(side="left", padx=(0, 30))
        ctk.CTkLabel(box, text="Options", font=ctk.CTkFont(size=12)).pack(anchor="w")
        ctk.CTkCheckBox(box, text="Merge audio + video", variable=self.merge_var).pack(anchor="w", pady=(5, 0))
        ctk.CTkCheckBox(box, text="Download full playlists", variable=self.playlist_var).pack(anchor="w", pady=(5, 0))

        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=40, pady=5)
        self._btn(row, self._paste_clipboard, key="paste", height=48, width=170).pack(side="left", padx=(0, 10))
        self._btn(row, self._add_to_queue, key="add_queue", height=48, width=200).pack(side="left", padx=(0, 10))
        self._btn(row, self._quick_download, key="quick", height=48, width=220).pack(side="left")

        stats = ctk.CTkFrame(f, fg_color="transparent")
        stats.pack(fill="x", padx=40, pady=20)
        self.stat_active = self._stat_card(stats, "Active")
        self.stat_queued = self._stat_card(stats, "Waiting")
        self.stat_done = self._stat_card(stats, "Completed")
        return f

    def _build_queue_view(self):
        f = ctk.CTkFrame(self.main, fg_color="transparent")
        head = ctk.CTkFrame(f, fg_color="transparent")
        head.pack(fill="x", padx=40, pady=(30, 10))
        ctk.CTkLabel(head, text="Download Queue", font=ctk.CTkFont(size=28, weight="bold")).pack(side="left")
        self.count_label = ctk.CTkLabel(head, text="", font=ctk.CTkFont(size=14), text_color="gray")
        self.count_label.pack(side="left", padx=15)

        bar = ctk.CTkFrame(f, fg_color="transparent")
        bar.pack(fill="x", padx=40, pady=(0, 10))
        self._btn(bar, self._start_all, key="start_all", height=40, width=130).pack(side="left", padx=(0, 8))
        self.pause_btn = self._btn(bar, self._toggle_pause, text="⏸ Pause All", height=40, width=130)
        self.pause_btn.pack(side="left", padx=(0, 8))
        self._btn(bar, self._retry_failed, text="↻ Retry Failed", height=40, width=140).pack(side="left", padx=(0, 8))
        self._btn(bar, self._clear_finished, text="Clear Finished", height=40, width=140).pack(side="left", padx=(0, 8))
        self._btn(bar, self._clear_all, text="🗑 Clear All", height=40, width=120).pack(side="left")

        self.queue_scroll = ctk.CTkScrollableFrame(f, corner_radius=15, fg_color="transparent")
        self.queue_scroll.pack(fill="both", expand=True, padx=40, pady=(0, 20))
        self.empty_label = ctk.CTkLabel(self.queue_scroll, text="Your queue is empty. Add links on the Downloader page.",
                                        text_color="gray")
        self.empty_label.pack(pady=40)
        return f

    def _build_settings_view(self):
        f = ctk.CTkFrame(self.main, fg_color="transparent")
        ctk.CTkLabel(f, text="Settings", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w", padx=40, pady=(30, 10))
        scroll = ctk.CTkScrollableFrame(f, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=40, pady=(0, 20))

        # Download location
        c = self._card(scroll)
        c.pack(fill="x", pady=8)
        self._section_title(c, "📁 Download Location", "location")
        r = ctk.CTkFrame(c, fg_color="transparent")
        r.pack(fill="x", padx=25, pady=(0, 20))
        ctk.CTkEntry(r, height=40, width=420, textvariable=self.path_var).pack(side="left", padx=(0, 10))
        self._btn(r, self._browse_location, text="Browse", height=40, width=110).pack(side="left", padx=(0, 10))
        self._btn(r, lambda: open_path(self.path_var.get()), text="Open folder", height=40, width=130).pack(side="left")

        # Performance
        c = self._card(scroll)
        c.pack(fill="x", pady=8)
        self._section_title(c, "⚡ Performance")
        r = ctk.CTkFrame(c, fg_color="transparent")
        r.pack(fill="x", padx=25, pady=4)
        ctk.CTkLabel(r, text="Max concurrent downloads:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 15))
        self._menu(r, ["1", "2", "3", "4", "5"], self.concurrent_var, self._update_concurrent, width=100).pack(side="left")
        r = ctk.CTkFrame(c, fg_color="transparent")
        r.pack(fill="x", padx=25, pady=4)
        ctk.CTkLabel(r, text="Speed limit (MB/s, 0 = unlimited):", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 15))
        self.speed_entry = ctk.CTkEntry(r, width=100)
        self.speed_entry.insert(0, str(self.cfg["speed_limit"]))
        self.speed_entry.pack(side="left")
        self.speed_entry.bind("<FocusOut>", self._save_perf)
        r = ctk.CTkFrame(c, fg_color="transparent")
        r.pack(fill="x", padx=25, pady=(4, 20))
        ctk.CTkLabel(r, text="Retries on network error:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 15))
        self.retries_entry = ctk.CTkEntry(r, width=100)
        self.retries_entry.insert(0, str(self.cfg["retries"]))
        self.retries_entry.pack(side="left")
        self.retries_entry.bind("<FocusOut>", self._save_perf)

        # Appearance
        c = self._card(scroll)
        c.pack(fill="x", pady=8)
        self._section_title(c, "🎨 Appearance")
        r = ctk.CTkFrame(c, fg_color="transparent")
        r.pack(fill="x", padx=25, pady=4)
        lbl = ctk.CTkLabel(r, text="", font=ctk.CTkFont(size=13))
        lbl.pack(side="left", padx=(0, 15))
        self._register(lbl, "theme")
        self._menu(r, list(THEMES), self.theme_var, self._change_theme).pack(side="left")
        r = ctk.CTkFrame(c, fg_color="transparent")
        r.pack(fill="x", padx=25, pady=(4, 20))
        lbl = ctk.CTkLabel(r, text="", font=ctk.CTkFont(size=13))
        lbl.pack(side="left", padx=(0, 15))
        self._register(lbl, "language")
        self._menu(r, list(LANGUAGES), self.language_var, self._change_language).pack(side="left")

        # FFmpeg
        c = self._card(scroll)
        c.pack(fill="x", pady=8)
        self._section_title(c, "🎬 FFmpeg")
        self.ffmpeg_status = ctk.CTkLabel(c, text="", font=ctk.CTkFont(size=13))
        self.ffmpeg_status.pack(anchor="w", padx=25)
        self.ffmpeg_version = ctk.CTkLabel(c, text="", font=ctk.CTkFont(size=11), text_color="gray")
        self.ffmpeg_version.pack(anchor="w", padx=25, pady=(4, 10))
        r = ctk.CTkFrame(c, fg_color="transparent")
        r.pack(fill="x", padx=25, pady=(0, 20))
        ctk.CTkEntry(r, height=40, width=420, textvariable=self.ffmpeg_var,
                     placeholder_text="Custom ffmpeg path (leave empty for auto-detect)").pack(side="left", padx=(0, 10))
        self._btn(r, self._browse_ffmpeg, text="Browse", height=40, width=110).pack(side="left", padx=(0, 10))
        self._btn(r, self._apply_ffmpeg, text="Apply", height=40, width=110).pack(side="left")
        return f

    def _build_diagnostics_view(self):
        f = ctk.CTkFrame(self.main, fg_color="transparent")
        head = ctk.CTkFrame(f, fg_color="transparent")
        head.pack(fill="x", padx=40, pady=(30, 10))
        ctk.CTkLabel(head, text="Network Diagnostics", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(head, text="Connectivity checks and a live activity log.",
                     font=ctk.CTkFont(size=14), text_color="gray").pack(anchor="w", pady=(4, 0))
        bar = ctk.CTkFrame(f, fg_color="transparent")
        bar.pack(fill="x", padx=40, pady=10)
        self._btn(bar, self.run_diagnostics, text="🔍 Run Full Diagnostics", height=45, width=230).pack(side="left", padx=(0, 10))
        self._btn(bar, self.clear_logs, text="🗑 Clear Logs", height=45, width=150).pack(side="left")
        card = self._card(f)
        card.pack(fill="both", expand=True, padx=40, pady=(0, 20))
        self.log_box = ctk.CTkTextbox(card, corner_radius=10, font=ctk.CTkFont(family=MONO_FONT, size=12))
        self.log_box.pack(fill="both", expand=True, padx=20, pady=20)
        self.log_box.configure(state="disabled")
        return f

    # ---------------- widget helpers ----------------
    def tr(self, key):
        return LANGUAGES.get(self.lang, {}).get(key) or LANGUAGES["English"].get(key, key)

    def _register(self, widget, key, prefix=""):
        self.i18n.append((widget, key, prefix))

    def _card(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=15, fg_color=self.colors["card"])
        self.cards.append(card)
        return card

    def _stat_card(self, parent, title):
        card = self._card(parent)
        card.pack(side="left", padx=(0, 15), ipadx=25, ipady=5)
        value = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=26, weight="bold"))
        value.pack(padx=20, pady=(10, 0))
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color="gray").pack(padx=20, pady=(0, 10))
        return value

    def _section_title(self, parent, text, key=None):
        lbl = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=16, weight="bold"))
        lbl.pack(anchor="w", padx=25, pady=(20, 10))
        if key:
            self._register(lbl, key, prefix=text.split(" ")[0] + " ")
            lbl.configure(text=text)

    def _btn(self, parent, command, text="", key=None, **kw):
        text = text or (self.tr(key) if key else "")
        kw.setdefault("corner_radius", 12)
        btn = ctk.CTkButton(parent, text=text, command=command,
                            font=ctk.CTkFont(size=14, weight="bold"), **kw)
        if key:
            self._register(btn, key)
        self.accent_buttons.append(btn)
        return btn

    def _menu(self, parent, values, var, command=None, width=180):
        menu = ctk.CTkOptionMenu(parent, values=values, variable=var, command=command, width=width)
        self.accent_menus.append(menu)
        return menu

    def _labeled_menu(self, parent, label, values, var):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(side="left", padx=(0, 30))
        ctk.CTkLabel(box, text=label, font=ctk.CTkFont(size=12)).pack(anchor="w")
        self._menu(box, values, var, width=130).pack(pady=(5, 0))

    def apply_colors(self):
        c = self.colors
        self.configure(fg_color=c["bg"])
        self.sidebar.configure(fg_color=c["side"])
        self.main.configure(fg_color=c["bg"])
        for b in self.accent_buttons:
            b.configure(fg_color=c["main"], hover_color=c["hover"])
        for m in self.accent_menus:
            m.configure(fg_color=c["main"], button_color=c["main"], button_hover_color=c["hover"])
        for card in self.cards:
            card.configure(fg_color=c["card"])
            if isinstance(card, TaskCard):
                card.bar.configure(progress_color=c["main"])
        self._update_nav()

    def apply_language(self):
        for widget, key, prefix in self.i18n:
            try:
                widget.configure(text=prefix + self.tr(key))
            except tk.TclError:
                pass
        if self.placeholder_on:
            self._show_placeholder()

    def _update_nav(self):
        c = self.colors
        for view, btn in self.nav_buttons.items():
            active = view == self.current_view
            btn.configure(fg_color=c["main"] if active else "transparent",
                          hover_color=c["hover"] if active else c["card"])

    def select_view(self, name):
        self.current_view = name
        self.views[name].tkraise()
        self._update_nav()

    def set_status(self, text):
        self.status_label.configure(text=text)

    # ---------------- thread-safe UI bridge ----------------
    def ui(self, fn, *args):
        """Schedule fn(*args) on the Tk main thread. Safe to call from any thread."""
        self.ui_queue.put((fn, args))

    def _poll_ui(self):
        try:
            while True:
                fn, args = self.ui_queue.get_nowait()
                try:
                    fn(*args)
                except Exception as e:
                    print("UI update failed:", e)
        except queue.Empty:
            pass
        self.after(50, self._poll_ui)

    # ---------------- URL input ----------------
    def _show_placeholder(self):
        self.url_box.delete("1.0", "end")
        self.url_box.insert("1.0", PLACEHOLDER)
        self.url_box.configure(text_color="gray")
        self.placeholder_on = True

    def _on_url_focus(self, _event=None):
        if self.placeholder_on:
            self.url_box.delete("1.0", "end")
            self.url_box.configure(text_color=("gray10", "gray90"))
            self.placeholder_on = False

    def _on_url_blur(self, _event=None):
        if not self.placeholder_on and not self.url_box.get("1.0", "end").strip():
            self._show_placeholder()

    def _read_urls(self):
        if self.placeholder_on:
            return []
        return [u for u in self.url_box.get("1.0", "end").split() if u]

    def _clear_url_box(self):
        self.url_box.delete("1.0", "end")
        self._show_placeholder()

    def _paste_clipboard(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            self.set_status("Clipboard is empty")
            return
        self._on_url_focus()
        self.url_box.insert("end", text.strip() + "\n")

    def _add_to_queue(self):
        added = self._enqueue(self._read_urls())
        if added:
            self._clear_url_box()
            self.select_view("queue")

    def _quick_download(self):
        added = self._enqueue(self._read_urls())
        for task in added:
            self.start_task(task)
        if added:
            self._clear_url_box()
            self.select_view("queue")

    # ---------------- settings sync ----------------
    def _current_settings(self):
        self.cfg["format"] = self.format_var.get()
        self.cfg["quality"] = self.quality_var.get()
        self.cfg["merge"] = bool(self.merge_var.get())
        self.cfg["playlist"] = bool(self.playlist_var.get())
        self.cfg["download_path"] = self.path_var.get().strip() or DEFAULT_CONFIG["download_path"]
        save_config(self.cfg)
        return dict(self.cfg)

    def _save_perf(self, _event=None):
        try:
            self.cfg["speed_limit"] = max(0.0, float(self.speed_entry.get().strip() or 0))
        except ValueError:
            pass
        try:
            self.cfg["retries"] = max(0, min(20, int(self.retries_entry.get().strip())))
        except ValueError:
            pass
        save_config(self.cfg)

    def _update_concurrent(self, value):
        n = int(value)
        self.cfg["concurrent"] = n
        save_config(self.cfg)
        old = self.executor
        self.executor = ThreadPoolExecutor(max_workers=n)
        old.shutdown(wait=False)

    def _change_theme(self, name):
        self.colors = THEMES[name]
        self.cfg["theme"] = name
        save_config(self.cfg)
        self.apply_colors()

    def _change_language(self, lang):
        self.lang = lang
        self.cfg["language"] = lang
        save_config(self.cfg)
        self.apply_language()

    def _browse_location(self):
        folder = filedialog.askdirectory(initialdir=self.path_var.get() or None)
        if folder:
            self.path_var.set(folder)
            self._current_settings()

    def _browse_ffmpeg(self):
        path = filedialog.askopenfilename(title="Select ffmpeg executable")
        if path:
            self.ffmpeg_var.set(path)
            self._apply_ffmpeg()

    def _apply_ffmpeg(self):
        path = self.ffmpeg_var.get().strip()
        self.ffmpeg_path = find_ffmpeg(path)
        self.cfg["ffmpeg_path"] = path
        save_config(self.cfg)
        self._refresh_ffmpeg_labels()
        self.set_status("FFmpeg found" if self.ffmpeg_path else "FFmpeg not found")

    def _refresh_ffmpeg_labels(self):
        ok = self.ffmpeg_path is not None
        color = "#4CAF50" if ok else "#F44336"
        self.ffmpeg_label.configure(text="FFmpeg: ✓ Ready" if ok else "FFmpeg: ✕ Not Found", text_color=color)
        self.ffmpeg_status.configure(
            text="✓ FFmpeg is available" if ok else
            "✕ FFmpeg not found: video is limited to ~720p and MP3 is unavailable",
            text_color=color)
        self.ffmpeg_version.configure(text=ffmpeg_version(self.ffmpeg_path))

    def _open_download_folder(self):
        open_path(self.cfg["download_path"])

    # ---------------- queue management ----------------
    def _enqueue(self, urls):
        if not urls:
            self.set_status("Paste at least one YouTube link first.")
            return []
        settings = self._current_settings()
        in_progress = {t.url for t in self.tasks if t.status in ("pending",) + ACTIVE_STATES}
        added, skipped, dupes = [], 0, 0
        for url in urls:
            if not is_youtube(url):
                skipped += 1
                continue
            if url in in_progress:
                dupes += 1
                continue
            in_progress.add(url)
            task = Task(url, settings)
            self.tasks.append(task)
            added.append(task)
            self._create_card(task)
            threading.Thread(target=self._fetch_title, args=(task,), daemon=True).start()

        self._update_counts()
        msg = f"Added {len(added)} item(s)"
        if skipped:
            msg += f" · {skipped} not a YouTube link"
        if dupes:
            msg += f" · {dupes} already in queue"
        if added and not self.ffmpeg_path:
            msg += " · FFmpeg missing: single-file formats only"
        self.set_status(msg)
        return added

    def _create_card(self, task):
        self.empty_label.pack_forget()
        card = TaskCard(self.queue_scroll, self, task)
        card.pack(fill="x", pady=6, padx=6)
        self.cards_by_task[task.id] = card

    def _refresh_card(self, task):
        card = self.cards_by_task.get(task.id)
        if card:
            card.render()

    def _fetch_title(self, task):
        try:
            opts = {"quiet": True, "no_warnings": True, "noplaylist": True,
                    "skip_download": True, "logger": self.ydl_logger}
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(task.url, download=False) or {}
            task.title = info.get("title") or task.title
        except Exception:
            pass
        self.ui(self._refresh_card, task)

    def start_task(self, task):
        if task.status not in ("pending", "error", "cancelled"):
            return
        task.cancel = threading.Event()
        task.percent, task.speed, task.eta, task.message = 0.0, "", "", ""
        task.status = "queued"
        self._refresh_card(task)
        self._update_counts()
        self.executor.submit(self._run_task, task)

    def _start_all(self):
        self.running.set()
        self.pause_btn.configure(text="⏸ Pause All")
        for task in list(self.tasks):
            if task.status == "pending":
                self.start_task(task)
        self.set_status("Downloads started")

    def _toggle_pause(self):
        if self.running.is_set():
            self.running.clear()
            self.pause_btn.configure(text="▶ Resume All")
            self.set_status("Paused: active downloads will hold until resumed")
        else:
            self.running.set()
            self.pause_btn.configure(text="⏸ Pause All")
            self.set_status("Resumed")

    def _retry_failed(self):
        for task in list(self.tasks):
            if task.status in ("error", "cancelled"):
                self.start_task(task)

    def cancel_task(self, task):
        if task.status in ACTIVE_STATES:
            task.cancel.set()
            if task.status == "queued":
                self._finish(task, "cancelled", "Cancelled")

    def remove_task(self, task):
        task.cancel.set()
        if task in self.tasks:
            self.tasks.remove(task)
        card = self.cards_by_task.pop(task.id, None)
        if card:
            if card in self.cards:
                self.cards.remove(card)
            card.destroy()
        self._update_counts()

    def _has_active(self):
        return any(t.status in ACTIVE_STATES for t in self.tasks)

    def _clear_finished(self):
        for task in list(self.tasks):
            if task.status in ("done", "error", "cancelled"):
                self.remove_task(task)

    def _clear_all(self):
        if self._has_active() and not messagebox.askyesno(
                "Clear queue", "Some downloads are still running. Cancel and remove everything?"):
            return
        for task in list(self.tasks):
            self.remove_task(task)

    def open_folder(self, task):
        if task.outfile and os.path.exists(task.outfile):
            folder = os.path.dirname(task.outfile)
        else:
            folder = self.cfg["download_path"]
        open_path(folder)

    def _finish(self, task, status, message=""):
        task.status = status
        task.message = message
        if status == "done":
            task.percent = 100.0
        task.speed, task.eta = "", ""
        self._refresh_card(task)
        self._update_counts()

    def _update_counts(self):
        active = sum(t.status in ACTIVE_STATES for t in self.tasks)
        waiting = sum(t.status == "pending" for t in self.tasks)
        done = sum(t.status == "done" for t in self.tasks)
        self.stat_active.configure(text=str(active))
        self.stat_queued.configure(text=str(waiting))
        self.stat_done.configure(text=str(done))
        n = len(self.tasks)
        self.count_label.configure(text=f"{n} item{'s' if n != 1 else ''}")
        if n:
            self.empty_label.pack_forget()
        else:
            self.empty_label.pack(pady=40)

    # ---------------- the actual download ----------------
    def _run_task(self, task):
        cfg = task.settings
        if task.cancel.is_set():
            self.ui(self._finish, task, "cancelled", "Cancelled")
            return
        if cfg["format"] == "MP3" and not self.ffmpeg_path:
            self.ui(self._finish, task, "error", "MP3 export needs FFmpeg")
            return

        task.status = "downloading"
        self.ui(self._refresh_card, task)

        def hook(d):
            if task.cancel.is_set():
                raise DownloadCancelled("cancelled by user")
            if not self.running.is_set():
                if task.status != "paused":
                    task.status = "paused"
                    self.ui(self._refresh_card, task)
                while not self.running.wait(0.3):
                    if task.cancel.is_set():
                        raise DownloadCancelled("cancelled by user")
                task.status = "downloading"
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done = d.get("downloaded_bytes") or 0
                if total:
                    task.percent = done * 100 / total
                task.speed = fmt_speed(d.get("speed"))
                task.eta = fmt_eta(d.get("eta"))
                now = time.monotonic()
                if now - task.last_ui >= 0.15:
                    task.last_ui = now
                    self.ui(self._refresh_card, task)
            elif status == "finished":
                task.percent, task.speed, task.eta = 100.0, "", ""
                self.ui(self._refresh_card, task)

        try:
            os.makedirs(cfg["download_path"], exist_ok=True)
            opts = make_ydl_opts(cfg, self.ffmpeg_path, hook, self.ydl_logger)
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(task.url, download=True) or {}
            task.title = info.get("title") or task.title
            reqs = info.get("requested_downloads") or []
            if reqs:
                task.outfile = reqs[0].get("filepath")
            self.ui(self._finish, task, "done", "")
            self.ui(self.add_log, "INFO", f"Completed ({cfg['quality']} {cfg['format']}): {task.title}")
        except DownloadCancelled:
            self.ui(self._finish, task, "cancelled", "Cancelled")
        except Exception as e:
            if task.cancel.is_set():
                self.ui(self._finish, task, "cancelled", "Cancelled")
            else:
                msg = str(e).replace("ERROR: ", "").split("\n")[0][:90]
                self.ui(self._finish, task, "error", msg)
                self.ui(self.add_log, "ERROR", f"{task.url}: {msg}")

    # ---------------- diagnostics ----------------
    def add_log(self, level, msg):
        line = f"[{datetime.now():%H:%M:%S}] [{level}] {msg}"
        self.logs.append(line)
        if len(self.logs) > 1000:
            del self.logs[:200]
        self.ui(self._append_log, line)

    def _append_log(self, line):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def clear_logs(self):
        self.logs.clear()
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def run_diagnostics(self):
        threading.Thread(target=self._diagnostics_worker, daemon=True).start()

    def _diagnostics_worker(self):
        self.add_log("INFO", "Starting network diagnostics...")
        for check in (check_internet, check_dns, check_youtube):
            ok, msg = check()
            self.add_log("INFO" if ok else "ERROR", msg)
        try:
            self.add_log("INFO", f"Hostname: {socket.gethostname()}  Local IP: {socket.gethostbyname(socket.gethostname())}")
        except OSError:
            self.add_log("WARN", "Local network info unavailable")
        self.add_log("INFO", f"yt-dlp version: {YTDLP_VERSION}")
        self.add_log("INFO", f"FFmpeg: {self.ffmpeg_path or 'not found'}")
        self.add_log("INFO", "Diagnostics complete")

    # ---------------- shutdown ----------------
    def _on_close(self):
        self.running.set()
        for task in self.tasks:
            task.cancel.set()
        save_config(self.cfg)
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()


if __name__ == "__main__":
    app = VanquishDownloaderPro()
    app.mainloop()