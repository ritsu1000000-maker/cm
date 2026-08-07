#!/usr/bin/env python3
import base64
import html
import json
import os
import re
import shutil
import subprocess
import threading
import zipfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

HOST = "0.0.0.0"
PORT = 7682
WORKSPACE = Path("/workspace")
BOT_DIR = WORKSPACE / "bot"
CONFIG = WORKSPACE / "bot.config"
LOG_DIR = WORKSPACE / ".botbox" / "logs"
MAX_BODY = 200 * 1024 * 1024

WEB_USER = os.environ.get("WEB_USER", "admin")
WEB_PASSWORD = os.environ.get("WEB_PASSWORD", "")

BOT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

ENV_FILE = WORKSPACE / ".env"
ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def load_env_map():
    result = {}
    if not ENV_FILE.exists():
        return result
    for raw in ENV_FILE.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if ENV_KEY_RE.fullmatch(key):
            result[key] = value
    return result

def save_env_map(values):
    lines = [
        "# Discord Bot environment variables",
        "# Managed by Bot Upload UI / botctl",
    ]
    for key in sorted(values):
        value = str(values[key]).replace("\r", "").replace("\n", "\\n")
        lines.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

def set_env_value(key, value):
    if not ENV_KEY_RE.fullmatch(key or ""):
        raise ValueError("環境変数名が不正です。英字/数字/_ を使用してください。")
    values = load_env_map()
    values[key] = value
    save_env_map(values)

def delete_env_key(key):
    if not ENV_KEY_RE.fullmatch(key or ""):
        raise ValueError("環境変数名が不正です。")
    values = load_env_map()
    existed = key in values
    values.pop(key, None)
    save_env_map(values)
    return existed

def env_page(message=""):
    keys = sorted(load_env_map())
    rows = "".join(
        f"<tr><td><code>{html.escape(k)}</code></td>"
        f"<td>••••••••</td>"
        f"<td><form method='post' action='/env-delete' onsubmit=\"return confirm('削除しますか？')\">"
        f"<input type='hidden' name='key' value='{html.escape(k, quote=True)}'>"
        f"<button type='submit' class='danger'>削除</button></form></td></tr>"
        for k in keys
    )
    if not rows:
        rows = "<tr><td colspan='3'>環境変数はまだありません。</td></tr>"
    msg = f'<div class="msg">{html.escape(message)}</div>' if message else ""
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Environment Variables</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#0b0f17;color:#e8edf5;font-family:system-ui,-apple-system,sans-serif}}
.wrap{{max-width:860px;margin:40px auto;padding:20px}}
.card{{background:#121927;border:1px solid #273246;border-radius:16px;padding:24px}}
input{{width:100%;padding:11px;background:#0b111c;color:#eef;border:1px solid #344055;border-radius:8px}}
label{{display:block;margin:14px 0 6px;color:#b9c4d2}}
button,a.btn{{border:0;border-radius:8px;padding:10px 14px;background:#dfe8f7;color:#111827;font-weight:700;text-decoration:none;cursor:pointer}}
button.danger{{background:#ffd3d3}}
table{{width:100%;border-collapse:collapse;margin-top:20px}}
th,td{{text-align:left;border-bottom:1px solid #273246;padding:12px}}
.msg{{margin-bottom:16px;padding:12px;border-radius:10px;background:#182437}}
.actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}}
small{{color:#91a0b2}}
</style>
</head>
<body>
<div class="wrap"><div class="card">
<h1>環境変数</h1>
<p><small>値は画面に再表示しません。Bot再起動時に /workspace/.env から読み込まれます。</small></p>
{msg}

<form method="post" action="/env-set">
<label>変数名</label>
<input name="key" placeholder="DISCORD_TOKEN" required pattern="[A-Za-z_][A-Za-z0-9_]*">
<label>値</label>
<input name="value" type="password" autocomplete="new-password" required>
<div class="actions">
<button type="submit">追加 / 上書き</button>
<a class="btn" href="/">アップロード画面</a>
<a class="btn" href="http://127.0.0.1:7681">Virtual CMD</a>
</div>
</form>

<table>
<thead><tr><th>名前</th><th>値</th><th>操作</th></tr></thead>
<tbody>{rows}</tbody>
</table>

<form method="post" action="/env-restart" style="margin-top:20px">
<button type="submit">Botを再起動して反映</button>
</form>
</div></div>
</body></html>""".encode("utf-8")

def safe_relpath(name: str) -> Path:
    name = name.replace("\\", "/").lstrip("/")
    parts = []
    for part in name.split("/"):
        if not part or part in (".", ".."):
            continue
        part = re.sub(r'[\x00-\x1f<>:"|?*]', "_", part)
        if part:
            parts.append(part)
    if not parts:
        raise ValueError("invalid filename")
    return Path(*parts)

def safe_extract_zip(zpath: Path, dest: Path):
    root = dest.resolve()
    with zipfile.ZipFile(zpath, "r") as zf:
        for info in zf.infolist():
            rel = safe_relpath(info.filename)
            target = (dest / rel).resolve()
            if root not in target.parents and target != root:
                raise ValueError("unsafe zip path")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info, "r") as src, target.open("wb") as out:
                    shutil.copyfileobj(src, out)

def detect_command():
    package = BOT_DIR / "package.json"
    if package.exists():
        try:
            data = json.loads(package.read_text(encoding="utf-8"))
            scripts = data.get("scripts") or {}
            if "start" in scripts:
                return "npm start"
            main = data.get("main")
            if isinstance(main, str) and (BOT_DIR / main).exists():
                return f"node {main}"
        except Exception:
            pass
        for name in ("bot.js", "index.js", "main.js", "app.js"):
            if (BOT_DIR / name).exists():
                return f"node {name}"

    for name in ("bot.py", "main.py", "app.py"):
        if (BOT_DIR / name).exists():
            return f"python {name}"

    pyfiles = sorted(BOT_DIR.glob("*.py"))
    if len(pyfiles) == 1:
        return f"python {pyfiles[0].name}"

    jsfiles = sorted(BOT_DIR.glob("*.js"))
    if len(jsfiles) == 1:
        return f"node {jsfiles[0].name}"

    return ""

def write_config(command: str):
    CONFIG.write_text(
        "BOT_WORKDIR=/workspace/bot\n"
        f"BOT_COMMAND={command}\n",
        encoding="utf-8"
    )

def run_install():
    log = LOG_DIR / "install.log"
    with log.open("a", encoding="utf-8", errors="replace") as f:
        f.write("\n===== dependency install =====\n")
        if (BOT_DIR / "package.json").exists():
            subprocess.run(
                ["/bin/bash", "-lc", "npm install"],
                cwd=BOT_DIR,
                stdout=f,
                stderr=subprocess.STDOUT
            )
        if (BOT_DIR / "requirements.txt").exists():
            subprocess.run(
                ["/bin/bash", "-lc", "pip install -r requirements.txt"],
                cwd=BOT_DIR,
                stdout=f,
                stderr=subprocess.STDOUT
            )

def restart_bot():
    subprocess.run(
        [
            "/usr/bin/supervisorctl",
            "-c", "/opt/botbox/supervisord.conf",
            "restart", "discord-bot"
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def background_finish(auto_install: bool, auto_restart: bool):
    if auto_install:
        run_install()
    if auto_restart:
        restart_bot()

def page(message=""):
    msg = f'<div class="msg">{html.escape(message)}</div>' if message else ""
    return f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Discord Bot Upload</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#0b0f17;color:#e8edf5;font-family:system-ui,-apple-system,sans-serif}}
.wrap{{max-width:820px;margin:40px auto;padding:20px}}
.card{{background:#121927;border:1px solid #273246;border-radius:16px;padding:24px}}
h1{{margin-top:0}}
p{{color:#aab5c4}}
label{{display:block;margin:16px 0 7px}}
input[type=file]{{display:block;width:100%;padding:14px;background:#0b111c;border:1px solid #344055;border-radius:10px;color:#dce6f4}}
.row{{display:flex;gap:12px;flex-wrap:wrap;margin-top:18px}}
button,a.btn{{border:0;border-radius:10px;padding:12px 16px;background:#dfe8f7;color:#111827;font-weight:700;text-decoration:none;cursor:pointer}}
.checks{{display:grid;gap:8px;margin:16px 0}}
.msg{{margin-bottom:16px;padding:12px;border-radius:10px;background:#182437}}
code{{background:#0a0f18;padding:2px 6px;border-radius:5px}}
small{{color:#8895a8}}
</style>
</head>
<body>
<div class="wrap">
<div class="card">
<h1>Discord Bot Upload</h1>
<p>アップロード先: <code>/workspace/bot</code></p>
{msg}

<form method="post" action="/upload" enctype="multipart/form-data">
<label>Botファイル / ZIP</label>
<input type="file" name="files" multiple required>
<div class="checks">
<label><input type="checkbox" name="clear" value="1"> 既存のBotファイルを削除してから配置</label>
<label><input type="checkbox" name="extract" value="1" checked> ZIPを自動展開</label>
<label><input type="checkbox" name="detect" value="1" checked> 起動コマンドを自動検出</label>
<label><input type="checkbox" name="install" value="1" checked> npm / pip依存関係を自動インストール</label>
<label><input type="checkbox" name="restart" value="1" checked> 完了後Botを再起動</label>
</div>
<button type="submit">アップロードして反映</button>
</form>

<hr style="border:0;border-top:1px solid #273246;margin:24px 0">

<label>フォルダーごとアップロード</label>
<input id="folderInput" type="file" webkitdirectory multiple>
<div class="checks">
<label><input id="folderClear" type="checkbox"> 既存のBotファイルを削除してから配置</label>
<label><input id="folderDetect" type="checkbox" checked> 起動コマンドを自動検出</label>
<label><input id="folderInstall" type="checkbox" checked> 依存関係を自動インストール</label>
<label><input id="folderRestart" type="checkbox" checked> 完了後Botを再起動</label>
</div>
<button type="button" onclick="sendFolder()">フォルダーをアップロード</button>

<div class="row">
<a class="btn" href="http://127.0.0.1:7681">Virtual CMD</a>
<a class="btn" href="/status">Bot状態</a>
<a class="btn" href="/install-log">Install Log</a>
<a class="btn" href="/env">環境変数</a>
</div>
<p><small>Virtual CMDと同じログイン情報を使います。初期状態では127.0.0.1からだけアクセスできます。</small></p>
</div>
</div>

<script>
async function sendFolder(){{
  const files=document.getElementById('folderInput').files;
  if(!files.length) return alert('フォルダーを選択してください');
  const fd=new FormData();
  for(const f of files) fd.append('files',f,f.webkitRelativePath||f.name);
  fd.append('clear',document.getElementById('folderClear').checked?'1':'0');
  fd.append('detect',document.getElementById('folderDetect').checked?'1':'0');
  fd.append('install',document.getElementById('folderInstall').checked?'1':'0');
  fd.append('restart',document.getElementById('folderRestart').checked?'1':'0');
  const r=await fetch('/upload-folder',{{method:'POST',body:fd}});
  document.open();
  document.write(await r.text());
  document.close();
}}
</script>
</body>
</html>'''.encode("utf-8")

class Handler(BaseHTTPRequestHandler):
    server_version = "BotUpload/1.0"

    def log_message(self, fmt, *args):
        return

    def auth_ok(self):
        if not WEB_PASSWORD:
            return False
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            raw = base64.b64decode(header[6:]).decode("utf-8")
            user, password = raw.split(":", 1)
            return user == WEB_USER and password == WEB_PASSWORD
        except Exception:
            return False

    def require_auth(self):
        if self.auth_ok():
            return True
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Discord Bot Upload"')
        self.end_headers()
        return False

    def send_html(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if not self.require_auth():
            return
        if self.path == "/":
            return self.send_html(page())
        if self.path == "/env":
            return self.send_html(env_page())
        if self.path == "/status":
            p = subprocess.run(
                [
                    "/usr/bin/supervisorctl",
                    "-c", "/opt/botbox/supervisord.conf",
                    "status", "discord-bot"
                ],
                capture_output=True,
                text=True
            )
            cmd = detect_command()
            text = (p.stdout or p.stderr).strip()
            if cmd:
                text += f" / detected: {cmd}"
            return self.send_html(page(text))
        if self.path == "/install-log":
            log = LOG_DIR / "install.log"
            text = (
                log.read_text(encoding="utf-8", errors="replace")[-30000:]
                if log.exists()
                else "install.log はまだありません。"
            )
            body = (
                "<!doctype html><meta charset='utf-8'>"
                "<body style='background:#0b0f17;color:#e8edf5'>"
                f"<pre>{html.escape(text)}</pre><p><a href='/'>戻る</a></p>"
                "</body>"
            ).encode("utf-8")
            return self.send_html(body)
        self.send_error(404)

    def parse_multipart(self):
        ctype = self.headers.get("Content-Type", "")
        m = re.search(r'boundary=(?:"([^"]+)"|([^;]+))', ctype)
        if not m:
            raise ValueError("multipart boundary missing")
        boundary = (m.group(1) or m.group(2)).encode()
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY:
            raise ValueError("upload too large or empty")

        body = self.rfile.read(length)
        parts = body.split(b"--" + boundary)
        fields = {}
        files = []

        for part in parts:
            if not part or part in (b"--\r\n", b"--"):
                continue
            part = part.strip(b"\r\n")
            if b"\r\n\r\n" not in part:
                continue

            head, data = part.split(b"\r\n\r\n", 1)
            headers = head.decode("utf-8", errors="replace")
            data = data.rstrip(b"\r\n")
            name_m = re.search(r'name="([^"]+)"', headers)
            file_m = re.search(r'filename="([^"]*)"', headers)

            if not name_m:
                continue
            name = name_m.group(1)

            if file_m and file_m.group(1):
                files.append((file_m.group(1), data))
            else:
                fields[name] = data.decode("utf-8", errors="replace")

        return fields, files

    def parse_urlencoded(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > 1024 * 1024:
            raise ValueError("request too large")
        raw = self.rfile.read(length).decode("utf-8", errors="replace")
        from urllib.parse import parse_qs
        parsed = parse_qs(raw, keep_blank_values=True)
        return {k: (v[-1] if v else "") for k, v in parsed.items()}

    def do_POST(self):
        if not self.require_auth():
            return

        if self.path == "/env-set":
            try:
                data = self.parse_urlencoded()
                key = data.get("key", "").strip()
                value = data.get("value", "")
                set_env_value(key, value)
                return self.send_html(env_page(f"{key} を保存しました。Bot再起動後に反映されます。"))
            except Exception as e:
                return self.send_html(env_page(f"エラー: {e}"), 400)

        if self.path == "/env-delete":
            try:
                data = self.parse_urlencoded()
                key = data.get("key", "").strip()
                existed = delete_env_key(key)
                msg = f"{key} を削除しました。" if existed else f"{key} は存在しません。"
                return self.send_html(env_page(msg))
            except Exception as e:
                return self.send_html(env_page(f"エラー: {e}"), 400)

        if self.path == "/env-restart":
            restart_bot()
            return self.send_html(env_page("Botを再起動しました。環境変数を再読み込みします。"))

        if self.path not in ("/upload", "/upload-folder"):
            return self.send_error(404)

        try:
            fields, files = self.parse_multipart()
            if not files:
                raise ValueError("ファイルがありません")

            if fields.get("clear") == "1":
                for child in BOT_DIR.iterdir():
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()

            saved = []
            root = BOT_DIR.resolve()

            for filename, data in files:
                rel = safe_relpath(filename)
                target = (BOT_DIR / rel).resolve()
                if root not in target.parents and target != root:
                    raise ValueError("unsafe path")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                saved.append(target)

            if fields.get("extract") == "1":
                for p in list(saved):
                    if p.suffix.lower() == ".zip":
                        safe_extract_zip(p, BOT_DIR)
                        try:
                            p.unlink()
                        except Exception:
                            pass

            command = ""
            if fields.get("detect") == "1":
                command = detect_command()
                if command:
                    write_config(command)

            auto_install = fields.get("install") == "1"
            auto_restart = fields.get("restart") == "1"

            threading.Thread(
                target=background_finish,
                args=(auto_install, auto_restart),
                daemon=True
            ).start()

            msg = f"{len(files)}ファイルを配置しました。"
            if command:
                msg += f" 起動コマンド: {command}"
            if auto_install:
                msg += " 依存関係インストール開始。"
            if auto_restart:
                msg += " 完了後Botを再起動します。"

            self.send_html(page(msg))
        except Exception as e:
            self.send_html(page(f"エラー: {e}"), 400)

def main():
    if not WEB_PASSWORD:
        raise SystemExit("WEB_PASSWORD is required")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()

if __name__ == "__main__":
    main()
