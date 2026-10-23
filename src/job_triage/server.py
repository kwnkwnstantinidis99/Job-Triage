"""Password-protected local web UI (standard library only)."""

from __future__ import annotations

import base64
import hmac
import json
import os
import secrets
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import store
from .config import data_dir

STATIC = Path(__file__).resolve().parent / "static"
MAX_CV_BYTES = 60_000
MAX_SEEN_BYTES = 4_000


def load_password(directory: Path) -> str:
    """JT_PASSWORD wins; otherwise a random password is created once in <data dir>/.password."""
    if os.environ.get("JT_PASSWORD"):
        return os.environ["JT_PASSWORD"]
    pw_file = directory / ".password"
    if not pw_file.exists():
        pw_file.write_text(secrets.token_urlsafe(9))
        pw_file.chmod(0o600)
    return pw_file.read_text().strip()


class JobTriageServer(ThreadingHTTPServer):
    def __init__(self, address, directory: Path, password: str, scan_command: list[str] | None = None):
        super().__init__(address, Handler)
        self.directory = directory
        self.password = password
        self.scan_command = scan_command or [sys.executable, "-m", "job_triage.scanner"]
        self.state = {"running": False, "error": None}

    def run_scan(self) -> None:
        self.state.update(running=True, error=None)
        try:
            env = {**os.environ, "JT_DATA_DIR": str(self.directory)}
            r = subprocess.run(self.scan_command, capture_output=True, text=True, timeout=1500, env=env)
            if r.returncode != 0:
                self.state["error"] = (r.stderr or r.stdout)[-400:]
        except Exception as exc:
            self.state["error"] = str(exc)[:300]
        finally:
            self.state["running"] = False


class Handler(BaseHTTPRequestHandler):
    server: JobTriageServer

    def _authed(self) -> bool:
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            _, _, pw = base64.b64decode(header[6:]).decode().partition(":")
        except Exception:
            return False
        return hmac.compare_digest(pw, self.server.password)

    def _json(self, obj, code: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self, limit: int) -> dict:
        n = min(int(self.headers.get("Content-Length", "0") or 0), limit)
        return json.loads(self.rfile.read(n).decode("utf-8"))

    def _deny(self) -> None:
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Job Triage"')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        if not self._authed():
            return self._deny()
        d = self.server.directory
        path = self.path.split("?")[0]
        if path == "/api/cv":
            cv = d / "cv.txt"
            return self._json({"cv": cv.read_text(errors="ignore") if cv.exists() else ""})
        if path == "/api/scan":
            data = store.load_json(d / "scan.json", {"jobs": [], "companies": {}})
            data = store.merge_scan(data, d)
            data["running"], data["error"] = self.server.state["running"], self.server.state["error"]
            return self._json(data)
        if path in ("/", "/index.html"):
            body = (STATIC / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if not self._authed():
            return self._deny()
        d = self.server.directory
        if self.path == "/api/scan":
            if not self.server.state["running"]:
                threading.Thread(target=self.server.run_scan, daemon=True).start()
            return self._json({"started": True})
        if self.path == "/api/seen":
            try:
                body = self._read_json(MAX_SEEN_BYTES)
                url, want = str(body.get("url", "")), bool(body.get("seen", True))
                if not url.startswith("http"):
                    return self._json({"saved": False, "error": "bad url"}, 400)
                store.set_seen(d, url, want)
                return self._json({"saved": True, "seen": want})
            except Exception as exc:
                return self._json({"saved": False, "error": str(exc)[:100]}, 400)
        if self.path == "/api/cv":
            try:
                body = self._read_json(MAX_CV_BYTES)
                (d / "cv.txt").write_text(str(body.get("cv", ""))[:MAX_CV_BYTES], encoding="utf-8")
                return self._json({"saved": True})
            except Exception as exc:
                return self._json({"saved": False, "error": str(exc)[:100]}, 400)
        self.send_error(404)

    def log_message(self, *args) -> None:  # keep the console quiet
        pass


def main() -> None:
    directory = data_dir()
    port = int(os.environ.get("PORT", "8787"))
    server = JobTriageServer(("127.0.0.1", port), directory, load_password(directory))
    print(f"Job Triage on http://127.0.0.1:{port}  (username: anything, password in {directory / '.password'} or JT_PASSWORD)")
    server.serve_forever()


if __name__ == "__main__":
    main()
