# Changelog

## v3.0.0 - 2026-11-16

### Fixed
- **Video quality stuck at 360p.** The app forced YouTube's `android` and `web` player clients. YouTube now blocks most formats on those clients unless extra tokens are provided, so the only stream left was the 360p combined one. The client override is gone, yt-dlp picks working clients on its own, and any installed JavaScript runtime (Deno, Node.js, Bun or QuickJS) is passed to yt-dlp so it can unlock the full format list.
- Quality is now chosen with format sorting instead of hard filters. You get the best stream at or below the height you pick. If nothing that small exists, you get the closest one above it instead of a silent drop to 360p.
- MP4 downloads were re-encoded by `FFmpegVideoConvertor` after every merge. That took minutes and lost quality. Streams are now merged without re-encoding, and H.264/AAC is preferred at the same resolution so MP4 files play everywhere.
- Progress bars never moved because `_percent_str` contains color codes and `float()` failed on it. Progress is now calculated from downloaded/total bytes.
- The UI was updated directly from download threads, which can freeze or crash Tkinter. All updates now go through a queue on the main thread.
- The concurrent downloads setting did nothing. "Start All" launched every item at once. Downloads now run in a real queue that respects the limit.
- Pause did nothing. Pause/Resume now works and resumes from the partial file.
- Removing an item while it downloaded left the download running in the background. It is now stopped.
- Settings changed after an item was queued affected that item. Each item keeps the format and quality it was added with.
- Typing a path into the download location box was ignored unless "Browse" was used.
- "Limit download speed" was a checkbox that had no effect. It now sets a real limit in MB/s.
- Quick Download started every pasted link at the same time on one shared progress bar.
- URL check accepted any text containing "youtube.com". Links are now validated properly, `youtube.com/...` without `https://` works, and duplicates are skipped.
- Changing the language only changed one label.
- New queue items ignored the selected theme.
- SSL certificate checks were turned off (`nocheckcertificate`). They are on again.
- Diagnostics leaked a socket on every run and the log colors were never applied.
- Running without FFmpeg gave no explanation for low quality. A clear warning is now shown.

### Added
- Single downloads page with the input and the download list together.
- Playlist links expand into one item per video (can be turned off).
- 1440p option and M4A (no re-encode) audio option.
- Per-item Pause/Resume, Retry, Open and Remove buttons.
- Shows the highest resolution a video offers before downloading, and the resolution you actually got afterwards.
- Embeds title, chapters and metadata. Audio files also get the cover art.
- Optional browser cookies for age restricted videos or "sign in to confirm" errors.
- Settings are saved between sessions.
- Paste button, Ctrl+Enter to start, Open Folder, Copy Log.
- Diagnostics now also check FFmpeg, the JavaScript runtime and the yt-dlp version, and show the app log live.

### Faster
- Video info is read once when a link is added and reused for the download instead of being fetched twice.
- No more re-encoding after merges.
- Progress updates are throttled so many parallel downloads do not slow the UI down.
- FFmpeg version lookup no longer blocks startup.

### Changed
- Download logic moved into `downloader_core.py`; `main.py` is only the interface.
- Removed the hardcoded old Chrome user agent.
- Added `requirements.txt` and `.gitignore`.

## v2.0.0

- CustomTkinter interface with themes, queue tab, settings and diagnostics.

## v1.0.0

- First release.
