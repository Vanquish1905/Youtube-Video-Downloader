# Vanquish Downloader

A powerful YouTube video downloader with a modern interface, built to handle everything from quick MP3 rips to full 8K video downloads.

---

## Quick Start

### Option 1: Download the Pre-Built Executable (Recommended)

Head over to the [Releases](../../releases) section and grab **v2** - it's a single `.exe` file that runs out of the box. No Python, no dependencies, no headaches.

1. Download `VanquishDownloader.exe` from the v2 release
2. Place it anywhere you like
3. Double-click and start downloading

That's it. The app bundles everything it needs, including FFmpeg.

### Option 2: Run from Source

If you prefer running the Python script directly or want to tinker with the code:

```bash
git clone https://github.com/yourusername/vanquish-downloader.git
cd vanquish-downloader

pip install -r requirements.txt

python main.py
```

**Requirements:**

- Python 3.8 or higher
- FFmpeg installed and available in your system PATH

To install FFmpeg:

- **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH, or use `winget install ffmpeg`
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg` or equivalent for your distro

### Option 3: Build Your Own Executable

Want to compile it yourself? Here's the PyInstaller command:

```bash
pip install pyinstaller

pyinstaller --onefile --windowed --icon=icon.ico --name="VanquishDownloader" --add-data="ffmpeg;ffmpeg" --hidden-import=customtkinter --hidden-import=yt_dlp --collect-all customtkinter main.py
```

Your executable will appear in the `dist` folder.

Note: On macOS/Linux, replace the `;` with `:` in the `--add-data` flag.

---

## How It Works

### The Download Process

When you paste a YouTube URL and hit download, here's what happens under the hood:

1. **URL Validation** - The app checks if your link is a valid YouTube URL (supports youtube.com, youtu.be, and various regional domains)

2. **Metadata Extraction** - yt-dlp reaches out to YouTube and pulls back video information: title, available formats, resolutions, duration, thumbnail, etc.

3. **Format Selection** - Based on your chosen quality (360p to 8K) and format (MP4, MKV, MP3), the app figures out which streams to grab. For video downloads, this usually means fetching separate video and audio streams since YouTube stores them separately at higher qualities.

4. **Parallel Downloading** - Instead of downloading one chunk at a time, the app splits the work across 8 concurrent connections. This dramatically speeds things up, especially on fast internet connections.

5. **Stream Merging** - Once both streams are downloaded, FFmpeg kicks in to merge the video and audio into a single file. For MP3 downloads, FFmpeg handles the audio extraction and conversion.

6. **File Delivery** - The final file lands in your chosen download folder, named after the video title.

### Bypassing YouTube's Detection

YouTube doesn't particularly like third-party downloaders and has various systems in place to block or throttle them. Here's how Vanquish gets around that:

**Client Impersonation**

The app doesn't just send requests as a generic downloader. It cycles through multiple "client" identities that YouTube recognizes as legitimate:

- `web` - Standard browser client
- `android` - Android app client
- `ios` - iOS app client
- `tv_embedded` - Smart TV embedded player
- `mweb` - Mobile web browser

Each client type has different capabilities and rate limits. When one gets throttled, the app can fall back to others.

**Browser Fingerprinting**

Every request includes headers that mimic a real browser - User-Agent strings, accept headers, cookies handling, and other fingerprint data that YouTube checks. The app uses the `extractor_args` to specify which client to impersonate.

**Chunked Downloads with Retries**

Instead of trying to grab the whole file at once (which YouTube monitors and throttles), downloads happen in 10MB chunks. If a chunk fails or gets rate-limited, the app backs off and retries up to 10 times with exponential delays.

**Fragment-Based Downloading**

For adaptive streams (DASH), videos are split into small fragments. The app downloads 8 fragments simultaneously, staying under YouTube's radar while maximizing speed. This parallel approach also means partial failures don't kill the whole download.

**No Authentication Required**

The app works without logging into a Google account, which means YouTube can't tie downloads to a user profile and apply stricter limits. Public videos are fully accessible this way.

---

## v1 vs v2 Comparison

### What v1 Had

The original version was functional but basic:

- Simple tkinter interface with a single input field
- One download at a time
- Basic quality selection (best available only)
- Minimal error feedback
- No progress indication beyond "downloading..."
- Fixed download location
- No format conversion options

### What v2 Brings

This rewrite is essentially a new application:

| Feature                  | v1               | v2                                        |
| ------------------------ | ---------------- | ----------------------------------------- |
| **Interface**            | Basic tkinter    | Modern CustomTkinter with dark theme      |
| **Themes**               | None             | 6 color schemes                           |
| **Resolution Options**   | Best only        | 360p, 480p, 720p, 1080p, 1440p, 4K, 8K    |
| **Output Formats**       | MP4 only         | MP4, MKV, MP3                             |
| **Concurrent Downloads** | 1                | Up to 5 simultaneous                      |
| **Batch Downloads**      | No               | Yes (paste multiple URLs)                 |
| **Download Queue**       | No               | Full queue management with pause/cancel   |
| **Progress Tracking**    | Basic            | Per-download progress bars with speed/ETA |
| **Download Location**    | Fixed            | User selectable                           |
| **Network Diagnostics**  | None             | Built-in connectivity testing             |
| **Error Handling**       | Basic exceptions | Detailed logging with timestamps          |
| **Speed Optimization**   | Default          | 8 concurrent fragments, optimized buffers |
| **YouTube Bypass**       | Basic            | Multi-client rotation, advanced headers   |

### Performance Difference

In real-world testing, v2 typically downloads 3-5x faster than v1 on the same connection. The combination of concurrent fragment downloading, larger buffers, and client rotation means you're not waiting around for YouTube's throttling to kick in.

### Why the Complete Rewrite?

v1 was written to solve a simple problem: download a video. But as YouTube's systems evolved and users wanted more features, patching the old codebase became unsustainable. v2 was built from scratch with extensibility in mind - adding new features, formats, or bypass methods is now straightforward.

---

## Using the App

### Main Download Tab

1. Paste one or more YouTube URLs (one per line for batch downloads)
2. Select your desired quality from the dropdown
3. Choose output format (MP4, MKV, or MP3)
4. Click "Add to Queue" or "Download Now"

### Queue Tab

View all pending and active downloads. Each item shows:

- Video title and thumbnail
- Current progress with speed and ETA
- Individual pause/cancel controls

### Settings Tab

- **Download Location** - Click browse to choose where files are saved
- **Concurrent Downloads** - Slider from 1-5 simultaneous downloads
- **Theme** - Pick from 6 color schemes

### Diagnostics Tab

Having issues? The diagnostics panel helps troubleshoot:

- Tests internet connectivity
- Checks DNS resolution
- Verifies YouTube is reachable
- Shows detailed logs with timestamps

---

## Troubleshooting

**"FFmpeg not found"**

The app needs FFmpeg for merging streams and format conversion. Either install it system-wide or place the ffmpeg executable in the same folder as the app.

**Downloads are slow**

Try the diagnostics tab to check your connection. If YouTube is throttling, the app will automatically retry with different client identities, but extremely slow speeds usually indicate network issues on your end.

**Video unavailable errors**

Some videos are region-locked, age-restricted, or private. The app can't bypass content restrictions that require authentication.

**App won't start (Windows)**

Make sure you're not running from a restricted folder. Try placing the app in your Documents or Downloads folder.

---

## Technical Details

Built with:

- **Python 3.8+** - Core language
- **CustomTkinter** - Modern UI framework
- **yt-dlp** - YouTube extraction engine
- **FFmpeg** - Media processing
- **Threading** - Concurrent download management

---

## License

MIT License - do whatever you want with it.

---

## Contributing

Found a bug or want to add a feature? PRs are welcome. Just keep the code clean and test your changes before submitting.
