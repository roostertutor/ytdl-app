# YouTube Downloader

A simple desktop app for downloading YouTube videos. Runs in your browser.

## Quick Start (for the person setting it up)

### 1. Install Python 3
- Download from https://python.org
- Windows: check "Add Python to PATH" during install

### 2. Install yt-dlp
Open a terminal/Command Prompt and run:
```
pip install yt-dlp
```

### 3. Run the app
- **Windows**: Double-click `start.bat`
- **Mac/Linux**: Run `./start.sh` in terminal (may need `chmod +x start.sh` first)

A browser window opens automatically. That's the app!

## For your mom (daily use)
1. Double-click `start.bat` (or `start.sh`)
2. Paste YouTube links into the box (one per line)
3. Click **Download**
4. Videos appear in `~/Downloads/YouTube/`

## Age-restricted / Private Videos
To download videos that require being logged in:

1. Install the **"Get cookies.txt LOCALLY"** extension in Chrome or Firefox
2. Log into YouTube
3. Click the extension icon on youtube.com → export cookies
4. Save the file (e.g. `C:\Users\YourName\youtube-cookies.txt`)
5. Open the **Settings** tab in the app and enter that file path

## Changing the download folder
Go to the **Settings** tab and update the Download Folder path.

## File naming
Files are saved as: `ChannelName - Video Title.mp4`
