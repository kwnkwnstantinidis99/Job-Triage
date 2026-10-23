import base64
import json
import sys
import threading
import urllib.error
import urllib.request

import pytest

from job_triage import store
from job_triage.server import JobTriageServer, load_password

PW = "s3cret"


@pytest.fixture
def running(tmp_path):
    srv = JobTriageServer(("127.0.0.1", 0), tmp_path, PW, scan_command=[sys.executable, "-c", "pass"])
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", tmp_path
    srv.shutdown()
    srv.server_close()


def call(base, path, body=None, password=PW):
    headers = {}
    if password is not None:
        headers["Authorization"] = "Basic " + base64.b64encode(f"x:{password}".encode()).decode()
    data = json.dumps(body).encode() if body is not None else None
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_requires_password(running):
    base, _ = running
    assert call(base, "/api/scan", password=None)[0] == 401
    assert call(base, "/api/scan", password="wrong")[0] == 401


def test_index_served(running):
    base, _ = running
    status, body = call(base, "/")
    assert status == 200 and b"job triage" in body.lower()


def test_unknown_path_404(running):
    assert call(running[0], "/nope")[0] == 404


def test_scan_endpoint_merges_seen_flag(running):
    base, d = running
    store.save_json(d / "scan.json", {"jobs": [{"t": "x" * 15, "c": "A", "u": "https://a.example/1", "s": [1, 1, 1, 1], "score": 4}]})
    assert call(base, "/api/seen", {"url": "https://a.example/1", "seen": True})[0] == 200
    status, body = call(base, "/api/scan")
    data = json.loads(body)
    assert status == 200 and data["jobs"][0]["seen"] is True and data["running"] is False


def test_seen_rejects_bad_url(running):
    status, _ = call(running[0], "/api/seen", {"url": "javascript:alert(1)"})
    assert status == 400


def test_cv_roundtrip(running):
    base, d = running
    assert call(base, "/api/cv", {"cv": "LCA and python"})[0] == 200
    assert (d / "cv.txt").read_text() == "LCA and python"
    assert json.loads(call(base, "/api/cv")[1])["cv"] == "LCA and python"


def test_load_password_env_and_file(tmp_path, monkeypatch):
    monkeypatch.setenv("JT_PASSWORD", "fromenv")
    assert load_password(tmp_path) == "fromenv"
    monkeypatch.delenv("JT_PASSWORD")
    first = load_password(tmp_path)
    assert first and load_password(tmp_path) == first
