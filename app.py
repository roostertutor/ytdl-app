#!/usr/bin/env python3
"""
YouTube Downloader - Simple desktop app for downloading YouTube videos.
Run this file to start the app. A browser window will open automatically.
"""

import os
import json
import threading
import subprocess
import webbrowser
import urllib.parse
import platform
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

# ── Config ──────────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).parent
CONFIG_FILE = APP_DIR / "config.json"
DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Downloads" / "YouTube")

def default_browser():
    """Return the best default browser for the current OS, derived from BROWSERS_BY_OS."""
    return BROWSERS_BY_OS.get(detect_os(), ["firefox"])[0]

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {
        "download_dir": DEFAULT_DOWNLOAD_DIR,
        "browser": default_browser(),
        "format": "best"
    }

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def detect_os():
    s = platform.system()
    if s == "Darwin": return "mac"
    if s == "Windows": return "windows"
    return "linux"

# Chrome is excluded from Windows — since Chrome 127 (mid-2024), Chrome uses
# app-bound cookie encryption on Windows that yt-dlp cannot decrypt.
# Firefox stores cookies in plain SQLite and works reliably on all platforms.
BROWSERS_BY_OS = {
    "mac":     ["safari", "firefox", "chrome", "edge"],
    "windows": ["firefox"],  # Chrome and Edge excluded — both use app-bound cookie encryption on Windows
    "linux":   ["chrome", "firefox"],
}

# ── Download logic ───────────────────────────────────────────────────────────
download_status = {}
download_lock = threading.Lock()

def run_download(url, cfg, download_id):
    with download_lock:
        download_status[download_id] = {"state": "downloading", "msg": "Starting..."}

    out_dir = cfg.get("download_dir", DEFAULT_DOWNLOAD_DIR)
    os.makedirs(out_dir, exist_ok=True)

    cmd = ["yt-dlp"]

    # Format — "best" uses no -f flag so yt-dlp picks whatever is available
    fmt = cfg.get("format", "best")
    if fmt == "audio":
        cmd += ["-x", "--audio-format", "mp3"]
    elif fmt == "720p":
        cmd += ["-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best"]
    # For "best": no -f flag at all, yt-dlp decides automatically
    if fmt != "audio":
        cmd += ["--merge-output-format", "mp4"]

    # Fetch the JavaScript challenge solver from GitHub (needed for YouTube's n-challenge).
    # This allows yt-dlp to unlock video formats that would otherwise be blocked.
    cmd += ["--remote-components", "ejs:github"]

    # Cookies — pulled automatically from the chosen browser, no extension needed.
    # NOTE: On Windows, use Firefox. Chrome cookies are encrypted since Chrome 127
    # and cannot be decrypted by yt-dlp on Windows.
    browser = cfg.get("browser") or default_browser()
    if browser and browser != "none":
        cmd += ["--cookies-from-browser", browser]

    # Output template: "Channel Name - Video Title.mp4"
    cmd += [
        "-o", os.path.join(out_dir, "%(uploader)s - %(title)s.%(ext)s"),
        "--no-playlist",
        "--progress",
        "--print", "YTDL_TITLE:%(title)s",  # emits a parseable title line before download starts
        url
    ]

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1
        )
        last_line = "Running..."
        last_error_line = ""  # track ERROR lines separately, ignoring WARNING lines
        all_lines = []        # full log for debug trace
        video_title = ""      # extracted from yt-dlp output when available
        for line in proc.stdout:
            line = line.strip()
            if line:
                last_line = line
                all_lines.append(line)
                # Extract title from the --print output line we requested
                if line.startswith("YTDL_TITLE:"):
                    video_title = line[len("YTDL_TITLE:"):].strip()
                    with download_lock:
                        download_status[download_id]["title"] = video_title
                # Only update progress in UI — skip WARNING noise and our own YTDL_TITLE marker
                if not line.startswith("WARNING:") and not line.startswith("YTDL_TITLE:"):
                    with download_lock:
                        download_status[download_id]["msg"] = line
                # Track the most recent actual ERROR line for failure reporting
                if line.startswith("ERROR:"):
                    last_error_line = line
        proc.wait()
        if proc.returncode == 0:
            with download_lock:
                download_status[download_id] = {
                    "state": "done",
                    "msg": "✅ Download complete!",
                    "title": video_title,
                }
        else:
            # Use the ERROR line if we captured one, otherwise fall back to last line
            failure = last_error_line or last_line
            hint = ""
            if "403" in failure or "cookie" in failure.lower():
                hint = " — Make sure you're logged into YouTube in the browser selected in Settings."
            elif "Requested format is not available" in failure:
                hint = " — Try a different quality option, or the video may be restricted."
            # Collect warnings and errors for the debug trace
            debug_lines = [l for l in all_lines if l.startswith("WARNING:") or l.startswith("ERROR:")]
            # If title wasn't extracted (error happened before yt-dlp printed it),
            # fall back to the video ID parsed from the URL
            display_title = video_title
            if not display_title:
                try:
                    import urllib.parse as _up
                    qs = _up.parse_qs(_up.urlparse(url).query)
                    display_title = qs.get("v", [""])[0] or url
                except Exception:
                    display_title = url
            with download_lock:
                download_status[download_id] = {
                    "state": "error",
                    "msg": f"❌ {failure}{hint}",
                    "title": display_title,
                    "trace": "\n".join(debug_lines[-10:]),  # last 10 warnings/errors
                }
    except FileNotFoundError:
        with download_lock:
            download_status[download_id] = {
                "state": "error",
                "msg": "❌ yt-dlp not found. Open a terminal and run: pip install yt-dlp"
            }
    except Exception as e:
        with download_lock:
            download_status[download_id] = {"state": "error", "msg": f"❌ {e}"}

# ── HTML ─────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>YouTube Downloader</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;600&family=Source+Sans+3:wght@300;400;600&display=swap');
  :root {
    --bg:#faf7f2; --card:#fff; --red:#cc2200; --red-soft:#f5e8e5;
    --text:#1a1a1a; --muted:#888; --border:#e8e2d9;
    --success:#2d7a4f; --success-bg:#eaf5ef;
    --error:#cc2200; --error-bg:#fdf0ee;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Source Sans 3',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;padding:32px 20px 60px}
  header{text-align:center;margin-bottom:36px}
  header h1{font-family:'Lora',serif;font-size:2.2rem;font-weight:600;color:var(--red);letter-spacing:-0.5px}
  header p{color:var(--muted);font-size:1rem;margin-top:6px;font-weight:300}
  .container{max-width:680px;margin:0 auto}
  .tabs{display:flex;border-bottom:2px solid var(--border);margin-bottom:28px}
  .tab-btn{padding:10px 22px;background:none;border:none;font-family:'Source Sans 3',sans-serif;font-size:.95rem;font-weight:600;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;transition:all .15s}
  .tab-btn.active{color:var(--red);border-bottom-color:var(--red)}
  .tab-panel{display:none}.tab-panel.active{display:block}
  .card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:28px;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.04)}
  label{display:block;font-weight:600;font-size:.9rem;margin-bottom:8px;color:#444}
  textarea,input[type=text]{width:100%;padding:12px 14px;font-family:'Source Sans 3',sans-serif;font-size:.95rem;border:1.5px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);transition:border-color .15s;resize:vertical}
  textarea:focus,input[type=text]:focus{outline:none;border-color:var(--red)}
  select{padding:10px 14px;font-family:'Source Sans 3',sans-serif;font-size:.95rem;border:1.5px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text);cursor:pointer}
  .btn{display:inline-flex;align-items:center;gap:8px;padding:12px 28px;background:var(--red);color:#fff;border:none;border-radius:8px;font-family:'Source Sans 3',sans-serif;font-size:1rem;font-weight:600;cursor:pointer;transition:background .15s,transform .1s}
  .btn:hover{background:#aa1a00;transform:translateY(-1px)}.btn:active{transform:translateY(0)}
  .btn-secondary{background:transparent;color:var(--red);border:1.5px solid var(--red)}
  .btn-secondary:hover{background:var(--red-soft)}
  .row{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-top:16px}
  .notice{padding:12px 16px;border-radius:8px;font-size:.88rem;margin-bottom:16px;line-height:1.5}
  .notice-info{background:#eef4ff;color:#1a4080;border:1px solid #c5d8f5}
  .notice-warn{background:#fffbea;color:#92600a;border:1px solid #f0d88a}
  .queue{margin-top:20px;display:flex;flex-direction:column;gap:10px}
  .queue-item{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px 16px;font-size:.88rem}
  .queue-item .url-text{font-family:monospace;color:var(--muted);font-size:.78rem;word-break:break-all;margin-bottom:6px}
  .queue-item .status-msg{font-size:.85rem;margin-top:4px;word-break:break-all}
  .state-pending{border-left:3px solid #ccc}
  .state-downloading{border-left:3px solid #e8a000}
  .state-done{border-left:3px solid var(--success);background:var(--success-bg)}
  .state-error{border-left:3px solid var(--error);background:var(--error-bg)}
  .badge{display:inline-block;padding:2px 8px;border-radius:99px;font-size:.75rem;font-weight:600;margin-bottom:4px}
  .badge-pending{background:#eee;color:#666}
  .badge-downloading{background:#fff4e0;color:#b37000}
  .badge-done{background:var(--success-bg);color:var(--success)}
  .badge-error{background:var(--error-bg);color:var(--error)}
  .browser-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:10px;margin-top:8px}
  .browser-option{padding:14px 10px;border:2px solid var(--border);border-radius:10px;text-align:center;cursor:pointer;font-size:.88rem;font-weight:600;transition:all .15s;background:var(--bg);color:#555}
  .browser-option:hover{border-color:var(--red);color:var(--red)}
  .browser-option.selected{border-color:var(--red);background:var(--red-soft);color:var(--red)}
  .browser-option .icon{font-size:1.6rem;display:block;margin-bottom:5px}
  h2{font-family:'Lora',serif;font-size:1.2rem;margin-bottom:16px}
  .hint{font-size:.82rem;color:var(--muted);margin-top:6px;line-height:1.5}
  .spacer{margin-top:20px}
  code{background:#f0ede8;padding:2px 6px;border-radius:4px;font-size:.85rem}
  .video-title{font-weight:600;font-size:.88rem;color:#1a1a2e;margin-bottom:4px;word-break:break-word}
  .trace-details{margin-top:8px}
  .trace-details summary{font-size:.78rem;color:#888;cursor:pointer;font-weight:600}
  .trace-details summary:hover{color:#cc2200}
  .trace-pre{margin-top:6px;background:#1a1a2e;color:#f0c090;font-size:.72rem;padding:10px 12px;border-radius:6px;overflow-x:auto;white-space:pre-wrap;word-break:break-all;line-height:1.5}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>▶ YouTube Downloader</h1>
    <p>Paste links, press download — that's it.</p>
  </header>

  <div class="tabs">
    <button class="tab-btn active" onclick="switchTab('download',this)">Download</button>
    <button class="tab-btn" onclick="switchTab('settings',this)">Settings</button>
  </div>

  <!-- DOWNLOAD TAB -->
  <div class="tab-panel active" id="tab-download">
    <div class="card">
      <div class="notice notice-info" id="browser-notice"></div>
      <label for="urls">Paste YouTube links (one per line)</label>
      <textarea id="urls" rows="6" placeholder="https://www.youtube.com/watch?v=...&#10;https://www.youtube.com/watch?v=..."></textarea>
      <div class="row">
        <button class="btn" onclick="startDownload()">⬇ Download</button>
        <button class="btn btn-secondary" onclick="clearAll()">Clear</button>
        <select id="format-quick">
          <option value="best">Best quality (MP4)</option>
          <option value="720p">720p (smaller file)</option>
          <option value="audio">Audio only (MP3)</option>
        </select>
      </div>
    </div>
    <div class="queue" id="queue"></div>
  </div>

  <!-- SETTINGS TAB -->
  <div class="tab-panel" id="tab-settings">
    <div class="card">
      <h2>Settings</h2>

      <label>Which browser are you logged into YouTube with?</label>
      <p class="hint" style="margin-bottom:12px">
        The app reads your login automatically — no extensions or file exports needed.
        Just make sure you're logged into YouTube in whichever browser you pick.
      </p>
      <div id="windows-chrome-warning" style="display:none" class="notice notice-warn">
        ⚠️ <strong>Chrome and Edge cannot be used on Windows</strong> — both use an encryption method that blocks external tools from reading cookies. Use <strong>Firefox</strong> instead (free to install at firefox.com).
      </div>
      <div class="browser-grid" id="browser-grid"></div>

      <div class="spacer">
        <label>Download Folder</label>
        <input type="text" id="cfg-dir">
        <p class="hint">Videos will be saved here.</p>
      </div>

      <div class="row" style="margin-top:20px">
        <button class="btn" onclick="saveSettings()">Save Settings</button>
        <span id="save-msg" style="color:var(--success);font-size:.9rem"></span>
      </div>
    </div>

    <div class="card">
      <h2>Troubleshooting</h2>
      <p style="font-size:.9rem;line-height:1.8;color:#444">
        <strong>Getting a 403 or login error?</strong> Make sure the browser selected above is the one you're logged into YouTube with.<br>
        <strong>On Windows, use Firefox</strong> — Chrome's cookies are encrypted and can't be read by this app.<br>
        <strong>Video says "private" or "unavailable"?</strong> Your account must have access to that video.<br>
        <strong>yt-dlp not found?</strong> Open a terminal and run: <code>pip install yt-dlp</code>
      </p>
    </div>
  </div>
</div>

<script>
const BROWSER_INFO = {
  chrome:  {icon:'🌐', label:'Chrome'},
  firefox: {icon:'🦊', label:'Firefox'},
  safari:  {icon:'🧭', label:'Safari'},
  edge:    {icon:'🔷', label:'Edge'},
  none:    {icon:'🚫', label:'No login'},
};

let cfg = {};
let pollInterval = null;
let jobs = {};
let currentOS = '';

async function init() {
  const r = await fetch('/api/config');
  const data = await r.json();
  cfg = data.config;
  currentOS = data.os;
  const browsers = [...data.browsers, 'none'];

  if (currentOS === 'windows') {
    document.getElementById('windows-chrome-warning').style.display = 'block';
  }

  const grid = document.getElementById('browser-grid');
  grid.innerHTML = browsers.map(b => {
    const info = BROWSER_INFO[b] || {icon:'🌐', label:b};
    return `<div class="browser-option ${cfg.browser===b?'selected':''}" onclick="selectBrowser('${b}',this)">
      <span class="icon">${info.icon}</span>${info.label}
    </div>`;
  }).join('');

  document.getElementById('cfg-dir').value = cfg.download_dir || '';
  updateNotice();
}

function selectBrowser(b, el) {
  cfg.browser = b;
  document.querySelectorAll('.browser-option').forEach(e => e.classList.remove('selected'));
  el.classList.add('selected');
  updateNotice();
}

function updateNotice() {
  const notice = document.getElementById('browser-notice');
  const b = cfg.browser;
  if (!b || b === 'none') {
    notice.className = 'notice notice-warn';
    notice.innerHTML = '⚠️ No browser selected — age-restricted or private videos may fail to download.';
  } else {
    const info = BROWSER_INFO[b] || {icon:'🌐', label:b};
    notice.className = 'notice notice-info';
    notice.innerHTML = `🔐 Using your <strong>${info.label}</strong> login automatically — no extra steps needed.`;
  }
}

function switchTab(name, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  btn.classList.add('active');
}

async function saveSettings() {
  cfg.download_dir = document.getElementById('cfg-dir').value.trim();
  await fetch('/api/config', {
    method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(cfg)
  });
  updateNotice();
  const msg = document.getElementById('save-msg');
  msg.textContent = '✓ Saved!';
  setTimeout(() => msg.textContent = '', 2000);
}

async function startDownload() {
  const raw = document.getElementById('urls').value.trim();
  if (!raw) return;
  const urls = raw.split('\n').map(u=>u.trim()).filter(Boolean);
  const fmt = document.getElementById('format-quick').value;

  const r = await fetch('/api/download', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body:JSON.stringify({urls, format:fmt})
  });
  const data = await r.json();
  data.ids.forEach((id,i) => {
    jobs[id] = {url:urls[i], state:'pending', title:''};
    renderItem(id, urls[i], '', 'pending', 'Waiting...');
  });
  document.getElementById('urls').value = '';
  startPolling();
}

function renderItem(id, url, title, state, msg, trace) {
  const queue = document.getElementById('queue');
  let el = document.getElementById('job-'+id);
  if (!el) { el = document.createElement('div'); el.id='job-'+id; queue.prepend(el); }
  el.className = 'queue-item state-'+state;
  const labels = {pending:'Waiting', downloading:'Downloading', done:'Done', error:'Error'};
  const titleHtml = title ? `<div class="video-title">${title}</div>` : '';
  const traceHtml = (trace && state === 'error')
    ? `<details class="trace-details"><summary>Show debug info</summary><pre class="trace-pre">${trace}</pre></details>`
    : '';
  el.innerHTML = `
    <div class="url-text">${url}</div>
    ${titleHtml}
    <span class="badge badge-${state}">${labels[state]||state}</span>
    <div class="status-msg">${msg}</div>
    ${traceHtml}`;
}

function startPolling() {
  if (pollInterval) return;
  pollInterval = setInterval(async () => {
    const active = Object.keys(jobs).filter(id=>['pending','downloading'].includes(jobs[id].state));
    if (!active.length) { clearInterval(pollInterval); pollInterval=null; return; }
    const r = await fetch('/api/status?ids='+active.join(','));
    const data = await r.json();
    for (const [id,info] of Object.entries(data)) {
      jobs[id].state = info.state;
      if (info.title) jobs[id].title = info.title;
      renderItem(id, jobs[id].url, jobs[id].title||'', info.state, info.msg, info.trace||'');
    }
  }, 1200);
}

function clearAll() {
  document.getElementById('urls').value='';
  document.getElementById('queue').innerHTML='';
  jobs={};
}

init();
</script>
</body>
</html>
"""

# ── HTTP Server ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass

    def send_json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            body = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/config":
            os_name = detect_os()
            browsers = BROWSERS_BY_OS.get(os_name, ["chrome", "firefox"])
            self.send_json({"config": load_config(), "browsers": browsers, "os": os_name})

        elif path == "/api/status":
            ids = query.get("ids", [""])[0].split(",")
            result = {}
            with download_lock:
                for id_ in ids:
                    if id_ in download_status:
                        result[id_] = download_status[id_]
            self.send_json(result)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/config":
            cfg = load_config()
            cfg.update(body)
            save_config(cfg)
            self.send_json({"ok": True})

        elif parsed.path == "/api/download":
            import time, hashlib
            cfg = load_config()
            if body.get("format"):
                cfg["format"] = body["format"]
            urls = body.get("urls", [])
            ids = []
            for url in urls:
                id_ = hashlib.md5((url + str(time.time())).encode()).hexdigest()[:8]
                ids.append(id_)
                with download_lock:
                    download_status[id_] = {"state": "pending", "msg": "Queued..."}
                t = threading.Thread(target=run_download, args=(url, cfg, id_), daemon=True)
                t.start()
            self.send_json({"ids": ids})

        else:
            self.send_response(404)
            self.end_headers()

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    port = 8765
    server = HTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"\n✅ YouTube Downloader running at {url}")
    print("   A browser window will open automatically.")
    print("   Close this terminal window to stop the app.\n")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()