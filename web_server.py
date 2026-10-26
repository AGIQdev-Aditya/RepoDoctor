"""RepoDoctor web console server: stdlib only, localhost only, works fully offline.

Run:  python web_server.py      (then open http://127.0.0.1:8502)
Wraps RepoDoctorEngine; does not modify engine.py / tools.py / ui.py.
"""
import json, os, webbrowser, subprocess, base64, zipfile, io
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from engine import RepoDoctorEngine

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("REPODOCTOR_PORT", 8502))
SKIP = {".git", "venv", ".venv", "__pycache__", "node_modules", ".pytest_cache"}
UPLOADS_DIR = ROOT / "uploaded_repos"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
engine = RepoDoctorEngine()

# Browser may only load things from this origin: a hard guarantee that the UI never phones home.
CSP = "default-src 'self' 'unsafe-inline' data:; connect-src 'self'"


def g(o, k):
    return o.get(k) if hasattr(o, "get") else getattr(o, k, None)


def handle_upload(body):
    """Handles folder, files, or zip uploaded via browser native file picker."""
    proj_name = body.get("name") or "custom_project"
    # sanitize folder name
    clean_name = "".join(c for c in proj_name if c.isalnum() or c in ("-", "_")).strip() or "custom_project"
    target_dir = UPLOADS_DIR / clean_name
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Zip file upload
    if body.get("zip_base64"):
        raw = base64.b64decode(body["zip_base64"])
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            z.extractall(target_dir)
        return {
            "status": "success",
            "repo_path": str(target_dir.resolve()),
            "name": clean_name,
            "message": f"Extracted ZIP archive to {clean_name}"
        }

    # 2. File list upload
    files = body.get("files", [])
    if not files:
        return {"status": "error", "message": "No files received in upload payload."}

    saved = 0
    for item in files:
        rel = item.get("path", "").lstrip("/")
        if not rel or ".." in rel:
            continue
        dest = (target_dir / rel).resolve()
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


def browse_folder():
    """Opens native OS file explorer dialog using zenity as desktop fallback."""
    try:
        parent_dir = str(ROOT.parent)
        cmd = ["zenity", "--file-selection", "--directory", "--title=Select Codebase to Audit", f"--filename={parent_dir}/"]
        env = os.environ.copy()
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)
        if proc.returncode == 0:
            chosen = proc.stdout.strip()
            if chosen and os.path.isdir(chosen):
                return {"status": "success", "path": chosen}
        return {"status": "cancelled", "path": ""}
    except Exception as e:
        return {"status": "error", "message": str(e), "path": ""}


def available_repos():
    """List current, sibling, and uploaded repositories for 1-click UI switching."""
    parent = ROOT.parent
    repos = [
        {"name": "RepoDoctor (Current Project)", "path": str(ROOT)},
        {"name": "workshop-agent (KT Baseline)", "path": str(parent / "workshop-agent")}
    ]
    try:
        for d in sorted(parent.iterdir()):
            if d.is_dir() and d not in (ROOT, parent / "workshop-agent") and not d.name.startswith((".", "venv")):
                repos.append({"name": d.name, "path": str(d)})
    except Exception:
        pass

    # Include uploaded repos
    try:
        for d in sorted(UPLOADS_DIR.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                repos.append({"name": f"📁 {d.name} (Uploaded)", "path": str(d.resolve())})
    except Exception:
        pass

    return {"current": str(ROOT), "repos": repos}


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


def py_files(repo):
    base, out = Path(repo).resolve(), []
    for r, d, f in os.walk(base):
        d[:] = [x for x in d if x not in SKIP and not x.startswith(".")]
        out += [str((Path(r) / n).relative_to(base)) for n in sorted(f) if n.endswith(".py")]
    return out[:400]


def read_file(repo, rel):
    base = Path(repo).resolve()
    p = (base / rel).resolve()
    if not p.is_relative_to(base):  # path-traversal guard
        raise PermissionError("Path escapes the repository.")
    return {"text": p.read_text(encoding="utf-8", errors="ignore")[:6000]}


POST = {
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


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, default=str).encode()
        self.send_response(code)
        for k, v in (("Content-Type", ctype + "; charset=utf-8"), ("Cache-Control", "no-store"),
                     ("X-Content-Type-Options", "nosniff"), ("Content-Security-Policy", CSP)):
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def guard(self):
        # Blocks DNS-rebinding and cross-site requests: this server can read local dirs and run tests.
        if self.headers.get("Host", "").split(":")[0] not in ("localhost", "127.0.0.1"):
            self.send(403, {"status": "error", "message": "Forbidden host."})
            return False
        return True

    def do_GET(self):
        if not self.guard():
            return
        u, q = urlparse(self.path), {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
        try:
            if u.path in ("/", "/index.html"):
                return self.send(200, (ROOT / "web" / "index.html").read_bytes(), "text/html")
            if u.path == "/api/status":
                return self.send(200, status())
            if u.path == "/api/browse":
                return self.send(200, browse_folder())
            if u.path == "/api/repos":
                return self.send(200, available_repos())
            if u.path == "/api/files":
                return self.send(200, py_files(q["repo"]))
            if u.path == "/api/file":
                return self.send(200, read_file(q["repo"], q["path"]))
            if u.path == "/api/report":
                return self.send(200, engine.export_markdown_report(q["repo"]).encode(), "text/markdown")
            self.send(404, {"status": "error", "message": "Not found."})
        except Exception as e:
            self.send(500, {"status": "error", "message": str(e)})

    def do_POST(self):
        if not self.guard():
            return
        if self.headers.get("X-RD") != "1":  # custom header forces a CORS preflight we never grant
            return self.send(403, {"status": "error", "message": "Missing header."})
        try:
            route = urlparse(self.path).path.removeprefix("/api/")
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            if route not in POST:
                return self.send(404, {"status": "error", "message": "Unknown endpoint."})
            self.send(200, POST[route](body))
        except KeyError as e:
            self.send(400, {"status": "error", "message": f"Missing field: {e}"})
        except Exception as e:
            self.send(500, {"status": "error", "message": str(e)})


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    url = f"http://127.0.0.1:{PORT}"
    print(f"🩺 RepoDoctor console → {url}  (Ctrl+C to stop)")
    try:
        webbrowser.open(url)
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
