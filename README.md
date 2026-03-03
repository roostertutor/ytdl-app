# YouTube Downloader

A simple desktop app for downloading YouTube videos. Runs in your browser.

---

## One-time Setup (done by the person setting it up)

### Step 1 — Install Python 3
- Download from **https://python.org**
- **Windows:** during install, check the box that says **"Add Python to PATH"**

### Step 2 — Install Deno (needed for YouTube video unlocking)

**Windows** — open PowerShell and run:
```
irm https://deno.land/install.ps1 | iex
```

**Mac** — open Terminal and run:
```
brew install deno
```

### Step 3 — Install yt-dlp (with all extras)
Open a terminal (or Command Prompt on Windows) and run:
```
pip install "yt-dlp[default]"
```

> This installs yt-dlp along with its challenge solver scripts, which are needed to unlock video formats on YouTube. Using just `pip install yt-dlp` will work but may cause warnings and missing formats.

### Step 4 — Install ffmpeg (needed for video/audio merging)
ffmpeg handles combining video and audio into a clean MP4 file.

**Windows** — open Command Prompt and run:
```
winget install ffmpeg
```
Then close and reopen Command Prompt so it takes effect.

**Mac** — open Terminal and run:
```
brew install ffmpeg
```

### Step 5 — Install Firefox and log into YouTube (Windows only)
On Windows, Chrome and Edge cannot be used with this app — both use an encryption method that blocks external tools from reading their cookies. Firefox stores cookies differently and works perfectly.

> **Your mom doesn't need to use Firefox day-to-day.** She can keep using Chrome or Edge as her normal browser. Firefox just needs to be installed and logged into YouTube once — the app uses it silently in the background.

1. Go to **https://firefox.com** and click **Download Firefox**
2. Run the installer (just click through, no special options needed)
3. Open Firefox
4. Go to **https://youtube.com** and sign in with your Google account
5. You can minimize or close Firefox — it doesn't need to stay open

### Step 6 — Run the app for the first time
- **Windows:** double-click `start.bat`
- **Mac:** run `./start.sh` in Terminal

A browser window opens automatically. Go to the **Settings** tab and confirm Firefox is selected.

---

## Daily Use (for your mom)

1. Double-click **`start.bat`** (Windows) or **`start.sh`** (Mac)
2. Paste one or more YouTube links into the box (one per line)
3. Click **Download**
4. Videos are saved to: `Downloads → YouTube`

That's it — no other steps needed.

---

## Video Name Format

Downloaded videos are saved as:
```
Channel Name - Video Title.mp4
```

---

## Troubleshooting

**Getting a login or 403 error?**
Make sure Firefox is selected in the Settings tab and that you're logged into YouTube in Firefox.

**Video says "private" or "unavailable"?**
The logged-in YouTube account must have permission to watch that video.

**App won't start?**
Make sure Python is installed and `pip install "yt-dlp[default]"` was run successfully.

**Getting warnings about MPEG-TS or malformed timestamps?**
Install ffmpeg (see Step 4 above). yt-dlp uses it automatically to fix these issues.

**Seeing warnings about Deno JS challenge solver?**
These are harmless — the app filters them out automatically. As long as the download completes, ignore them. If downloads are failing, make sure you installed with `pip install "yt-dlp[default]"` (not just `pip install yt-dlp`).