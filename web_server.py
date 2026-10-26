"""
RepoDoctor Web Console Server
Thread-Safe, Air-Gapped, Localhost-Only with Hardware Sandboxing & DNS-Rebinding Guard.

Run: python web_server.py (starts at http://127.0.0.1:8502)
"""

from __future__ import annotations

import base64
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import hardened
from engine import RepoDoctorEngine

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("REPODOCTOR_PORT", 8502))
SKIP = {".git", "venv", ".venv", "__pycache__", "node_modules", ".pytest_cache"}
UPLOADS_DIR = ROOT / "uploaded_repos"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Install security invariants & optimizations across all tools
hardened.install()

engine = RepoDoctorEngine()
AI_SEMAPHORE = threading.BoundedSemaphore(2)  # Cap parallel model tasks to protect GPU VRAM
SLOW_ROUTES = {"pr", "patch", "synth", "chat", "search"}

# Strict localhost-only Content Security Policy
CSP = "default-src 'self' 'unsafe-inline' data:; connect-src 'self'"
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "[::1]"}


def g(o, k):
    return o.get(k) if hasattr(o, "get") else getattr(o, k, None)


def status():
    base = {"root": str(ROOT), "default": engine.default_model}
    try:
        import ollama
        res = ollama.list()
        items = g(res, "models") or []
        names = [g(m, "model") or g(m, "name") for m in items]
        return {**base, "ollama": True, "models": [n for n in names if n]}
    except Exception as e:
        return {**base, "ollama": False, "models": [], "error": str(e)}


def py_files(repo: str) -> list[str]:
    base = hardened.safe_resolve_path(repo)
    out = []
    for r, d, f in os.walk(base):
        d[:] = [x for x in d if x not in SKIP and not x.startswith(".")]
        out += [str((Path(r) / n).relative_to(base)) for n in sorted(f) if n.endswith(".py")]
    return out[:500]


def read_file(repo: str, rel: str) -> dict[str, str]:
    base = hardened.safe_resolve_path(repo)
    p = hardened.safe_resolve_path(base, rel)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {rel}")
    with p.open("rb") as stream:
        data = stream.read(6001)
    return {
        "text": data[:6000].decode("utf-8", errors="replace"),
        "truncated": len(data) > 6000
    }


def list_directory(path_str: str) -> dict:
    p = Path(path_str or Path.home()).expanduser().resolve()
    if not p.is_dir():
        raise NotADirectoryError(str(p))
    dirs = []
    for c in sorted(p.iterdir(), key=lambda x: x.name.lower()):
        try:
            if c.is_dir() and not c.is_symlink() and not c.name.startswith(".") and c.name not in SKIP:
                dirs.append({"name": c.name, "full": str(c), "git": (c / ".git").exists()})
        except OSError:
            pass
    return {"path": str(p), "parent": str(p.parent) if p.parent != p else None, "dirs": dirs[:500]}


def pick_native_dialog() -> dict:
    for cmd in (
        ["zenity", "--file-selection", "--directory", "--title=Select Codebase to Audit"],
        ["kdialog", "--getexistingdirectory", str(Path.home())],
        ["yad", "--file", "--directory"]
    ):
        if shutil.which(cmd[0]):
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if r.returncode == 0 and r.stdout.strip():
                    chosen = r.stdout.strip()
                    if os.path.isdir(chosen):
                        return {"status": "success", "path": chosen}
            except Exception:
                pass
    return {"status": "error", "message": "No native dialog available."}


def locate_dropped_folder(name: str) -> list[str]:
    home = Path.home()
    hits, end = [], time.time() + 4
    for r, d, _ in os.walk(home):
        d[:] = [x for x in d if not x.startswith(".") and x not in SKIP and x not in {"snap", "Library", "AppData"}]
        if len(Path(r).relative_to(home).parts) >= 5:
            d[:] = []
        if name in d:
            hits.append(str(Path(r) / name))
        if len(hits) >= 8 or time.time() > end:
            break
    return hits


def available_repos() -> dict:
    parent = ROOT.parent
    repos = [
        {"name": "RepoDoctor (Current Project)", "path": str(ROOT)},
        {"name": "workshop-agent (KT Baseline)", "path": str(parent / "workshop-agent")}
    ]
    try:
        for d in sorted(parent.iterdir()):
            if d.is_dir() and d not in (ROOT, parent / "workshop-agent") and not d.name.startswith((".", "venv")):
                repos.append({"name": d.name, "path": str(d.resolve())})
    except Exception:
        pass

    try:
        for d in sorted(UPLOADS_DIR.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                repos.append({"name": f"📁 {d.name} (Uploaded)", "path": str(d.resolve())})
    except Exception:
        pass

    return {"current": str(ROOT), "repos": repos}


def handle_upload(body: dict) -> dict:
    """Save browser-uploaded folder files or extract uploaded ZIP with Zip-Slip protection."""
    proj_name = body.get("name") or "custom_project"
    clean_name = "".join(c for c in proj_name if c.isalnum() or c in ("-", "_")).strip() or "custom_project"
    target_dir = UPLOADS_DIR / clean_name
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Base64 ZIP Archive Upload
    if body.get("zip_base64"):
        raw = base64.b64decode(body["zip_base64"])
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            extracted = hardened.extract_zip_safely(z, target_dir)
        return {
            "status": "success",
            "repo_path": str(target_dir.resolve()),
            "name": clean_name,
            "message": f"Safely extracted {extracted} files from ZIP archive into {clean_name}"
        }

    # 2. File Array Upload
    files = body.get("files", [])
    if not files:
        return {"status": "error", "message": "No files provided in upload payload."}

    saved = 0
    for item in files:
        rel = item.get("path", "").lstrip("/")
        if not rel or ".." in rel:
            continue
        dest = (target_dir / rel).resolve(strict=False)
        if not dest.is_relative_to(target_dir):
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = item.get("content", "")
        dest.write_text(content, encoding="utf-8", errors="ignore")
        saved += 1

    return {
        "status": "success",
        "repo_path": str(target_dir.resolve()),
        "name": clean_name,
        "files_count": saved,
        "message": f"Successfully loaded {saved} file(s) into {clean_name}"
    }


POST_DISPATCH = {
    "diagnose": lambda b: engine.get_full_diagnosis(b["repo"]),
    "complexity": lambda b: engine.analyze_complexity(b["repo"]),
    "pr": lambda b: engine.synthesize_pr_review(b["repo"], b.get("model")),
    "patch": lambda b: engine.generate_vulnerability_fix(b["vulnerability"], b["snippet"], b["file"], b.get("model")),
    "synth": lambda b: engine.synthesize_unit_test(b["code"], b.get("model")),
    "run": lambda b: engine.run_sandbox_test(b["test"], b.get("code", "")),
    "search": lambda b: engine.search_code(b["repo"], b["query"], int(b.get("k", 4))),
    "chat": lambda b: engine.chat_with_agent(b["prompt"], b["repo"], b.get("model")),
    "upload": lambda b: handle_upload(b),
}


class RepoDoctorHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_json(self, code: int, body: any, ctype: str = "application/json") -> None:
        data = body if isinstance(body, bytes) else json.dumps(body, default=str).encode("utf-8")
        try:
            self.send_response(code)
            for k, v in (
                ("Content-Type", ctype + "; charset=utf-8"),
                ("Cache-Control", "no-store"),
                ("X-Content-Type-Options", "nosniff"),
                ("Content-Security-Policy", CSP)
            ):
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def verify_airgap_origin(self) -> bool:
        """Blocks DNS Rebinding and Cross-Origin Web Attacks."""
        host = self.headers.get("Host", "").split(":")[0].lower()
        if host not in ALLOWED_HOSTS:
            self.send_json(403, {"status": "error", "message": "Forbidden host (DNS rebinding guard)."})
            return False

        origin = self.headers.get("Origin")
        if origin:
            parsed = urlparse(origin)
            if (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
                self.send_json(403, {"status": "error", "message": "Cross-origin request blocked."})
                return False
        return True

    def do_GET(self) -> None:
        if not self.verify_airgap_origin():
            return
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}

        try:
            if u.path in ("/", "/index.html"):
                html_path = ROOT / "web" / "index.html"
                if not html_path.exists():
                    html_path = ROOT / "index.html"
                return self.send_json(200, html_path.read_bytes(), "text/html")
            if u.path == "/api/status":
                return self.send_json(200, status())
            if u.path == "/api/repos":
                return self.send_json(200, available_repos())
            if u.path == "/api/files":
                return self.send_json(200, py_files(q["repo"]))
            if u.path == "/api/file":
                return self.send_json(200, read_file(q["repo"], q["path"]))
            if u.path == "/api/ls":
                return self.send_json(200, list_directory(q.get("path", "")))
            if u.path == "/api/pick":
                return self.send_json(200, pick_native_dialog())
            if u.path == "/api/find":
                return self.send_json(200, locate_dropped_folder(q.get("name", "")))
            if u.path == "/api/report":
                return self.send_json(200, engine.export_markdown_report(q["repo"]).encode(), "text/markdown")
            self.send_json(404, {"status": "error", "message": "Not found."})
        except Exception as e:
            self.send_json(500, {"status": "error", "message": str(e)})

    def do_POST(self) -> None:
        if not self.verify_airgap_origin():
            return
        if self.headers.get("X-RD") != "1":
            return self.send_json(403, {"status": "error", "message": "Missing required security header."})

        try:
            route = urlparse(self.path).path.removeprefix("/api/")
            content_length = int(self.headers.get("Content-Length", 0))

            # 30MB limit for safe zip archives, 2MB for standard JSON
            max_bytes = 30 * 1024 * 1024 if route == "upload" else 2 * 1024 * 1024
            if not 0 <= content_length <= max_bytes:
                return self.send_json(413, {"status": "error", "message": "Request payload exceeds size limit."})

            raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            body = json.loads(raw_body.decode("utf-8", errors="replace"))

            if route not in POST_DISPATCH:
                return self.send_json(404, {"status": "error", "message": "Unknown endpoint."})

            if route in SLOW_ROUTES:
                if not AI_SEMAPHORE.acquire(timeout=3):
                    return self.send_json(429, {"status": "error", "message": "Gemma 4 is processing another request. Please retry shortly."})
                try:
                    return self.send_json(200, POST_DISPATCH[route](body))
                finally:
                    AI_SEMAPHORE.release()

            self.send_json(200, POST_DISPATCH[route](body))
        except KeyError as e:
            self.send_json(400, {"status": "error", "message": f"Missing required parameter: {e}"})
        except Exception as e:
            self.send_json(500, {"status": "error", "message": str(e)})


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), RepoDoctorHandler)
    srv.daemon_threads = True
    url = f"http://127.0.0.1:{PORT}"
    print(f"🩺 RepoDoctor Air-Gapped Console active on {url} (Ctrl+C to stop)")
    try:
        webbrowser.open(url)
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nShutdown complete.")


if __name__ == "__main__":
    main()
