import os
import platform
import re
import queue
import socket
import threading
import time
import tkinter as tk
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog

import customtkinter as ctk
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadCancelled

import downloader_core as core
from downloader_core import JobState

GREEN = "#22c55e"
RED = "#ef4444"
YELLOW = "#eab308"
MUTED = "gray60"
# Separate video/audio streams are saved as "name.f137.mp4" before merging.
_SPLIT_RE = re.compile(r"\.f[\w-]+\.\w+(?:\.part)?$")
PLACEHOLDER = "Paste YouTube links here, one per line (videos, Shorts or playlists)"

THEMES = {
    "Midnight Blue": {"main": "#0ea5e9", "hover": "#0284c7", "bg": "#0f172a", "side": "#111c33", "card": "#1e293b", "accent": "#38bdf8"},
    "Emerald": {"main": "#10b981", "hover": "#059669", "bg": "#0f1f1a", "side": "#0f2a24", "card": "#1a3a36", "accent": "#34d399"},
    "Crimson": {"main": "#ef4444", "hover": "#dc2626", "bg": "#1a0f0f", "side": "#241414", "card": "#2a1a1a", "accent": "#f87171"},
    "Violet": {"main": "#8b5cf6", "hover": "#7c3aed", "bg": "#1a1625", "side": "#221b35", "card": "#2a1f42", "accent": "#a78bfa"},
    "Amber": {"main": "#f59e0b", "hover": "#d97706", "bg": "#1a1608", "side": "#231e0c", "card": "#2a2410", "accent": "#fbbf24"},
    "Rose": {"main": "#f43f5e", "hover": "#e11d48", "bg": "#1a0f14", "side": "#24141b", "card": "#2a1a22", "accent": "#fb7185"},
}

LANGUAGES = {
    "English": {
        "url": "YouTube links", "dl": "Add to Queue", "download": "Download", "downloads": "Downloads",
        "set": "Settings", "lang": "Language", "col": "Theme", "succ": "Complete", "err": "Failed",
        "work": "Processing...", "clear": "Clear Finished", "start": "Start All", "pause": "Pause All",
        "format": "Format", "quality": "Quality", "location": "Download Location", "browse": "Browse",
        "concurrent": "Concurrent downloads", "logs": "Diagnostics", "run_diag": "Run Diagnostics",
        "clear_logs": "Clear Logs", "ffmpeg": "Tools", "about": "About", "speed": "Limit speed (MB/s)",
    },
    "German": {
        "url": "YouTube-Links", "dl": "Zur Warteschlange", "download": "Herunterladen", "downloads": "Downloads",
        "set": "Einstellungen", "lang": "Sprache", "col": "Design", "succ": "Fertig", "err": "Fehlgeschlagen",
        "work": "Verarbeitung...", "clear": "Fertige entfernen", "start": "Alle starten", "pause": "Alle pausieren",
        "format": "Format", "quality": "Qualität", "location": "Speicherort", "browse": "Durchsuchen",
        "concurrent": "Gleichzeitige Downloads", "logs": "Diagnose", "run_diag": "Diagnose starten",
        "clear_logs": "Logs löschen", "ffmpeg": "Werkzeuge", "about": "Über", "speed": "Geschwindigkeit begrenzen (MB/s)",
    },
    "French": {
        "url": "Liens YouTube", "dl": "Ajouter", "download": "Télécharger", "downloads": "Téléchargements",
        "set": "Paramètres", "lang": "Langue", "col": "Thème", "succ": "Terminé", "err": "Échec",
        "work": "Traitement...", "clear": "Effacer terminés", "start": "Tout démarrer", "pause": "Tout suspendre",
        "format": "Format", "quality": "Qualité", "location": "Emplacement", "browse": "Parcourir",
        "concurrent": "Téléchargements simultanés", "logs": "Diagnostics", "run_diag": "Lancer diagnostic",
        "clear_logs": "Effacer logs", "ffmpeg": "Outils", "about": "À propos", "speed": "Limiter la vitesse (Mo/s)",
    },
    "Spanish": {
        "url": "Enlaces de YouTube", "dl": "Agregar", "download": "Descargar", "downloads": "Descargas",
        "set": "Ajustes", "lang": "Idioma", "col": "Tema", "succ": "Completado", "err": "Fallido",
        "work": "Procesando...", "clear": "Borrar terminados", "start": "Iniciar todo", "pause": "Pausar todo",
        "format": "Formato", "quality": "Calidad", "location": "Ubicación", "browse": "Explorar",
        "concurrent": "Descargas simultáneas", "logs": "Diagnósticos", "run_diag": "Ejecutar diagnóstico",
        "clear_logs": "Borrar logs", "ffmpeg": "Herramientas", "about": "Acerca de", "speed": "Limitar velocidad (MB/s)",
    },
    "Japanese": {
        "url": "YouTube リンク", "dl": "キューに追加", "download": "ダウンロード", "downloads": "ダウンロード",
        "set": "設定", "lang": "言語", "col": "テーマ", "succ": "完了", "err": "失敗",
        "work": "処理中...", "clear": "完了済みを消去", "start": "すべて開始", "pause": "すべて一時停止",
        "format": "形式", "quality": "画質", "location": "保存場所", "browse": "参照",
        "concurrent": "同時ダウンロード数", "logs": "診断", "run_diag": "診断実行",
        "clear_logs": "ログクリア", "ffmpeg": "ツール", "about": "情報", "speed": "速度制限 (MB/s)",
    },
    "Chinese": {
        "url": "YouTube 链接", "dl": "添加到队列", "download": "下载", "downloads": "下载",
        "set": "设置", "lang": "语言", "col": "主题", "succ": "完成", "err": "失败",
        "work": "处理中...", "clear": "清除已完成", "start": "全部开始", "pause": "全部暂停",
        "format": "格式", "quality": "画质", "location": "下载位置", "browse": "浏览",
        "concurrent": "并发下载数", "logs": "诊断", "run_diag": "运行诊断",
        "clear_logs": "清除日志", "ffmpeg": "工具", "about": "关于", "speed": "限速 (MB/s)",
    },
    "Korean": {
        "url": "YouTube 링크", "dl": "대기열에 추가", "download": "다운로드", "downloads": "다운로드",
        "set": "설정", "lang": "언어", "col": "테마", "succ": "완료", "err": "실패",
        "work": "처리 중...", "clear": "완료 항목 지우기", "start": "모두 시작", "pause": "모두 일시정지",
        "format": "형식", "quality": "화질", "location": "저장 위치", "browse": "찾아보기",
        "concurrent": "동시 다운로드", "logs": "진단", "run_diag": "진단 실행",
        "clear_logs": "로그 지우기", "ffmpeg": "도구", "about": "정보", "speed": "속도 제한 (MB/s)",
    },
    "Russian": {
        "url": "Ссылки YouTube", "dl": "В очередь", "download": "Скачать", "downloads": "Загрузки",
        "set": "Настройки", "lang": "Язык", "col": "Тема", "succ": "Готово", "err": "Ошибка",
        "work": "Обработка...", "clear": "Убрать готовые", "start": "Запустить все", "pause": "Пауза для всех",
        "format": "Формат", "quality": "Качество", "location": "Папка", "browse": "Обзор",
        "concurrent": "Одновременных загрузок", "logs": "Диагностика", "run_diag": "Запустить",
        "clear_logs": "Очистить логи", "ffmpeg": "Инструменты", "about": "О программе", "speed": "Ограничить скорость (МБ/с)",
    },
    "Portuguese": {
        "url": "Links do YouTube", "dl": "Adicionar", "download": "Baixar", "downloads": "Downloads",
        "set": "Configurações", "lang": "Idioma", "col": "Tema", "succ": "Concluído", "err": "Falhou",
        "work": "Processando...", "clear": "Limpar concluídos", "start": "Iniciar tudo", "pause": "Pausar tudo",
        "format": "Formato", "quality": "Qualidade", "location": "Local", "browse": "Procurar",
        "concurrent": "Downloads simultâneos", "logs": "Diagnósticos", "run_diag": "Executar diagnóstico",
        "clear_logs": "Limpar logs", "ffmpeg": "Ferramentas", "about": "Sobre", "speed": "Limitar velocidade (MB/s)",
    },
    "Arabic": {
        "url": "روابط YouTube", "dl": "إضافة", "download": "تنزيل", "downloads": "التنزيلات",
        "set": "الإعدادات", "lang": "اللغة", "col": "السمة", "succ": "اكتمل", "err": "فشل",
        "work": "جاري المعالجة...", "clear": "مسح المكتمل", "start": "بدء الكل", "pause": "إيقاف الكل",
        "format": "التنسيق", "quality": "الجودة", "location": "موقع التنزيل", "browse": "تصفح",
        "concurrent": "التنزيلات المتزامنة", "logs": "التشخيصات", "run_diag": "تشغيل التشخيص",
        "clear_logs": "مسح السجلات", "ffmpeg": "الأدوات", "about": "حول", "speed": "تحديد السرعة (MB/s)",
    },
}


class JobRow(ctk.CTkFrame):
    """One line in the download list."""

    def __init__(self, master, app, job):
        super().__init__(master, corner_radius=12)
        self.app = app
        self.job = job
        self.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self, text="", anchor="w", font=ctk.CTkFont(size=13, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=(16, 8), pady=(10, 0), sticky="ew")

        self.meta_label = ctk.CTkLabel(self, text="", anchor="w", font=ctk.CTkFont(size=11), text_color=MUTED)
        self.meta_label.grid(row=1, column=0, padx=(16, 8), sticky="ew")

        self.bar = ctk.CTkProgressBar(self, height=8, corner_radius=4)
        self.bar.set(0)
        self.bar.grid(row=2, column=0, padx=(16, 8), pady=(6, 4), sticky="ew")

        self.status_label = ctk.CTkLabel(self, text="", anchor="w", font=ctk.CTkFont(size=11))
        self.status_label.grid(row=3, column=0, padx=(16, 8), pady=(0, 10), sticky="ew")

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=0, column=1, rowspan=4, padx=(0, 12), pady=10, sticky="e")
        self.action_btn = ctk.CTkButton(btns, text="", width=80, height=30, corner_radius=8, command=self._action)
        self.action_btn.pack(side="left", padx=3)
        self.open_btn = ctk.CTkButton(btns, text="Open", width=60, height=30, corner_radius=8,
                                      command=lambda: core.open_in_file_manager(self.job.filepath or self.job.download_dir))
        self.remove_btn = ctk.CTkButton(btns, text="✕", width=30, height=30, corner_radius=8,
                                        fg_color="transparent", border_width=1, border_color="gray40",
                                        hover_color="gray25", command=lambda: self.app.remove_job(self.job))
        self.remove_btn.pack(side="left", padx=3)
        self.apply_theme(THEMES[app.settings.theme])
        self.refresh()

    def apply_theme(self, c):
        self.configure(fg_color=c["card"])
        self.bar.configure(progress_color=c["main"])
        for b in (self.action_btn, self.open_btn):
            b.configure(fg_color=c["main"], hover_color=c["hover"])

    def _action(self):
        s = self.job.state
        if s == JobState.RUNNING:
            self.app.pause_job(self.job)
        elif s in (JobState.HELD, JobState.PAUSED, JobState.ERROR):
            self.app.resume_job(self.job)

    def refresh(self):
        job = self.job
        title = job.display_title()
        self.title_label.configure(text=title if len(title) <= 80 else title[:77] + "...")

        parts = [job.output_format]
        if not core.is_audio_format(job.output_format):
            parts.append(job.quality)
        if job.max_height and not core.is_audio_format(job.output_format):
            parts.append(f"source up to {job.max_height}p")
        if job.duration:
            parts.append(core.format_duration(job.duration))
        self.meta_label.configure(text="  ·  ".join(parts))

        s = job.state
        labels = {JobState.RUNNING: "Pause", JobState.HELD: "Start", JobState.PAUSED: "Resume", JobState.ERROR: "Retry"}
        if s in labels:
            self.action_btn.configure(text=labels[s], state="normal")
            self.action_btn.pack(side="left", padx=3, before=self.remove_btn)
        else:
            self.action_btn.pack_forget()

        if s == JobState.DONE:
            self.open_btn.pack(side="left", padx=3, before=self.remove_btn)
        else:
            self.open_btn.pack_forget()

        t = self.app.t
        if s == JobState.FETCHING:
            self.set_status("Reading video info...", MUTED)
        elif s == JobState.HELD:
            self.set_status("In queue (press Start)", MUTED)
        elif s == JobState.QUEUED:
            self.set_status("Waiting for a free slot...", MUTED)
        elif s == JobState.PAUSED:
            self.set_status("Paused", YELLOW)
        elif s == JobState.ERROR:
            self.set_status(f"{t('err')}: {job.error or 'unknown error'}", RED)
        elif s == JobState.DONE:
            self.bar.set(1)
            info = []
            if job.result_height and not core.is_audio_format(job.output_format):
                info.append(f"{job.result_height}p")
                wanted = core.quality_height(job.quality)
                if wanted and job.result_height < wanted:
                    info.append("highest available")
            if job.filepath and os.path.exists(job.filepath):
                info.append(core.format_bytes(os.path.getsize(job.filepath)))
            self.set_status(f"✓ {t('succ')}" + (f"  ·  {'  ·  '.join(info)}" if info else ""), GREEN)

    def set_status(self, text, color=None):
        self.status_label.configure(text=text, text_color=color or ("gray10", "gray90"))


class VanquishDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.settings = core.Settings.load()
        if self.settings.theme not in THEMES:
            self.settings.theme = "Midnight Blue"
        if self.settings.language not in LANGUAGES:
            self.settings.language = "English"

        self.title(core.APP_NAME)
        self.geometry("1180x780")
        self.minsize(960, 640)
        icon = core.resource_path("app.ico") or core.resource_path("icon.ico")
        if icon and core.IS_WINDOWS:
            try:
                self.iconbitmap(icon)
            except tk.TclError:
                pass

        ctk.set_appearance_mode("Dark")

        self.ffmpeg_path = core.find_ffmpeg()
        self.js_runtimes = core.find_js_runtimes()

        self.jobs = []
        self.rows = {}
        self.ui_queue = queue.SimpleQueue()
        self.meta_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="meta")
        self.log_lines = []
        self.i18n = []
        self.themed_buttons = []
        self.themed_menus = []
        self.cards = []
        self.nav_buttons = {}
        self.current_view = None
        self.placeholder_active = False

        self._build_ui()
        self._apply_theme(self.settings.theme)
        self._apply_language(self.settings.language)
        self.show_view("downloads")
        self._drain_ui_queue()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.log("INFO", f"{core.APP_NAME} {core.APP_VERSION}, yt-dlp {core.ytdlp_version()}")
        self.log("INFO", f"FFmpeg: {self.ffmpeg_path or 'not found'}")
        self.log("INFO", "JavaScript runtime: " + (", ".join(self.js_runtimes) or "not found"))

    # ------------------------------------------------------------------ helpers

    def t(self, key):
        return LANGUAGES.get(self.settings.language, {}).get(key) or LANGUAGES["English"][key]

    def post(self, fn, *args):
        """Run fn on the Tk thread. Safe to call from any thread."""
        self.ui_queue.put((fn, args))

    def _drain_ui_queue(self):
        deadline = time.monotonic() + 0.03
        try:
            while time.monotonic() < deadline:
                fn, args = self.ui_queue.get_nowait()
                try:
                    fn(*args)
                except tk.TclError:
                    pass
        except queue.Empty:
            pass
        self.after(40, self._drain_ui_queue)

    def log(self, level, message):
        line = f"[{core.timestamp()}] [{level}] {message}"
        if threading.current_thread() is threading.main_thread():
            self._append_log(line)
        else:
            self.post(self._append_log, line)

    def _append_log(self, line):
        self.log_lines.append(line)
        if len(self.log_lines) > 2000:
            del self.log_lines[:500]
        tag = "error" if "[ERROR]" in line else "warn" if "[WARN]" in line else "info"
        tb = self.log_textbox._textbox
        tb.configure(state="normal")
        tb.insert("end", line + "\n", tag)
        tb.see("end")
        tb.configure(state="disabled")

    def _button(self, master, key=None, text="", **kw):
        kw.setdefault("height", 38)
        kw.setdefault("corner_radius", 10)
        btn = ctk.CTkButton(master, text=self.t(key) if key else text, **kw)
        self.themed_buttons.append(btn)
        if key:
            self.i18n.append((btn, key, None))
        return btn

    def _label(self, master, key, fmt=None, **kw):
        lbl = ctk.CTkLabel(master, text=(fmt or "{}").format(self.t(key)), **kw)
        self.i18n.append((lbl, key, fmt))
        return lbl

    def _card(self, master):
        card = ctk.CTkFrame(master, corner_radius=14)
        self.cards.append(card)
        return card

    def _menu(self, master, values, variable=None, command=None, width=150):
        m = ctk.CTkOptionMenu(master, values=values, variable=variable, command=command, width=width,
                              dynamic_resizing=False)
        self.themed_menus.append(m)
        return m

    # ------------------------------------------------------------------ layout

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo.pack(pady=(28, 24), padx=20, anchor="w")
        self.logo_label = ctk.CTkLabel(logo, text="VANQUISH", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.pack(anchor="w")
        ctk.CTkLabel(logo, text="VIDEO DOWNLOADER", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=MUTED).pack(anchor="w")

        nav = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav.pack(fill="x", padx=12)
        for name, key in (("downloads", "downloads"), ("settings", "set"), ("diagnostics", "logs")):
            btn = ctk.CTkButton(nav, text=self.t(key), height=42, anchor="w", corner_radius=10,
                                font=ctk.CTkFont(size=14), command=lambda n=name: self.show_view(n))
            btn.pack(fill="x", pady=3)
            self.nav_buttons[name] = btn
            self.i18n.append((btn, key, "  {}"))

        status = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        status.pack(side="bottom", fill="x", padx=20, pady=20)
        self._status_line(status, "FFmpeg", bool(self.ffmpeg_path))
        self._status_line(status, "JS runtime", bool(self.js_runtimes))
        self.active_label = ctk.CTkLabel(status, text="", font=ctk.CTkFont(size=11), text_color=MUTED, anchor="w")
        self.active_label.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(status, text=f"Version {core.APP_VERSION}", font=ctk.CTkFont(size=11),
                     text_color=MUTED, anchor="w").pack(fill="x")

        self.main = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main.grid(row=0, column=1, sticky="nsew")

        self.views = {
            "downloads": self._build_downloads_view(),
            "settings": self._build_settings_view(),
            "diagnostics": self._build_diagnostics_view(),
        }

    def _status_line(self, master, name, ok):
        ctk.CTkLabel(master, text=f"{'●'} {name}: {'ready' if ok else 'missing'}", anchor="w",
                     font=ctk.CTkFont(size=11), text_color=GREEN if ok else RED).pack(fill="x")

    def _header(self, master, key, subtitle):
        h = ctk.CTkFrame(master, fg_color="transparent")
        h.pack(fill="x", padx=32, pady=(28, 12))
        self._label(h, key, font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(h, text=subtitle, font=ctk.CTkFont(size=13), text_color=MUTED).pack(anchor="w", pady=(2, 0))
        return h

    def _build_downloads_view(self):
        view = ctk.CTkFrame(self.main, fg_color="transparent")
        self._header(view, "downloads", "Paste links, pick a quality, and go.")

        for msg in self._tool_warnings():
            warn = ctk.CTkFrame(view, corner_radius=10, fg_color="#3b2f0b")
            warn.pack(fill="x", padx=32, pady=(0, 8))
            ctk.CTkLabel(warn, text=msg, text_color="#fde68a", justify="left", anchor="w",
                         wraplength=820, font=ctk.CTkFont(size=12)).pack(fill="x", padx=14, pady=8)

        card = self._card(view)
        card.pack(fill="x", padx=32, pady=(4, 12))
        card.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 6))
        self._label(top, "url", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        self._button(top, text="Paste", width=70, height=28, command=self._paste).pack(side="right")

        self.url_box = ctk.CTkTextbox(card, height=96, corner_radius=10, wrap="none")
        self.url_box.grid(row=1, column=0, sticky="ew", padx=20)
        self._set_placeholder()
        self.url_box.bind("<FocusIn>", self._clear_placeholder)
        self.url_box.bind("<FocusOut>", lambda e: self._set_placeholder())
        self.url_box.bind("<Control-Return>", lambda e: (self._submit(start=True), "break")[1])

        opts = ctk.CTkFrame(card, fg_color="transparent")
        opts.grid(row=2, column=0, sticky="ew", padx=20, pady=(12, 16))

        self.format_var = ctk.StringVar(value=self.settings.output_format)
        self.quality_var = ctk.StringVar(value=self.settings.quality)
        for key, values, var, cmd in (
            ("format", core.FORMAT_CHOICES, self.format_var, self._on_format_change),
            ("quality", core.QUALITY_CHOICES, self.quality_var, self._on_quality_change),
        ):
            col = ctk.CTkFrame(opts, fg_color="transparent")
            col.pack(side="left", padx=(0, 16))
            self._label(col, key, font=ctk.CTkFont(size=12), text_color=MUTED).pack(anchor="w")
            menu = self._menu(col, values, variable=var, command=cmd, width=140)
            menu.pack(pady=(4, 0))
            if key == "quality":
                self.quality_menu = menu

        self.download_btn = self._button(opts, "download", width=150, height=40,
                                         font=ctk.CTkFont(size=14, weight="bold"),
                                         command=lambda: self._submit(start=True))
        self.download_btn.pack(side="right", pady=(18, 0))
        self.queue_btn = self._button(opts, "dl", width=150, height=40, command=lambda: self._submit(start=False))
        self.queue_btn.pack(side="right", padx=10, pady=(18, 0))
        self._on_format_change(self.format_var.get())

        self.input_hint = ctk.CTkLabel(card, text="Tip: Ctrl+Enter starts the download.", anchor="w",
                                       font=ctk.CTkFont(size=11), text_color=MUTED)
        self.input_hint.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 12))

        bar = ctk.CTkFrame(view, fg_color="transparent")
        bar.pack(fill="x", padx=32, pady=(4, 6))
        self.count_label = ctk.CTkLabel(bar, text="No downloads yet", font=ctk.CTkFont(size=13), text_color=MUTED)
        self.count_label.pack(side="left")
        self._button(bar, text="Open Folder", width=110, height=32,
                     command=lambda: core.open_in_file_manager(self._ensure_download_dir())).pack(side="right")
        self._button(bar, "clear", width=130, height=32, command=self.clear_finished).pack(side="right", padx=6)
        self._button(bar, "pause", width=110, height=32, command=self.pause_all).pack(side="right")
        self._button(bar, "start", width=110, height=32, command=self.start_all).pack(side="right", padx=6)

        self.list_frame = ctk.CTkScrollableFrame(view, corner_radius=0)
        self.list_frame.pack(fill="both", expand=True, padx=26, pady=(0, 20))
        self.empty_label = ctk.CTkLabel(self.list_frame, text="Your downloads will show up here.",
                                        text_color=MUTED, font=ctk.CTkFont(size=13))
        self.empty_label.pack(pady=40)
        return view

    def _tool_warnings(self):
        out = []
        if not self.ffmpeg_path:
            out.append("FFmpeg was not found. YouTube keeps HD video and audio in separate streams that need "
                       "FFmpeg to be joined, so without it downloads are limited to 360p and MP3/M4A will not work.")
        if not self.js_runtimes:
            out.append("No JavaScript runtime (Deno or Node.js) was found. YouTube now requires one to unlock "
                       "most formats; without it quality is often capped. Install Deno from deno.com and restart.")
        return out

    def _build_settings_view(self):
        view = ctk.CTkFrame(self.main, fg_color="transparent")
        self._header(view, "set", "Saved automatically.")
        scroll = self.settings_scroll = ctk.CTkScrollableFrame(view)
        scroll.pack(fill="both", expand=True, padx=26, pady=(0, 20))

        def section(key=None, text=None):
            card = self._card(scroll)
            card.pack(fill="x", pady=8, padx=6)
            if key:
                self._label(card, key, font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=20, pady=(16, 8))
            else:
                ctk.CTkLabel(card, text=text, font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=20, pady=(16, 8))
            body = ctk.CTkFrame(card, fg_color="transparent")
            body.pack(fill="x", padx=20, pady=(0, 16))
            return body

        def row(body, key=None, text=None):
            r = ctk.CTkFrame(body, fg_color="transparent")
            r.pack(fill="x", pady=4)
            if key:
                self._label(r, key, width=200, anchor="w", font=ctk.CTkFont(size=13)).pack(side="left")
            elif text:
                ctk.CTkLabel(r, text=text, width=200, anchor="w", font=ctk.CTkFont(size=13)).pack(side="left")
            return r

        body = section("location")
        r = row(body)
        self.path_entry = ctk.CTkEntry(r, height=36)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.path_entry.insert(0, self.settings.download_dir)
        self.path_entry.bind("<FocusOut>", lambda e: self._commit_path())
        self.path_entry.bind("<Return>", lambda e: self._commit_path())
        self._button(r, "browse", width=100, height=36, command=self._browse).pack(side="left")

        body = section(text="Appearance")
        r = row(body, "col")
        self.theme_menu = self._menu(r, list(THEMES), command=self._on_theme, width=180)
        self.theme_menu.set(self.settings.theme)
        self.theme_menu.pack(side="left")
        r = row(body, "lang")
        self.lang_menu = self._menu(r, list(LANGUAGES), command=self._on_language, width=180)
        self.lang_menu.set(self.settings.language)
        self.lang_menu.pack(side="left")

        body = section(text="Downloading")
        r = row(body, "concurrent")
        self.concurrent_menu = self._menu(r, [str(i) for i in range(1, 9)], command=self._on_concurrent, width=80)
        self.concurrent_menu.set(str(self.settings.max_concurrent))
        self.concurrent_menu.pack(side="left")

        r = row(body, "speed")
        self.limit_var = ctk.BooleanVar(value=self.settings.speed_limit_enabled)
        ctk.CTkSwitch(r, text="", variable=self.limit_var, width=46, command=self._commit_limit).pack(side="left")
        self.limit_entry = ctk.CTkEntry(r, width=80, height=32)
        self.limit_entry.insert(0, f"{self.settings.speed_limit_mb:g}")
        self.limit_entry.pack(side="left", padx=8)
        self.limit_entry.bind("<FocusOut>", lambda e: self._commit_limit())
        self.limit_entry.bind("<Return>", lambda e: self._commit_limit())

        r = row(body, text="Playlists")
        self.playlist_var = ctk.BooleanVar(value=self.settings.expand_playlists)
        ctk.CTkCheckBox(r, text="Add every video of a playlist link", variable=self.playlist_var,
                        command=lambda: self._set("expand_playlists", self.playlist_var.get())).pack(side="left")

        r = row(body, text="Metadata")
        self.meta_var = ctk.BooleanVar(value=self.settings.embed_metadata)
        ctk.CTkCheckBox(r, text="Embed title and chapters (plus cover art for audio)", variable=self.meta_var,
                        command=lambda: self._set("embed_metadata", self.meta_var.get())).pack(side="left")

        r = row(body, text="Browser cookies")
        self.cookie_menu = self._menu(r, core.COOKIE_BROWSERS, command=lambda v: self._set("cookies_browser", v), width=140)
        self.cookie_menu.set(self.settings.cookies_browser)
        self.cookie_menu.pack(side="left")
        ctk.CTkLabel(body, text="Only needed for age restricted videos or when YouTube asks you to sign in.",
                     font=ctk.CTkFont(size=11), text_color=MUTED, anchor="w").pack(fill="x", pady=(2, 0))

        body = section("ffmpeg")
        self.ffmpeg_info = ctk.CTkLabel(body, text=f"FFmpeg: {self.ffmpeg_path or 'not found'}", anchor="w",
                                        justify="left", font=ctk.CTkFont(size=12))
        self.ffmpeg_info.pack(fill="x")
        js = ", ".join(f"{k} ({v['path']})" for k, v in self.js_runtimes.items()) or "not found"
        ctk.CTkLabel(body, text=f"JavaScript runtime: {js}", anchor="w", justify="left",
                     font=ctk.CTkFont(size=12)).pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(body, text=f"yt-dlp: {core.ytdlp_version()}", anchor="w",
                     font=ctk.CTkFont(size=12)).pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(body, text=f"Settings file: {core.Settings.path()}", anchor="w", text_color=MUTED,
                     font=ctk.CTkFont(size=11)).pack(fill="x", pady=(4, 0))
        if self.ffmpeg_path:
            threading.Thread(target=self._load_ffmpeg_version, daemon=True).start()
        return view

    def _build_diagnostics_view(self):
        view = ctk.CTkFrame(self.main, fg_color="transparent")
        self._header(view, "logs", "Connection checks and the app log.")
        controls = ctk.CTkFrame(view, fg_color="transparent")
        controls.pack(fill="x", padx=32, pady=(0, 12))
        self.diag_btn = self._button(controls, "run_diag", width=160, command=self._run_diagnostics)
        self.diag_btn.pack(side="left")
        self._button(controls, "clear_logs", width=120, command=self._clear_logs).pack(side="left", padx=8)
        self._button(controls, text="Copy Log", width=110, command=self._copy_log).pack(side="left")

        card = self._card(view)
        card.pack(fill="both", expand=True, padx=32, pady=(0, 24))
        mono = "Consolas" if core.IS_WINDOWS else "Menlo" if platform.system() == "Darwin" else "DejaVu Sans Mono"
        self.log_textbox = ctk.CTkTextbox(card, corner_radius=10, font=ctk.CTkFont(family=mono, size=12), wrap="word")
        self.log_textbox.pack(fill="both", expand=True, padx=14, pady=14)
        tb = self.log_textbox._textbox
        tb.tag_configure("error", foreground="#f87171")
        tb.tag_configure("warn", foreground="#facc15")
        tb.tag_configure("info", foreground="#86efac")
        tb.configure(state="disabled")
        return view

    # ------------------------------------------------------------------ view / theme / language

    def show_view(self, name):
        if self.current_view:
            self.views[self.current_view].pack_forget()
        self.views[name].pack(fill="both", expand=True)
        self.current_view = name
        self._style_nav()

    def _style_nav(self):
        c = THEMES[self.settings.theme]
        for name, btn in self.nav_buttons.items():
            if name == self.current_view:
                btn.configure(fg_color=c["main"], hover_color=c["hover"], text_color="white")
            else:
                btn.configure(fg_color="transparent", hover_color=c["card"], text_color=("gray10", "gray85"))

    def _apply_theme(self, name):
        c = THEMES[name]
        self.configure(fg_color=c["bg"])
        self.sidebar.configure(fg_color=c["side"])
        self.logo_label.configure(text_color=c["accent"])
        for b in self.themed_buttons:
            b.configure(fg_color=c["main"], hover_color=c["hover"])
        for m in self.themed_menus:
            m.configure(fg_color=c["bg"], button_color=c["main"], button_hover_color=c["hover"])
        for frame in (self.list_frame, self.settings_scroll):
            frame.configure(fg_color=c["bg"])
        self.url_box.configure(fg_color=c["bg"])
        self.log_textbox.configure(fg_color=c["bg"])
        for card in self.cards:
            card.configure(fg_color=c["card"])
        for row in self.rows.values():
            row.apply_theme(c)
        self._style_nav()

    def _on_theme(self, name):
        self._set("theme", name)
        self._apply_theme(name)

    def _apply_language(self, lang):
        for widget, key, fmt in self.i18n:
            try:
                widget.configure(text=(fmt or "{}").format(self.t(key)))
            except tk.TclError:
                pass
        for row in self.rows.values():
            row.refresh()

    def _on_language(self, lang):
        self._set("language", lang)
        self._apply_language(lang)

    # ------------------------------------------------------------------ settings

    def _set(self, key, value):
        setattr(self.settings, key, value)
        self.settings.validate()
        self.settings.save()

    def _on_format_change(self, value):
        self._set("output_format", value)
        self.quality_menu.configure(state="disabled" if core.is_audio_format(value) else "normal")

    def _on_quality_change(self, value):
        self._set("quality", value)

    def _on_concurrent(self, value):
        self._set("max_concurrent", int(value))
        self._pump()

    def _commit_limit(self):
        try:
            mb = float(self.limit_entry.get().replace(",", "."))
            if mb <= 0:
                raise ValueError
        except ValueError:
            mb = self.settings.speed_limit_mb
        self.settings.speed_limit_mb = mb
        self._set("speed_limit_enabled", self.limit_var.get())
        self.limit_entry.delete(0, "end")
        self.limit_entry.insert(0, f"{self.settings.speed_limit_mb:g}")

    def _commit_path(self):
        path = os.path.expanduser(self.path_entry.get().strip())
        if not path:
            path = core.default_download_dir()
        if path != self.settings.download_dir:
            self._set("download_dir", path)
            self.log("INFO", f"Download location: {path}")
        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, self.settings.download_dir)

    def _browse(self):
        start = self.settings.download_dir if os.path.isdir(self.settings.download_dir) else os.path.expanduser("~")
        folder = filedialog.askdirectory(initialdir=start)
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
            self._commit_path()

    def _ensure_download_dir(self):
        self._commit_path()
        try:
            os.makedirs(self.settings.download_dir, exist_ok=True)
        except OSError as e:
            self.log("ERROR", f"Can not create download folder: {e}")
        return self.settings.download_dir

    def _load_ffmpeg_version(self):
        version = core.ffmpeg_version(self.ffmpeg_path)
        self.post(lambda: self.ffmpeg_info.configure(text=f"FFmpeg: {self.ffmpeg_path}\n{version[:90]}"))

    # ------------------------------------------------------------------ url input

    def _set_placeholder(self):
        if not self.url_box.get("1.0", "end-1c").strip():
            self.url_box.delete("1.0", "end")
            self.url_box.insert("1.0", PLACEHOLDER)
            self.url_box.configure(text_color=MUTED)
            self.placeholder_active = True

    def _clear_placeholder(self, _event=None):
        if self.placeholder_active:
            self.url_box.delete("1.0", "end")
            self.url_box.configure(text_color=("gray10", "gray90"))
            self.placeholder_active = False

    def _paste(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return
        self._clear_placeholder()
        current = self.url_box.get("1.0", "end-1c")
        if current and not current.endswith("\n"):
            self.url_box.insert("end", "\n")
        self.url_box.insert("end", text.strip() + "\n")

    def _submit(self, start):
        text = "" if self.placeholder_active else self.url_box.get("1.0", "end-1c")
        urls, rejected = core.parse_urls(text)
        if not urls:
            self.input_hint.configure(text="No YouTube links found. Paste a youtube.com or youtu.be link.",
                                      text_color=RED)
            return
        fmt = self.format_var.get()
        if core.is_audio_format(fmt) and not self.ffmpeg_path:
            self.input_hint.configure(text=f"{fmt} needs FFmpeg. Install it or choose MP4/MKV.", text_color=RED)
            return
        download_dir = self._ensure_download_dir()
        for url in urls:
            self._add_job(url, fmt, self.quality_var.get(), download_dir, start)
        msg = f"Added {len(urls)} link{'s' if len(urls) != 1 else ''}."
        if rejected:
            msg += f" Skipped {len(rejected)} line{'s' if len(rejected) != 1 else ''} without a YouTube link."
        self.input_hint.configure(text=msg, text_color=YELLOW if rejected else MUTED)
        self.url_box.delete("1.0", "end")
        try:
            focused = self.focus_get()
        except (KeyError, tk.TclError):
            focused = None
        if focused is not self.url_box._textbox:
            self._set_placeholder()

    # ------------------------------------------------------------------ jobs

    def _add_job(self, url, fmt, quality, download_dir, start, title=""):
        job = core.DownloadJob(url=url, output_format=fmt, quality=quality, download_dir=download_dir,
                               title=title, start_when_ready=start)
        self.jobs.append(job)
        if self.empty_label.winfo_manager():
            self.empty_label.pack_forget()
        row = JobRow(self.list_frame, self, job)
        row.pack(fill="x", pady=4, padx=4)
        self.rows[job.id] = row
        self.meta_pool.submit(self._fetch_info, job)
        self._update_counts()
        return job

    def _refresh(self, job):
        row = self.rows.get(job.id)
        if row is not None and not job.removed:
            row.refresh()
        self._update_counts()

    def _fetch_info(self, job):
        """Runs on a worker. Reads title and formats, expands playlists."""
        opts = core.base_ydl_options(self.settings, self.ffmpeg_path, self.js_runtimes)
        opts["extract_flat"] = "in_playlist"
        opts["noplaylist"] = not self.settings.expand_playlists
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(job.url, download=False)
        except Exception as e:
            # Let the download try again; it reports the real error if any.
            self.log("WARN", f"Could not read info for {job.url}: {core.clean_error(e)}")
            self.post(self._info_ready, job, None)
            return
        self.post(self._info_ready, job, info)

    def _info_ready(self, job, info):
        if job.removed:
            return
        if info and info.get("_type") == "playlist":
            entries = [e for e in (info.get("entries") or []) if e]
            self.log("INFO", f"Playlist '{info.get('title')}' with {len(entries)} videos")
            for e in entries:
                url = core.playlist_entry_url(e)
                if url:
                    self._add_job(url, job.output_format, job.quality, job.download_dir,
                                  job.start_when_ready, title=e.get("title") or "")
            self.remove_job(job)
            return
        if info:
            summary = core.summarize_info(info)
            job.title = summary["title"] or job.title
            job.max_height = summary["max_height"]
            job.duration = summary["duration"]
            if info.get("formats"):
                job.info = info
                job.info_time = time.time()
        if job.state == JobState.FETCHING:
            job.state = JobState.QUEUED if job.start_when_ready else JobState.HELD
        self._refresh(job)
        self._pump()

    def _pump(self):
        """Start queued jobs while there are free slots."""
        running = sum(1 for j in self.jobs if j.state == JobState.RUNNING)
        for job in self.jobs:
            if running >= self.settings.max_concurrent:
                break
            if job.state == JobState.QUEUED:
                job.state = JobState.RUNNING
                job.cancel_event.clear()
                job.error = None
                running += 1
                self._refresh(job)
                threading.Thread(target=self._run_job, args=(job,), daemon=True, name=f"job-{job.id}").start()
        self._update_counts()

    def _run_job(self, job):
        row = self.rows.get(job.id)
        audio_only = core.is_audio_format(job.output_format)
        last = [0.0]

        def progress_hook(d):
            if job.cancel_event.is_set():
                raise DownloadCancelled()
            status = d.get("status")
            now = time.monotonic()
            if status == "downloading" and now - last[0] < 0.15:
                return
            last[0] = now
            part = d.get("info_dict") or {}
            is_audio_part = part.get("vcodec") == "none"
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes") or 0
            frac = min(done / total, 1.0) if total else 0.0
            if status == "finished":
                frac = 1.0
            split = bool(_SPLIT_RE.search(d.get("filename") or ""))
            if audio_only or not split:
                overall = frac
            elif is_audio_part:
                overall = 0.85 + 0.15 * frac
            else:
                overall = 0.85 * frac
            what = "audio" if is_audio_part and not audio_only else "video" if not audio_only else "audio"
            if status == "downloading":
                bits = [f"Downloading {what}  {frac * 100:4.1f}%"]
                if total:
                    bits.append(f"{core.format_bytes(done)} / {core.format_bytes(total)}")
                if d.get("speed"):
                    bits.append(core.format_speed(d["speed"]))
                if d.get("eta") is not None:
                    bits.append(f"ETA {core.format_eta(d['eta'])}")
                self.post(update_row, overall, "  ·  ".join(bits))
            elif status == "finished":
                self.post(update_row, overall, f"Finished {what}")

        def pp_hook(d):
            if d.get("status") == "started":
                names = {"Merger": "Merging video and audio...", "FFmpegExtractAudio": "Converting audio...",
                         "EmbedThumbnail": "Embedding thumbnail...", "FFmpegMetadata": "Writing metadata..."}
                text = names.get(d.get("postprocessor"))
                if text:
                    self.post(update_row, None, text)

        def update_row(value, text):
            if job.removed or job.state != JobState.RUNNING or row is None:
                return
            if value is not None:
                row.bar.set(value)
            row.set_status(text)

        opts = core.build_download_options(self.settings, job, self.ffmpeg_path, self.js_runtimes,
                                           progress_hook, pp_hook, log_sink=self.log)
        self.log("INFO", f"Starting: {job.display_title()} ({job.output_format}, {job.quality})")

        result, error = None, None
        try:
            os.makedirs(job.download_dir, exist_ok=True)
            with YoutubeDL(opts) as ydl:
                info = job.fresh_info()
                if info is not None:
                    try:
                        result = ydl.process_ie_result(dict(info), download=True)
                    except DownloadCancelled:
                        raise
                    except Exception as e:
                        if job.cancel_event.is_set():
                            raise DownloadCancelled() from e
                        self.log("WARN", f"Cached info failed ({core.clean_error(e)}), reading it again")
                        result = None
                if result is None:
                    result = ydl.extract_info(job.url, download=True)
        except DownloadCancelled:
            error = None
        except Exception as e:
            error = core.clean_error(e)
        self.post(self._job_finished, job, result, error)

    def _job_finished(self, job, result, error):
        if job.removed:
            self._pump()
            return
        if job.cancel_event.is_set():
            job.state = JobState.PAUSED
            self.log("INFO", f"Paused: {job.display_title()}")
        elif error:
            job.state = JobState.ERROR
            job.error = error if len(error) <= 160 else error[:157] + "..."
            self.log("ERROR", f"{job.display_title()}: {error}")
        else:
            job.state = JobState.DONE
            job.info = None  # free memory, stream URLs are no longer useful
            if result:
                job.title = result.get("title") or job.title
                job.result_height = result.get("height")
                downloads = result.get("requested_downloads") or []
                if downloads:
                    job.filepath = downloads[-1].get("filepath") or downloads[-1].get("filename")
            self.log("INFO", f"Done: {job.display_title()}" + (f" ({job.result_height}p)" if job.result_height else ""))
        self._refresh(job)
        self._pump()

    def pause_job(self, job):
        if job.state == JobState.RUNNING:
            job.cancel_event.set()
            row = self.rows.get(job.id)
            if row:
                row.set_status("Pausing...", YELLOW)
                row.action_btn.configure(state="disabled")

    def resume_job(self, job):
        if job.state in (JobState.HELD, JobState.PAUSED, JobState.ERROR):
            job.state = JobState.QUEUED
            self._refresh(job)
            self._pump()

    def remove_job(self, job):
        job.removed = True
        job.cancel_event.set()
        if job in self.jobs:
            self.jobs.remove(job)
        row = self.rows.pop(job.id, None)
        if row is not None:
            row.destroy()
        if not self.jobs and not self.empty_label.winfo_manager():
            self.empty_label.pack(pady=40)
        self._update_counts()

    def start_all(self):
        for job in self.jobs:
            if job.state in (JobState.HELD, JobState.PAUSED, JobState.ERROR):
                job.state = JobState.QUEUED
                self._refresh(job)
            elif job.state == JobState.FETCHING:
                job.start_when_ready = True
        self._pump()

    def pause_all(self):
        for job in self.jobs:
            if job.state == JobState.RUNNING:
                self.pause_job(job)
            elif job.state == JobState.QUEUED:
                job.state = JobState.HELD
                self._refresh(job)
            elif job.state == JobState.FETCHING:
                job.start_when_ready = False

    def clear_finished(self):
        for job in [j for j in self.jobs if j.state == JobState.DONE]:
            self.remove_job(job)

    def _update_counts(self):
        total = len(self.jobs)
        running = sum(1 for j in self.jobs if j.state == JobState.RUNNING)
        done = sum(1 for j in self.jobs if j.state == JobState.DONE)
        waiting = sum(1 for j in self.jobs if j.state in (JobState.QUEUED, JobState.FETCHING))
        if not total:
            self.count_label.configure(text="No downloads yet")
        else:
            self.count_label.configure(text=f"{total} total  ·  {running} active  ·  {waiting} waiting  ·  {done} done")
        self.active_label.configure(text=f"{running} active download{'s' if running != 1 else ''}" if running else "Idle")

    # ------------------------------------------------------------------ diagnostics

    def _run_diagnostics(self):
        self.diag_btn.configure(state="disabled")
        threading.Thread(target=self._diagnostics_worker, daemon=True).start()

    def _diagnostics_worker(self):
        self.log("INFO", "Running diagnostics...")
        try:
            with socket.create_connection(("1.1.1.1", 443), timeout=4):
                pass
            self.log("INFO", "Internet connection: OK")
        except OSError as e:
            self.log("ERROR", f"Internet connection: FAILED ({e})")
        try:
            addr = socket.gethostbyname("www.youtube.com")
            self.log("INFO", f"DNS resolution: OK ({addr})")
        except OSError as e:
            self.log("ERROR", f"DNS resolution: FAILED ({e})")
        try:
            start = time.monotonic()
            req = urllib.request.Request("https://www.youtube.com/generate_204", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                ms = (time.monotonic() - start) * 1000
                self.log("INFO", f"YouTube reachable: HTTP {resp.status} in {ms:.0f} ms")
        except Exception as e:
            self.log("ERROR", f"YouTube reachable: FAILED ({str(e)[:80]})")
        self.log("INFO" if self.ffmpeg_path else "ERROR", f"FFmpeg: {self.ffmpeg_path or 'not found'}")
        self.log("INFO" if self.js_runtimes else "WARN",
                 "JavaScript runtime: " + (", ".join(self.js_runtimes) or "not found (install Deno for full quality)"))
        self.log("INFO", f"yt-dlp version: {core.ytdlp_version()}")
        self.log("INFO", "Diagnostics complete")
        self.post(lambda: self.diag_btn.configure(state="normal"))

    def _clear_logs(self):
        self.log_lines.clear()
        tb = self.log_textbox._textbox
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        tb.configure(state="disabled")

    def _copy_log(self):
        self.clipboard_clear()
        self.clipboard_append("\n".join(self.log_lines))

    # ------------------------------------------------------------------ shutdown

    def _on_close(self):
        self._commit_path()
        self._commit_limit()
        for job in self.jobs:
            job.cancel_event.set()
        self.meta_pool.shutdown(wait=False, cancel_futures=True)
        self.destroy()


if __name__ == "__main__":
    if core.IS_WINDOWS:
        # Own taskbar entry, so Windows shows the app icon instead of Python's.
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Vanquish.Downloader")
        except Exception:
            pass
    app = VanquishDownloader()
    app.mainloop()
