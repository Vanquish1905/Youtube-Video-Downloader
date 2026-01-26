import tkinter as tk
import customtkinter as ctk
from yt_dlp import YoutubeDL
import threading
import os
import sys
import subprocess
import platform
import time
import queue
import socket
import urllib.request
import json
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

class AnimatedProgressBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(fg_color="transparent")
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ctk.CTkProgressBar(self, variable=self.progress_var, width=400, height=20, corner_radius=10)
        self.progress_bar.pack(pady=5)
        
        self.percentage_label = ctk.CTkLabel(self, text="0%", font=ctk.CTkFont(size=12, weight="bold"))
        self.percentage_label.pack(pady=2)
        
        self.speed_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11))
        self.speed_label.pack(pady=2)
        
        self.eta_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11))
        self.eta_label.pack(pady=2)
        
        self._animation_running = False
        self._pulse_direction = 1
        
    def set_progress(self, value, speed="", eta=""):
        self.progress_var.set(value / 100)
        self.percentage_label.configure(text=f"{value:.1f}%")
        if speed:
            self.speed_label.configure(text=f"Speed: {speed}")
        if eta:
            self.eta_label.configure(text=f"ETA: {eta}")
            
    def start_indeterminate(self):
        self._animation_running = True
        self._animate_pulse()
        
    def stop_indeterminate(self):
        self._animation_running = False
        
    def _animate_pulse(self):
        if not self._animation_running:
            return
        current = self.progress_var.get()
        current += 0.02 * self._pulse_direction
        if current >= 1.0:
            self._pulse_direction = -1
        elif current <= 0.0:
            self._pulse_direction = 1
        self.progress_var.set(current)
        self.after(30, self._animate_pulse)
        
    def reset(self):
        self.progress_var.set(0)
        self.percentage_label.configure(text="0%")
        self.speed_label.configure(text="")
        self.eta_label.configure(text="")


class DownloadItem(ctk.CTkFrame):
    def __init__(self, master, title, url, on_remove, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(corner_radius=10, height=80)
        self.pack_propagate(False)
        
        self.url = url
        self.title = title
        self.on_remove = on_remove
        self.status = "pending"
        
        self.grid_columnconfigure(1, weight=1)
        
        self.title_label = ctk.CTkLabel(self, text=title[:50] + "..." if len(title) > 50 else title, 
                                        font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        self.title_label.grid(row=0, column=0, columnspan=2, padx=15, pady=(10, 2), sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(self, width=300, height=12, corner_radius=6)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, padx=15, pady=5, sticky="w")
        
        self.status_label = ctk.CTkLabel(self, text="Pending", font=ctk.CTkFont(size=11))
        self.status_label.grid(row=1, column=1, padx=10, sticky="w")
        
        self.remove_btn = ctk.CTkButton(self, text="✕", width=30, height=30, corner_radius=15,
                                        command=lambda: self.on_remove(self))
        self.remove_btn.grid(row=0, column=2, rowspan=2, padx=10, pady=10)
        
    def update_progress(self, value, status=""):
        self.progress_bar.set(value / 100)
        if status:
            self.status_label.configure(text=status)
            
    def set_complete(self):
        self.status = "complete"
        self.progress_bar.set(1)
        self.status_label.configure(text="✓ Complete", text_color="#4CAF50")
        
    def set_error(self, msg="Error"):
        self.status = "error"
        self.status_label.configure(text=f"✕ {msg}", text_color="#F44336")


class NetworkDiagnostics:
    def __init__(self):
        self.logs = []
        
    def add_log(self, level, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}"
        self.logs.append(log_entry)
        return log_entry
        
    def check_internet(self):
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True, "Internet connection: OK"
        except OSError:
            return False, "Internet connection: FAILED"
            
    def check_youtube_access(self):
        try:
            urllib.request.urlopen("https://www.youtube.com", timeout=5)
            return True, "YouTube access: OK"
        except Exception as e:
            return False, f"YouTube access: FAILED ({str(e)[:50]})"
            
    def check_dns(self):
        try:
            socket.gethostbyname("www.youtube.com")
            return True, "DNS resolution: OK"
        except socket.gaierror:
            return False, "DNS resolution: FAILED"
            
    def get_network_info(self):
        info = []
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            info.append(f"Hostname: {hostname}")
            info.append(f"Local IP: {local_ip}")
        except:
            info.append("Network info: Unavailable")
        return info
        
    def run_full_diagnostics(self):
        results = []
        results.append(self.add_log("INFO", "Starting network diagnostics..."))
        
        for check_name, check_func in [
            ("Internet", self.check_internet),
            ("DNS", self.check_dns),
            ("YouTube", self.check_youtube_access)
        ]:
            success, msg = check_func()
            level = "INFO" if success else "ERROR"
            results.append(self.add_log(level, msg))
            
        for info in self.get_network_info():
            results.append(self.add_log("INFO", info))
            
        results.append(self.add_log("INFO", "Diagnostics complete"))
        return results
        
    def clear_logs(self):
        self.logs = []


class FFmpegManager:
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        
    def _find_ffmpeg(self):
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        local_ffmpeg = os.path.join(base_path, "ffmpeg", "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg")
        if os.path.exists(local_ffmpeg):
            return local_ffmpeg
            
        ffmpeg_in_path = shutil.which("ffmpeg")
        if ffmpeg_in_path:
            return ffmpeg_in_path
            
        return None
        
    def is_available(self):
        return self.ffmpeg_path is not None
        
    def get_path(self):
        return self.ffmpeg_path
        
    def get_version(self):
        if not self.is_available():
            return "Not found"
        try:
            result = subprocess.run([self.ffmpeg_path, "-version"], capture_output=True, text=True, timeout=10)
            first_line = result.stdout.split('\n')[0]
            return first_line
        except:
            return "Unknown version"


class VanquishDownloaderPro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Vanquish Pro Video Downloader")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        self.ffmpeg = FFmpegManager()
        self.diagnostics = NetworkDiagnostics()
        self.download_queue = queue.Queue()
        self.active_downloads = []
        self.max_concurrent = 3
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent)
        self.download_items = []
        
        self.default_download_path = os.path.join(os.path.expanduser("~"), "Downloads", "VanquishDownloads")
        os.makedirs(self.default_download_path, exist_ok=True)
        self.current_download_path = self.default_download_path
        
        self.themes = {
            "Midnight Blue": {"main": "#0ea5e9", "hover": "#0284c7", "bg": "#0f172a", "side": "#1e293b", "card": "#1e293b", "accent": "#38bdf8"},
            "Emerald": {"main": "#10b981", "hover": "#059669", "bg": "#0f1f1a", "side": "#134e4a", "card": "#1a3a36", "accent": "#34d399"},
            "Crimson": {"main": "#ef4444", "hover": "#dc2626", "bg": "#1a0f0f", "side": "#2d1f1f", "card": "#2a1a1a", "accent": "#f87171"},
            "Violet": {"main": "#8b5cf6", "hover": "#7c3aed", "bg": "#1a1625", "side": "#2e2447", "card": "#2a1f42", "accent": "#a78bfa"},
            "Amber": {"main": "#f59e0b", "hover": "#d97706", "bg": "#1a1608", "side": "#2d2812", "card": "#2a2410", "accent": "#fbbf24"},
            "Rose": {"main": "#f43f5e", "hover": "#e11d48", "bg": "#1a0f14", "side": "#2d1f27", "card": "#2a1a22", "accent": "#fb7185"}
        }

        self.languages = {
            "English": {
                "url": "Enter YouTube URL(s):", "dl": "Add to Queue", "set": "Settings", 
                "lang": "Language", "col": "Theme", "succ": "Download Complete!", 
                "err": "Download Failed", "work": "Processing...", "queue": "Download Queue",
                "clear": "Clear All", "start": "Start Downloads", "pause": "Pause",
                "format": "Output Format", "quality": "Video Quality", "location": "Download Location",
                "browse": "Browse", "concurrent": "Concurrent Downloads", "logs": "Diagnostics",
                "run_diag": "Run Diagnostics", "clear_logs": "Clear Logs", "ffmpeg": "FFmpeg Status",
                "about": "About", "speed": "Download Speed", "merge": "Auto-merge Audio/Video"
            },
            "German": {
                "url": "YouTube-URL(s) eingeben:", "dl": "Zur Warteschlange", "set": "Einstellungen",
                "lang": "Sprache", "col": "Design", "succ": "Download abgeschlossen!",
                "err": "Download fehlgeschlagen", "work": "Verarbeitung...", "queue": "Download-Warteschlange",
                "clear": "Alle löschen", "start": "Downloads starten", "pause": "Pause",
                "format": "Ausgabeformat", "quality": "Videoqualität", "location": "Speicherort",
                "browse": "Durchsuchen", "concurrent": "Gleichzeitige Downloads", "logs": "Diagnose",
                "run_diag": "Diagnose starten", "clear_logs": "Logs löschen", "ffmpeg": "FFmpeg-Status",
                "about": "Über", "speed": "Geschwindigkeit", "merge": "Auto-Merge Audio/Video"
            },
            "French": {
                "url": "Entrez les URL(s) YouTube:", "dl": "Ajouter", "set": "Paramètres",
                "lang": "Langue", "col": "Thème", "succ": "Téléchargement terminé!",
                "err": "Échec du téléchargement", "work": "Traitement...", "queue": "File d'attente",
                "clear": "Tout effacer", "start": "Démarrer", "pause": "Pause",
                "format": "Format de sortie", "quality": "Qualité vidéo", "location": "Emplacement",
                "browse": "Parcourir", "concurrent": "Téléchargements simultanés", "logs": "Diagnostics",
                "run_diag": "Lancer diagnostic", "clear_logs": "Effacer logs", "ffmpeg": "Statut FFmpeg",
                "about": "À propos", "speed": "Vitesse", "merge": "Fusion auto Audio/Vidéo"
            },
            "Spanish": {
                "url": "Ingrese URL(s) de YouTube:", "dl": "Agregar", "set": "Ajustes",
                "lang": "Idioma", "col": "Tema", "succ": "¡Descarga completada!",
                "err": "Descarga fallida", "work": "Procesando...", "queue": "Cola de descarga",
                "clear": "Borrar todo", "start": "Iniciar", "pause": "Pausar",
                "format": "Formato de salida", "quality": "Calidad de video", "location": "Ubicación",
                "browse": "Explorar", "concurrent": "Descargas simultáneas", "logs": "Diagnósticos",
                "run_diag": "Ejecutar diagnóstico", "clear_logs": "Borrar logs", "ffmpeg": "Estado FFmpeg",
                "about": "Acerca de", "speed": "Velocidad", "merge": "Auto-fusión Audio/Video"
            },
            "Japanese": {
                "url": "YouTube URLを入力:", "dl": "キューに追加", "set": "設定",
                "lang": "言語", "col": "テーマ", "succ": "ダウンロード完了!",
                "err": "ダウンロード失敗", "work": "処理中...", "queue": "ダウンロードキュー",
                "clear": "すべてクリア", "start": "開始", "pause": "一時停止",
                "format": "出力形式", "quality": "動画品質", "location": "保存場所",
                "browse": "参照", "concurrent": "同時ダウンロード数", "logs": "診断",
                "run_diag": "診断実行", "clear_logs": "ログクリア", "ffmpeg": "FFmpeg状態",
                "about": "情報", "speed": "速度", "merge": "音声/動画自動結合"
            },
            "Chinese": {
                "url": "输入YouTube链接:", "dl": "添加到队列", "set": "设置",
                "lang": "语言", "col": "主题", "succ": "下载完成!",
                "err": "下载失败", "work": "处理中...", "queue": "下载队列",
                "clear": "清空", "start": "开始下载", "pause": "暂停",
                "format": "输出格式", "quality": "视频质量", "location": "下载位置",
                "browse": "浏览", "concurrent": "并发下载数", "logs": "诊断",
                "run_diag": "运行诊断", "clear_logs": "清除日志", "ffmpeg": "FFmpeg状态",
                "about": "关于", "speed": "下载速度", "merge": "自动合并音视频"
            },
            "Korean": {
                "url": "YouTube URL 입력:", "dl": "대기열에 추가", "set": "설정",
                "lang": "언어", "col": "테마", "succ": "다운로드 완료!",
                "err": "다운로드 실패", "work": "처리 중...", "queue": "다운로드 대기열",
                "clear": "모두 지우기", "start": "시작", "pause": "일시정지",
                "format": "출력 형식", "quality": "비디오 품질", "location": "저장 위치",
                "browse": "찾아보기", "concurrent": "동시 다운로드", "logs": "진단",
                "run_diag": "진단 실행", "clear_logs": "로그 지우기", "ffmpeg": "FFmpeg 상태",
                "about": "정보", "speed": "속도", "merge": "오디오/비디오 자동 병합"
            },
            "Russian": {
                "url": "Введите URL YouTube:", "dl": "Добавить", "set": "Настройки",
                "lang": "Язык", "col": "Тема", "succ": "Загрузка завершена!",
                "err": "Ошибка загрузки", "work": "Обработка...", "queue": "Очередь",
                "clear": "Очистить", "start": "Начать", "pause": "Пауза",
                "format": "Формат", "quality": "Качество", "location": "Папка",
                "browse": "Обзор", "concurrent": "Одновременных загрузок", "logs": "Диагностика",
                "run_diag": "Запустить", "clear_logs": "Очистить логи", "ffmpeg": "Статус FFmpeg",
                "about": "О программе", "speed": "Скорость", "merge": "Авто-слияние"
            },
            "Portuguese": {
                "url": "Insira URL(s) do YouTube:", "dl": "Adicionar", "set": "Configurações",
                "lang": "Idioma", "col": "Tema", "succ": "Download concluído!",
                "err": "Falha no download", "work": "Processando...", "queue": "Fila de download",
                "clear": "Limpar tudo", "start": "Iniciar", "pause": "Pausar",
                "format": "Formato de saída", "quality": "Qualidade do vídeo", "location": "Local",
                "browse": "Procurar", "concurrent": "Downloads simultâneos", "logs": "Diagnósticos",
                "run_diag": "Executar diagnóstico", "clear_logs": "Limpar logs", "ffmpeg": "Status FFmpeg",
                "about": "Sobre", "speed": "Velocidade", "merge": "Auto-mesclar Áudio/Vídeo"
            },
            "Arabic": {
                "url": "أدخل رابط YouTube:", "dl": "إضافة", "set": "الإعدادات",
                "lang": "اللغة", "col": "السمة", "succ": "اكتمل التنزيل!",
                "err": "فشل التنزيل", "work": "جاري المعالجة...", "queue": "قائمة التنزيل",
                "clear": "مسح الكل", "start": "بدء", "pause": "إيقاف مؤقت",
                "format": "تنسيق الإخراج", "quality": "جودة الفيديو", "location": "موقع التنزيل",
                "browse": "تصفح", "concurrent": "التنزيلات المتزامنة", "logs": "التشخيصات",
                "run_diag": "تشغيل التشخيص", "clear_logs": "مسح السجلات", "ffmpeg": "حالة FFmpeg",
                "about": "حول", "speed": "السرعة", "merge": "دمج تلقائي"
            }
        }
        
        self.current_lang = "English"
        self.current_theme = "Midnight Blue"
        ctk.set_appearance_mode("Dark")
        
        self._setup_ui()
        self._apply_theme("Midnight Blue")
        self._start_queue_processor()

    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        self.logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.logo_frame.pack(pady=30, padx=20)
        
        self.logo = ctk.CTkLabel(self.logo_frame, text="⚡ VANQUISH", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo.pack()
        self.logo_sub = ctk.CTkLabel(self.logo_frame, text="PRO DOWNLOADER", font=ctk.CTkFont(size=12, weight="bold"))
        self.logo_sub.pack()

        self.nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_frame.pack(fill="x", padx=15, pady=20)

        self.btn_download = ctk.CTkButton(self.nav_frame, text="📥  Downloader", height=45, 
                                          anchor="w", font=ctk.CTkFont(size=14),
                                          command=self.show_download_view)
        self.btn_download.pack(fill="x", pady=5)

        self.btn_queue = ctk.CTkButton(self.nav_frame, text="📋  Queue", height=45,
                                       anchor="w", font=ctk.CTkFont(size=14),
                                       command=self.show_queue_view)
        self.btn_queue.pack(fill="x", pady=5)

        self.btn_settings = ctk.CTkButton(self.nav_frame, text="⚙️  Settings", height=45,
                                          anchor="w", font=ctk.CTkFont(size=14),
                                          command=self.show_settings_view)
        self.btn_settings.pack(fill="x", pady=5)

        self.btn_diagnostics = ctk.CTkButton(self.nav_frame, text="🔍  Diagnostics", height=45,
                                             anchor="w", font=ctk.CTkFont(size=14),
                                             command=self.show_diagnostics_view)
        self.btn_diagnostics.pack(fill="x", pady=5)

        self.stats_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.stats_frame.pack(side="bottom", fill="x", padx=15, pady=20)
        
        self.ffmpeg_status = ctk.CTkLabel(self.stats_frame, 
                                          text=f"FFmpeg: {'✓ Ready' if self.ffmpeg.is_available() else '✕ Not Found'}",
                                          font=ctk.CTkFont(size=11),
                                          text_color="#4CAF50" if self.ffmpeg.is_available() else "#F44336")
        self.ffmpeg_status.pack(pady=5)
        
        self.version_label = ctk.CTkLabel(self.stats_frame, text="Version 2.0 Pro", 
                                          font=ctk.CTkFont(size=11), text_color="gray")
        self.version_label.pack(pady=5)

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self._create_download_view()
        self._create_queue_view()
        self._create_settings_view()
        self._create_diagnostics_view()

    def _create_download_view(self):
        self.download_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        header = ctk.CTkFrame(self.download_frame, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(40, 20))
        
        title = ctk.CTkLabel(header, text="Download Videos", font=ctk.CTkFont(size=28, weight="bold"))
        title.pack(anchor="w")
        subtitle = ctk.CTkLabel(header, text="Paste YouTube URLs to download in high quality", 
                               font=ctk.CTkFont(size=14), text_color="gray")
        subtitle.pack(anchor="w", pady=(5, 0))

        input_card = ctk.CTkFrame(self.download_frame, corner_radius=15)
        input_card.pack(fill="x", padx=40, pady=20)
        
        self.url_label = ctk.CTkLabel(input_card, text=self.languages[self.current_lang]["url"], 
                                      font=ctk.CTkFont(size=14, weight="bold"))
        self.url_label.pack(anchor="w", padx=25, pady=(20, 10))
        
        self.url_textbox = ctk.CTkTextbox(input_card, height=100, corner_radius=10)
        self.url_textbox.pack(fill="x", padx=25, pady=(0, 15))
        self.url_textbox.insert("1.0", "Enter one URL per line for batch downloads...")
        self.url_textbox.bind("<FocusIn>", self._clear_placeholder)

        options_frame = ctk.CTkFrame(input_card, fg_color="transparent")
        options_frame.pack(fill="x", padx=25, pady=(0, 20))
        
        format_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        format_frame.pack(side="left", padx=(0, 30))
        ctk.CTkLabel(format_frame, text="Format:", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.format_var = ctk.StringVar(value="MP4")
        self.format_menu = ctk.CTkOptionMenu(format_frame, values=["MP4", "MKV", "MP3"], 
                                             variable=self.format_var, width=120)
        self.format_menu.pack(pady=(5, 0))
        
        quality_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        quality_frame.pack(side="left", padx=(0, 30))
        ctk.CTkLabel(quality_frame, text="Quality:", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.quality_var = ctk.StringVar(value="1080p")
        self.quality_menu = ctk.CTkOptionMenu(quality_frame, values=["Best", "8K", "4K", "1080p", "720p", "480p", "360p"], 
                                              variable=self.quality_var, width=120)
        self.quality_menu.pack(pady=(5, 0))
        
        merge_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        merge_frame.pack(side="left")
        ctk.CTkLabel(merge_frame, text="Options:", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.merge_var = ctk.BooleanVar(value=True)
        self.merge_check = ctk.CTkCheckBox(merge_frame, text="Merge Audio/Video", variable=self.merge_var)
        self.merge_check.pack(pady=(5, 0))

        btn_frame = ctk.CTkFrame(self.download_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=40, pady=10)
        
        self.add_queue_btn = ctk.CTkButton(btn_frame, text="➕ Add to Queue", height=50,
                                           font=ctk.CTkFont(size=15, weight="bold"),
                                           corner_radius=12, command=self._add_to_queue)
        self.add_queue_btn.pack(side="left", padx=(0, 10))
        
        self.quick_download_btn = ctk.CTkButton(btn_frame, text="⚡ Quick Download", height=50,
                                                font=ctk.CTkFont(size=15, weight="bold"),
                                                corner_radius=12, command=self._quick_download)
        self.quick_download_btn.pack(side="left")

        progress_card = ctk.CTkFrame(self.download_frame, corner_radius=15)
        progress_card.pack(fill="x", padx=40, pady=20)
        
        ctk.CTkLabel(progress_card, text="Current Download", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=25, pady=(20, 10))
        
        self.current_title_label = ctk.CTkLabel(progress_card, text="No active download", 
                                                font=ctk.CTkFont(size=12), text_color="gray")
        self.current_title_label.pack(anchor="w", padx=25)
        
        self.progress_widget = AnimatedProgressBar(progress_card)
        self.progress_widget.pack(pady=20)
        
        self.status_label = ctk.CTkLabel(progress_card, text="Ready", font=ctk.CTkFont(size=13))
        self.status_label.pack(pady=(0, 20))

    def _create_queue_view(self):
        self.queue_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        header = ctk.CTkFrame(self.queue_frame, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(40, 20))
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(fill="x")
        
        title = ctk.CTkLabel(title_frame, text="Download Queue", font=ctk.CTkFont(size=28, weight="bold"))
        title.pack(side="left")
        
        self.queue_count_label = ctk.CTkLabel(title_frame, text="0 items", 
                                              font=ctk.CTkFont(size=14), text_color="gray")
        self.queue_count_label.pack(side="left", padx=15)

        controls_frame = ctk.CTkFrame(header, fg_color="transparent")
        controls_frame.pack(fill="x", pady=(15, 0))
        
        self.start_all_btn = ctk.CTkButton(controls_frame, text="▶ Start All", height=40,
                                           corner_radius=10, command=self._start_all_downloads)
        self.start_all_btn.pack(side="left", padx=(0, 10))
        
        self.pause_all_btn = ctk.CTkButton(controls_frame, text="⏸ Pause All", height=40,
                                           corner_radius=10, command=self._pause_all_downloads)
        self.pause_all_btn.pack(side="left", padx=(0, 10))
        
        self.clear_all_btn = ctk.CTkButton(controls_frame, text="🗑 Clear All", height=40,
                                           corner_radius=10, command=self._clear_queue)
        self.clear_all_btn.pack(side="left")

        self.queue_scroll = ctk.CTkScrollableFrame(self.queue_frame, corner_radius=15)
        self.queue_scroll.pack(fill="both", expand=True, padx=40, pady=20)

    def _create_settings_view(self):
        self.settings_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        header = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(40, 20))
        
        title = ctk.CTkLabel(header, text="Settings", font=ctk.CTkFont(size=28, weight="bold"))
        title.pack(anchor="w")

        settings_scroll = ctk.CTkScrollableFrame(self.settings_frame, fg_color="transparent")
        settings_scroll.pack(fill="both", expand=True, padx=40, pady=20)

        location_card = ctk.CTkFrame(settings_scroll, corner_radius=15)
        location_card.pack(fill="x", pady=10)
        
        ctk.CTkLabel(location_card, text="📁 Download Location", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=25, pady=(20, 10))
        
        path_frame = ctk.CTkFrame(location_card, fg_color="transparent")
        path_frame.pack(fill="x", padx=25, pady=(0, 20))
        
        self.path_entry = ctk.CTkEntry(path_frame, height=40, width=400)
        self.path_entry.pack(side="left", padx=(0, 10))
        self.path_entry.insert(0, self.current_download_path)
        
        self.browse_btn = ctk.CTkButton(path_frame, text="Browse", height=40, width=100,
                                        command=self._browse_location)
        self.browse_btn.pack(side="left")

        appearance_card = ctk.CTkFrame(settings_scroll, corner_radius=15)
        appearance_card.pack(fill="x", pady=10)
        
        ctk.CTkLabel(appearance_card, text="🎨 Appearance", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=25, pady=(20, 10))
        
        theme_frame = ctk.CTkFrame(appearance_card, fg_color="transparent")
        theme_frame.pack(fill="x", padx=25, pady=(0, 10))
        
        ctk.CTkLabel(theme_frame, text="Theme:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 15))
        self.theme_menu = ctk.CTkOptionMenu(theme_frame, values=list(self.themes.keys()),
                                            command=self._apply_theme, width=180)
        self.theme_menu.pack(side="left")
        
        lang_frame = ctk.CTkFrame(appearance_card, fg_color="transparent")
        lang_frame.pack(fill="x", padx=25, pady=(0, 20))
        
        ctk.CTkLabel(lang_frame, text="Language:", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 15))
        self.lang_menu = ctk.CTkOptionMenu(lang_frame, values=list(self.languages.keys()),
                                           command=self._update_language, width=180)
        self.lang_menu.pack(side="left")

        performance_card = ctk.CTkFrame(settings_scroll, corner_radius=15)
        performance_card.pack(fill="x", pady=10)
        
        ctk.CTkLabel(performance_card, text="⚡ Performance", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=25, pady=(20, 10))
        
        concurrent_frame = ctk.CTkFrame(performance_card, fg_color="transparent")
        concurrent_frame.pack(fill="x", padx=25, pady=(0, 10))
        
        ctk.CTkLabel(concurrent_frame, text="Max Concurrent Downloads:", 
                    font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 15))
        self.concurrent_var = ctk.StringVar(value="3")
        self.concurrent_menu = ctk.CTkOptionMenu(concurrent_frame, values=["1", "2", "3", "4", "5"],
                                                 variable=self.concurrent_var,
                                                 command=self._update_concurrent, width=100)
        self.concurrent_menu.pack(side="left")
        
        speed_frame = ctk.CTkFrame(performance_card, fg_color="transparent")
        speed_frame.pack(fill="x", padx=25, pady=(0, 20))
        
        self.throttle_var = ctk.BooleanVar(value=False)
        self.throttle_check = ctk.CTkCheckBox(speed_frame, text="Limit download speed (for stability)",
                                              variable=self.throttle_var)
        self.throttle_check.pack(anchor="w")

        ffmpeg_card = ctk.CTkFrame(settings_scroll, corner_radius=15)
        ffmpeg_card.pack(fill="x", pady=10)
        
        ctk.CTkLabel(ffmpeg_card, text="🎬 FFmpeg Configuration", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=25, pady=(20, 10))
        
        ffmpeg_info = ctk.CTkFrame(ffmpeg_card, fg_color="transparent")
        ffmpeg_info.pack(fill="x", padx=25, pady=(0, 20))
        
        status_text = "✓ FFmpeg is available" if self.ffmpeg.is_available() else "✕ FFmpeg not found"
        status_color = "#4CAF50" if self.ffmpeg.is_available() else "#F44336"
        self.ffmpeg_label = ctk.CTkLabel(ffmpeg_info, text=status_text, 
                                         font=ctk.CTkFont(size=13), text_color=status_color)
        self.ffmpeg_label.pack(anchor="w")
        
        if self.ffmpeg.is_available():
            version_text = self.ffmpeg.get_version()
            ctk.CTkLabel(ffmpeg_info, text=version_text[:60], 
                        font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", pady=(5, 0))

    def _create_diagnostics_view(self):
        self.diagnostics_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        
        header = ctk.CTkFrame(self.diagnostics_frame, fg_color="transparent")
        header.pack(fill="x", padx=40, pady=(40, 20))
        
        title = ctk.CTkLabel(header, text="Network Diagnostics", font=ctk.CTkFont(size=28, weight="bold"))
        title.pack(anchor="w")
        subtitle = ctk.CTkLabel(header, text="Real-time network analysis and troubleshooting", 
                               font=ctk.CTkFont(size=14), text_color="gray")
        subtitle.pack(anchor="w", pady=(5, 0))

        controls = ctk.CTkFrame(self.diagnostics_frame, fg_color="transparent")
        controls.pack(fill="x", padx=40, pady=(0, 20))
        
        self.run_diag_btn = ctk.CTkButton(controls, text="🔍 Run Full Diagnostics", height=45,
                                          corner_radius=10, command=self._run_diagnostics)
        self.run_diag_btn.pack(side="left", padx=(0, 10))
        
        self.clear_logs_btn = ctk.CTkButton(controls, text="🗑 Clear Logs", height=45,
                                            corner_radius=10, command=self._clear_logs)
        self.clear_logs_btn.pack(side="left")

        log_card = ctk.CTkFrame(self.diagnostics_frame, corner_radius=15)
        log_card.pack(fill="both", expand=True, padx=40, pady=(0, 40))
        
        ctk.CTkLabel(log_card, text="Diagnostic Logs", 
                    font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=25, pady=(20, 10))
        
        self.log_textbox = ctk.CTkTextbox(log_card, corner_radius=10, font=ctk.CTkFont(family="Consolas", size=12))
        self.log_textbox.pack(fill="both", expand=True, padx=25, pady=(0, 20))
        self.log_textbox.configure(state="disabled")

    def _clear_placeholder(self, event):
        current_text = self.url_textbox.get("1.0", "end-1c")
        if current_text == "Enter one URL per line for batch downloads...":
            self.url_textbox.delete("1.0", "end")

    def _browse_location(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory(initialdir=self.current_download_path)
        if folder:
            self.current_download_path = folder
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)

    def _update_concurrent(self, value):
        self.max_concurrent = int(value)
        self.executor._max_workers = self.max_concurrent

    def _update_language(self, lang):
        self.current_lang = lang
        l = self.languages[lang]
        self.url_label.configure(text=l["url"])

    def _apply_theme(self, theme_name):
        self.current_theme = theme_name
        c = self.themes[theme_name]
        
        self.configure(fg_color=c["bg"])
        self.sidebar.configure(fg_color=c["side"])
        self.main_container.configure(fg_color=c["bg"])
        
        for btn in [self.btn_download, self.btn_queue, self.btn_settings, self.btn_diagnostics,
                    self.add_queue_btn, self.quick_download_btn, self.start_all_btn, 
                    self.pause_all_btn, self.clear_all_btn, self.browse_btn,
                    self.run_diag_btn, self.clear_logs_btn]:
            btn.configure(fg_color=c["main"], hover_color=c["hover"])
            
        for menu in [self.format_menu, self.quality_menu, self.theme_menu, 
                     self.lang_menu, self.concurrent_menu]:
            menu.configure(fg_color=c["main"], button_color=c["main"], button_hover_color=c["hover"])
            
        self.progress_widget.progress_bar.configure(progress_color=c["main"])

    def show_download_view(self):
        self._hide_all_views()
        self.download_frame.pack(fill="both", expand=True)

    def show_queue_view(self):
        self._hide_all_views()
        self.queue_frame.pack(fill="both", expand=True)

    def show_settings_view(self):
        self._hide_all_views()
        self.settings_frame.pack(fill="both", expand=True)

    def show_diagnostics_view(self):
        self._hide_all_views()
        self.diagnostics_frame.pack(fill="both", expand=True)

    def _hide_all_views(self):
        self.download_frame.pack_forget()
        self.queue_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.diagnostics_frame.pack_forget()

    def _add_to_queue(self):
        urls = self.url_textbox.get("1.0", "end-1c").strip().split('\n')
        urls = [u.strip() for u in urls if u.strip() and u.strip() != "Enter one URL per line for batch downloads..."]
        
        for url in urls:
            if "youtube.com" in url or "youtu.be" in url:
                self._create_queue_item(url)
        
        self.url_textbox.delete("1.0", "end")
        self._update_queue_count()
        
        if urls:
            self.show_queue_view()

    def _create_queue_item(self, url, title=None):
        if title is None:
            title = url[:50]
        
        item = DownloadItem(self.queue_scroll, title, url, self._remove_queue_item)
        item.pack(fill="x", pady=5)
        self.download_items.append(item)
        
        threading.Thread(target=self._fetch_video_title, args=(item,), daemon=True).start()

    def _fetch_video_title(self, item):
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(item.url, download=False)
                title = info.get('title', item.url[:50])
                self.after(0, lambda: item.title_label.configure(
                    text=title[:50] + "..." if len(title) > 50 else title))
                item.title = title
        except:
            pass

    def _remove_queue_item(self, item):
        item.pack_forget()
        if item in self.download_items:
            self.download_items.remove(item)
        item.destroy()
        self._update_queue_count()

    def _update_queue_count(self):
        count = len(self.download_items)
        self.queue_count_label.configure(text=f"{count} item{'s' if count != 1 else ''}")

    def _clear_queue(self):
        for item in self.download_items[:]:
            if item.status == "pending":
                self._remove_queue_item(item)

    def _start_all_downloads(self):
        for item in self.download_items:
            if item.status == "pending":
                threading.Thread(target=self._download_item, args=(item,), daemon=True).start()

    def _pause_all_downloads(self):
        pass

    def _quick_download(self):
        urls = self.url_textbox.get("1.0", "end-1c").strip().split('\n')
        urls = [u.strip() for u in urls if u.strip() and u.strip() != "Enter one URL per line for batch downloads..."]
        
        if urls:
            self.url_textbox.delete("1.0", "end")
            for url in urls:
                if "youtube.com" in url or "youtu.be" in url:
                    threading.Thread(target=self._download_single, args=(url,), daemon=True).start()

    def _download_single(self, url):
        self.add_queue_btn.configure(state="disabled")
        self.quick_download_btn.configure(state="disabled")
        self.status_label.configure(text=self.languages[self.current_lang]["work"], text_color="#3399FF")
        self.progress_widget.start_indeterminate()
        
        format_choice = self.format_var.get()
        quality_choice = self.quality_var.get()
        
        quality_map = {
            "Best": "bestvideo+bestaudio/best",
            "8K": "bestvideo[height<=4320]+bestaudio/best[height<=4320]",
            "4K": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]"
        }
        
        format_map = {"MP4": "mp4", "MKV": "mkv", "MP3": "mp3"}
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    percent = d.get('_percent_str', '0%').replace('%', '').strip()
                    speed = d.get('_speed_str', 'N/A')
                    eta = d.get('_eta_str', 'N/A')
                    self.after(0, lambda: self.progress_widget.stop_indeterminate())
                    self.after(0, lambda: self.progress_widget.set_progress(float(percent), speed, eta))
                    title = d.get('info_dict', {}).get('title', 'Downloading...')
                    self.after(0, lambda: self.current_title_label.configure(text=title[:60]))
                except:
                    pass
            elif d['status'] == 'finished':
                self.after(0, lambda: self.progress_widget.set_progress(100, "Complete", "Done"))
        
        ydl_opts = {
            'format': quality_map.get(quality_choice, "best"),
            'outtmpl': os.path.join(self.current_download_path, "%(title)s.%(ext)s"),
            'nocheckcertificate': True,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'concurrent_fragment_downloads': 8,
            'buffersize': 1024 * 64,
            'http_chunk_size': 10485760,
            'progress_hooks': [progress_hook],
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        if format_choice == "MP3":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320'
            }]
        elif self.merge_var.get() and self.ffmpeg.is_available():
            ydl_opts['merge_output_format'] = format_map.get(format_choice, "mp4")
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': format_map.get(format_choice, "mp4")
            }]
            
        if self.ffmpeg.is_available():
            ydl_opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg.get_path())
        
        try:
            self.diagnostics.add_log("INFO", f"Starting download: {url}")
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.diagnostics.add_log("INFO", "Download completed successfully")
            self.after(0, lambda: self.status_label.configure(
                text=self.languages[self.current_lang]["succ"], text_color="#4CAF50"))
        except Exception as e:
            self.diagnostics.add_log("ERROR", f"Download failed: {str(e)}")
            self.after(0, lambda: self.status_label.configure(
                text=f"{self.languages[self.current_lang]['err']}: {str(e)[:50]}", text_color="#F44336"))
        
        self.after(0, lambda: self.progress_widget.stop_indeterminate())
        self.after(0, lambda: self.add_queue_btn.configure(state="normal"))
        self.after(0, lambda: self.quick_download_btn.configure(state="normal"))

    def _download_item(self, item):
        item.status = "downloading"
        item.update_progress(0, "Starting...")
        
        format_choice = self.format_var.get()
        quality_choice = self.quality_var.get()
        
        quality_map = {
            "Best": "bestvideo+bestaudio/best",
            "8K": "bestvideo[height<=4320]+bestaudio/best[height<=4320]",
            "4K": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]"
        }
        
        format_map = {"MP4": "mp4", "MKV": "mkv", "MP3": "mp3"}
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    percent = d.get('_percent_str', '0%').replace('%', '').strip()
                    speed = d.get('_speed_str', 'N/A')
                    self.after(0, lambda: item.update_progress(float(percent), f"{speed}"))
                except:
                    pass
            elif d['status'] == 'finished':
                self.after(0, lambda: item.update_progress(100, "Processing..."))
        
        ydl_opts = {
            'format': quality_map.get(quality_choice, "best"),
            'outtmpl': os.path.join(self.current_download_path, "%(title)s.%(ext)s"),
            'nocheckcertificate': True,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'concurrent_fragment_downloads': 8,
            'buffersize': 1024 * 64,
            'http_chunk_size': 10485760,
            'progress_hooks': [progress_hook],
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        if format_choice == "MP3":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320'
            }]
        elif self.merge_var.get() and self.ffmpeg.is_available():
            ydl_opts['merge_output_format'] = format_map.get(format_choice, "mp4")
            
        if self.ffmpeg.is_available():
            ydl_opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg.get_path())
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([item.url])
            self.after(0, item.set_complete)
        except Exception as e:
            self.after(0, lambda: item.set_error(str(e)[:30]))

    def _start_queue_processor(self):
        pass

    def _run_diagnostics(self):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        
        def run():
            results = self.diagnostics.run_full_diagnostics()
            for line in results:
                self.after(0, lambda l=line: self._append_log(l))
                time.sleep(0.2)
        
        threading.Thread(target=run, daemon=True).start()

    def _append_log(self, text):
        self.log_textbox.configure(state="normal")
        color = "white"
        if "[ERROR]" in text:
            color = "#F44336"
        elif "[INFO]" in text:
            color = "#4CAF50"
        self.log_textbox.insert("end", text + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def _clear_logs(self):
        self.diagnostics.clear_logs()
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")


if __name__ == "__main__":
    app = VanquishDownloaderPro()
    app.mainloop()
