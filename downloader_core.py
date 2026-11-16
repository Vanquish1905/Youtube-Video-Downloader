"""Download engine for Vanquish Downloader.

Everything in here is free of UI code so it can be tested on its own.
"""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime

APP_NAME = "Vanquish Downloader"
APP_VERSION = "3.0.0"

IS_WINDOWS = platform.system() == "Windows"

QUALITY_CHOICES = ["Best", "4320p (8K)", "2160p (4K)", "1440p", "1080p", "720p", "480p", "360p"]
VIDEO_FORMATS = ["MP4", "MKV"]
AUDIO_FORMATS = ["MP3", "M4A"]
FORMAT_CHOICES = VIDEO_FORMATS + AUDIO_FORMATS
COOKIE_BROWSERS = ["None", "chrome", "firefox", "edge", "brave", "opera", "vivaldi", "chromium", "safari"]

# How long extracted info (and the signed stream URLs in it) is reused
# before a fresh extraction is done at download time.
INFO_MAX_AGE = 20 * 60

_YOUTUBE_RE = re.compile(
    r"^https?://(?:[\w-]+\.)?(?:youtube\.com|youtube-nocookie\.com|youtu\.be)/\S+$",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- paths

def resource_dirs():
    """Directories that may contain bundled tools (ffmpeg, deno, ...)."""
    dirs = []
    if getattr(sys, "frozen", False):
        dirs.append(getattr(sys, "_MEIPASS", ""))
        dirs.append(os.path.dirname(sys.executable))
    else:
        dirs.append(os.path.dirname(os.path.abspath(__file__)))
    out = []
    for d in dirs:
        if d and d not in out:
            out.append(d)
            out.append(os.path.join(d, "ffmpeg"))
            out.append(os.path.join(d, "bin"))
    return out


def resource_path(name):
    for d in resource_dirs():
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def _find_tool(*names):
    exe = ".exe" if IS_WINDOWS else ""
    for name in names:
        for d in resource_dirs():
            p = os.path.join(d, name + exe)
            if os.path.isfile(p):
                return p
        p = shutil.which(name)
        if p:
            return p
    return None


def find_ffmpeg():
    return _find_tool("ffmpeg")


def find_js_runtimes():
    """Map of yt-dlp JS runtime name -> config for every runtime we can find.

    YouTube now hides most high quality formats behind a JavaScript challenge.
    Without a runtime yt-dlp can only use a fallback client that tops out at
    low resolutions, which was the main cause of the "always low quality" bug.
    """
    runtimes = {}
    for key, names in (("deno", ("deno",)), ("node", ("node",)), ("bun", ("bun",)), ("quickjs", ("qjs", "quickjs"))):
        path = _find_tool(*names)
        if path:
            runtimes[key] = {"path": path}
    return runtimes


def ffmpeg_version(path):
    if not path:
        return "Not found"
    try:
        kwargs = {}
        if IS_WINDOWS:
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10, **kwargs)
        return out.stdout.splitlines()[0] if out.stdout else "Unknown version"
    except Exception:
        return "Unknown version"


def ytdlp_version():
    try:
        from yt_dlp.version import __version__
        return __version__
    except Exception:
        return "unknown"


def config_dir():
    if IS_WINDOWS:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "VanquishDownloader")
    if platform.system() == "Darwin":
        return os.path.expanduser("~/Library/Application Support/VanquishDownloader")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "vanquish-downloader")


def default_download_dir():
    return os.path.join(os.path.expanduser("~"), "Downloads", "VanquishDownloads")


def open_in_file_manager(path):
    """Open a folder, or reveal a file, in the system file manager."""
    if not path or not os.path.exists(path):
        return False
    try:
        if IS_WINDOWS:
            if os.path.isfile(path):
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            else:
                os.startfile(path)  # noqa: S606
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-R", path] if os.path.isfile(path) else ["open", path])
        else:
            folder = path if os.path.isdir(path) else os.path.dirname(path)
            subprocess.Popen(["xdg-open", folder])
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------- settings

@dataclass
class Settings:
    download_dir: str = field(default_factory=default_download_dir)
    theme: str = "Midnight Blue"
    language: str = "English"
    quality: str = "1080p"
    output_format: str = "MP4"
    max_concurrent: int = 3
    speed_limit_enabled: bool = False
    speed_limit_mb: float = 5.0
    expand_playlists: bool = True
    embed_metadata: bool = True
    cookies_browser: str = "None"

    @classmethod
    def path(cls):
        return os.path.join(config_dir(), "settings.json")

    @classmethod
    def load(cls):
        s = cls()
        try:
            with open(cls.path(), encoding="utf-8") as fh:
                data = json.load(fh)
            known = {f.name: f.type for f in fields(cls)}
            for key, value in data.items():
                if key in known:
                    setattr(s, key, value)
        except (OSError, ValueError):
            pass
        s.validate()
        return s

    def validate(self):
        if self.quality not in QUALITY_CHOICES:
            self.quality = "1080p"
        if self.output_format not in FORMAT_CHOICES:
            self.output_format = "MP4"
        try:
            self.max_concurrent = max(1, min(8, int(self.max_concurrent)))
        except (TypeError, ValueError):
            self.max_concurrent = 3
        try:
            self.speed_limit_mb = max(0.1, float(self.speed_limit_mb))
        except (TypeError, ValueError):
            self.speed_limit_mb = 5.0
        if self.cookies_browser not in COOKIE_BROWSERS:
            self.cookies_browser = "None"
        if not isinstance(self.download_dir, str) or not self.download_dir.strip():
            self.download_dir = default_download_dir()

    def save(self):
        try:
            os.makedirs(config_dir(), exist_ok=True)
            tmp = self.path() + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(asdict(self), fh, indent=2)
            os.replace(tmp, self.path())
            return True
        except OSError:
            return False


# --------------------------------------------------------------------------- urls

def normalize_url(text):
    text = text.strip().strip("<>\"'")
    if not text:
        return None
    if not re.match(r"^https?://", text, re.IGNORECASE):
        text = "https://" + text
    return text if _YOUTUBE_RE.match(text) else None


def parse_urls(text):
    """Return (valid_urls, rejected_lines) from free text, de-duplicated."""
    valid, rejected, seen = [], [], set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        found = [u for u in (normalize_url(tok) for tok in re.split(r"[\s,]+", line)) if u]
        if not found:
            rejected.append(line)
        for url in found:
            if url not in seen:
                seen.add(url)
                valid.append(url)
    return valid, rejected


def is_playlist_url(url):
    return "/playlist" in url.lower() and "list=" in url


# --------------------------------------------------------------------------- formats

def quality_height(label):
    m = re.match(r"(\d+)p", label or "")
    return int(m.group(1)) if m else None


def is_audio_format(fmt):
    return fmt in AUDIO_FORMATS


def build_format_options(output_format, quality, has_ffmpeg):
    """yt-dlp options that decide which streams get downloaded.

    Uses format sorting instead of hard filters so that the best stream at or
    below the requested height is picked, and if nothing that small exists the
    closest larger one is used instead of silently dropping to a low quality
    combined stream.
    """
    opts = {}
    if is_audio_format(output_format):
        if output_format == "M4A":
            opts["format"] = "ba[ext=m4a]/ba/b"
        else:
            opts["format"] = "ba/b"
        opts["format_sort"] = ["abr", "asr"]
        return opts

    height = quality_height(quality)
    res = f"res:{height}" if height else "res"
    sort = [res, "fps"]
    if output_format == "MP4":
        # Same resolution and frame rate: prefer codecs that play everywhere
        # in an MP4. Resolution still wins, so 4K is not capped by H.264.
        sort += ["vcodec:avc", "acodec:aac"]
    opts["format_sort"] = sort

    if has_ffmpeg:
        opts["format"] = "bv*+ba/b"
        opts["merge_output_format"] = output_format.lower()
    else:
        # Without FFmpeg separate streams can not be merged, so only
        # pre-muxed streams are possible (YouTube caps these at 360p).
        opts["format"] = "b"
    return opts


def build_postprocessors(output_format, embed_metadata):
    pps = []
    if output_format == "MP3":
        pps.append({"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"})
    elif output_format == "M4A":
        # Copies the stream when it already is AAC, so no quality loss.
        pps.append({"key": "FFmpegExtractAudio", "preferredcodec": "m4a"})
    if embed_metadata:
        pps.append({"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": True})
        if output_format in AUDIO_FORMATS:
            pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
    return pps


class _Logger:
    def __init__(self, sink):
        self.sink = sink

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        if self.sink:
            self.sink("WARN", _strip_ansi(msg))

    def error(self, msg):
        if self.sink:
            self.sink("ERROR", _strip_ansi(msg))


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text):
    return _ANSI_RE.sub("", str(text))


def clean_error(exc):
    msg = _strip_ansi(exc)
    msg = re.sub(r"^ERROR:\s*", "", msg)
    msg = re.sub(r"^\[youtube\]\s*[\w-]+:\s*", "", msg)
    return msg.strip() or exc.__class__.__name__


def base_ydl_options(settings, ffmpeg_path, js_runtimes, log_sink=None):
    opts = {
        "quiet": True,
        "no_warnings": False,
        "noprogress": True,
        "logger": _Logger(log_sink),
        "noplaylist": True,
        "windowsfilenames": True,
        "continuedl": True,
        "socket_timeout": 20,
        "retries": 10,
        "fragment_retries": 10,
        "extractor_retries": 3,
        "file_access_retries": 5,
        "concurrent_fragment_downloads": 8,
        "http_chunk_size": 10 * 1024 * 1024,
        "js_runtimes": js_runtimes or {},
        # Only fetched if the bundled solver scripts are missing.
        "remote_components": ["ejs:github"],
    }
    if ffmpeg_path:
        opts["ffmpeg_location"] = ffmpeg_path
    if settings.cookies_browser and settings.cookies_browser != "None":
        opts["cookiesfrombrowser"] = (settings.cookies_browser,)
    return opts


def build_download_options(settings, job, ffmpeg_path, js_runtimes, progress_hook, pp_hook, log_sink=None):
    opts = base_ydl_options(settings, ffmpeg_path, js_runtimes, log_sink)
    opts.update(build_format_options(job.output_format, job.quality, bool(ffmpeg_path)))
    opts["outtmpl"] = {"default": os.path.join(job.download_dir, "%(title).180B.%(ext)s")}
    opts["progress_hooks"] = [progress_hook]
    opts["postprocessor_hooks"] = [pp_hook]
    if ffmpeg_path:
        pps = build_postprocessors(job.output_format, settings.embed_metadata)
        if pps:
            opts["postprocessors"] = pps
        if settings.embed_metadata and is_audio_format(job.output_format):
            opts["writethumbnail"] = True
    if settings.speed_limit_enabled:
        opts["ratelimit"] = int(settings.speed_limit_mb * 1024 * 1024)
    return opts


# --------------------------------------------------------------------------- jobs

class JobState:
    FETCHING = "fetching"
    HELD = "held"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    ERROR = "error"


_job_counter = 0
_job_counter_lock = threading.Lock()


def _next_job_id():
    global _job_counter
    with _job_counter_lock:
        _job_counter += 1
        return _job_counter


@dataclass
class DownloadJob:
    url: str
    output_format: str
    quality: str
    download_dir: str
    title: str = ""
    state: str = JobState.FETCHING
    start_when_ready: bool = True
    info: dict = None
    info_time: float = 0.0
    max_height: int = None
    duration: float = None
    filepath: str = None
    result_height: int = None
    error: str = None
    removed: bool = False
    id: int = field(default_factory=_next_job_id)
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)

    def display_title(self):
        return self.title or self.url

    def fresh_info(self):
        if self.info and self.info.get("formats") and time.time() - self.info_time < INFO_MAX_AGE:
            return self.info
        return None


def summarize_info(info):
    """Pull the handful of fields the UI cares about from an info dict."""
    heights = [f.get("height") for f in info.get("formats") or [] if f.get("height") and f.get("vcodec") != "none"]
    return {
        "title": info.get("title") or "",
        "max_height": max(heights) if heights else info.get("height"),
        "duration": info.get("duration"),
    }


def playlist_entry_url(entry):
    url = entry.get("url") or ""
    if url.startswith("http"):
        return url
    vid = entry.get("id")
    return f"https://www.youtube.com/watch?v={vid}" if vid else None


def format_bytes(n):
    if not n:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024
    return ""


def format_speed(bps):
    return f"{format_bytes(bps)}/s" if bps else ""


def format_eta(seconds):
    if seconds is None:
        return ""
    seconds = int(seconds)
    if seconds >= 3600:
        return f"{seconds // 3600}h {seconds % 3600 // 60:02d}m"
    return f"{seconds // 60}:{seconds % 60:02d}"


def format_duration(seconds):
    if not seconds:
        return ""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def timestamp():
    return datetime.now().strftime("%H:%M:%S")
