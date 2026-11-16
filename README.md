# Vanquish Downloader

A YouTube downloader with a clean desktop interface. Paste a link (or a whole playlist), pick a quality, and download anything from a quick MP3 to full 4K/8K video.

See [CHANGELOG.md](CHANGELOG.md) for what changed in each version.

---

## Quick Start

### Option 1: Pre-built executable (Windows)

Grab `VanquishDownloader.exe` from the [Releases](../../releases) page, put it anywhere and run it. FFmpeg is bundled.

For full quality you also need **Deno** (see below). Without it YouTube often only serves low resolutions.

### Option 2: Run from source

```bash
git clone https://github.com/vanquish1905/youtube-video-downloader.git
cd youtube-video-downloader
pip install -r requirements.txt
python main.py
```

**You need:**

- Python 3.9 or newer (with Tkinter)
- **FFmpeg** to merge HD video with audio, and for MP3/M4A
- **Deno** (or Node.js 20+) so yt-dlp can unlock YouTube's full format list

| Tool   | Windows                     | macOS                 | Linux                                      |
| ------ | --------------------------- | --------------------- | ------------------------------------------ |
| FFmpeg | `winget install ffmpeg`     | `brew install ffmpeg` | `sudo apt install ffmpeg`                  |
| Deno   | `winget install DenoLand.Deno` | `brew install deno` | `curl -fsSL https://deno.land/install.sh \| sh` |

The app also finds `ffmpeg` and `deno` if you put them next to `main.py` / the `.exe`, or in an `ffmpeg` folder beside it.

### Option 3: Build the executable yourself

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon.ico --name=VanquishDownloader --add-data="icon.ico;." --add-data="ffmpeg;ffmpeg" --collect-all customtkinter --collect-all yt_dlp_ejs main.py
```

Put `ffmpeg.exe` in an `ffmpeg` folder before building. To ship Deno with it, add `--add-binary="deno.exe;."`.
On macOS/Linux use `:` instead of `;` in `--add-data` and `--add-binary`. The result is in `dist/`.

---

## Using the App

### Downloads

1. Paste one or more links (one per line). Videos, Shorts, `youtu.be` links and playlists all work.
2. Pick a **Format**: MP4, MKV, MP3 or M4A.
3. Pick a **Quality**: Best, 8K, 4K, 1440p, 1080p, 720p, 480p or 360p.
4. Click **Download** to start right away, or **Add to Queue** to start later with **Start All**.

Each item shows the highest resolution the video offers, live speed, size and time left, and after it finishes the resolution you actually got. Items can be paused, resumed, retried, opened in your file manager or removed.

If a video does not exist in the quality you chose, you get the closest one available, never a random low one.

### Settings

Everything here is saved automatically.

- **Download Location**: type a path or use Browse.
- **Theme** and **Language**: 6 themes, 10 languages.
- **Concurrent downloads**: 1 to 8 at a time. The rest wait in the queue.
- **Limit speed**: cap the download speed in MB/s.
- **Playlists**: turn a playlist link into one item per video.
- **Metadata**: embed title and chapters, plus cover art for audio files.
- **Browser cookies**: use your browser's YouTube login. Only needed for age restricted videos or when YouTube asks you to sign in.

### Diagnostics

Checks your internet connection, DNS, whether YouTube is reachable, and whether FFmpeg and a JavaScript runtime were found. The full app log shows here as well and can be copied.

---

## How It Works

1. **Link check**: pasted text is split into lines, real YouTube links are kept and duplicates are dropped.
2. **Info**: as soon as a link is added, yt-dlp reads the title, length and available formats in the background. Playlists are expanded here.
3. **Format choice**: YouTube stores HD video and audio as separate streams. The app sorts them by resolution (up to your limit), then frame rate, then codec. For MP4 it prefers H.264 + AAC at the same resolution so the file plays everywhere. 4K still uses VP9/AV1 because YouTube has no H.264 at that size.
4. **Download**: the info read in step 2 is reused, so nothing is fetched twice. Large files are downloaded in 10 MB chunks with automatic retries.
5. **Merge**: FFmpeg joins video and audio into one file without re-encoding, so it is quick and lossless. MP3 is converted from the best audio stream. M4A is copied as is.

### Why quality used to be low

Older versions told yt-dlp to use YouTube's `android` and `web` clients. YouTube now hides almost every format on those clients unless extra tokens are provided, which left only the 360p combined stream. Version 3 lets yt-dlp choose the clients and gives it a JavaScript runtime to solve YouTube's player challenge. That brings back the full range of formats up to 8K.

If you still only get low quality:

- Check the sidebar. **FFmpeg** and **JS runtime** should both say *ready*.
- Update yt-dlp: `pip install -U "yt-dlp[default]"`. YouTube changes often.

---

## Troubleshooting

**"FFmpeg: missing"**
Install FFmpeg (see the table above) or put `ffmpeg.exe` next to the app. Without it HD downloads are limited to 360p and MP3/M4A will not work.

**"JS runtime: missing"**
Install Deno and restart the app.

**"Sign in to confirm you're not a bot" / age restricted videos**
Set **Browser cookies** in Settings to the browser where you are logged into YouTube. Close that browser first if it is Chrome or Edge.

**Video unavailable**
Private, removed or region locked videos can not be downloaded.

**Slow downloads**
Run Diagnostics. Lower the concurrent downloads if your connection is shared, and make sure the speed limit is off.

---

## Built With

- [Python](https://www.python.org/)
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg](https://ffmpeg.org/)

## Project Layout

| File                 | What it does                                          |
| -------------------- | ----------------------------------------------------- |
| `main.py`            | The interface and download queue                      |
| `downloader_core.py` | Format selection, yt-dlp options, settings, URL check |
| `CHANGELOG.md`       | Version history                                       |

## Contributing

Found a bug or want a feature? Open an issue or a pull request.
