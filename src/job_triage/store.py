"""JSON-file persistence for scan results, seen URLs, extra postings and the CV text."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def load_seen_urls(directory: Path) -> set[str]:
    return set(load_json(directory / "seen.json", {}).get("urls", []))


def set_seen(directory: Path, url: str, seen: bool) -> None:
    """Mark a posting URL as reviewed (or clear the mark)."""
    path = directory / "seen.json"
    data = load_json(path, {})
    urls = [u for u in data.get("urls", []) if u != url]
    if seen:
        urls.append(url)
    data["urls"] = urls
    save_json(path, data)


def previous_urls(scan_path: Path) -> set[str]:
    """URLs from the last completed scan, used to flag what is new."""
    data = load_json(scan_path, {})
    return {j["u"] for j in data.get("jobs", [])} if data.get("finished") else set()


def merge_scan(data: dict, directory: Path) -> dict:
    """Add extra.json postings and flag seen postings / companies already in the pipeline."""
    seen = load_json(directory / "seen.json", {})
    seen_urls = set(seen.get("urls", []))
    pipeline = [c.lower() for c in seen.get("applied_companies", []) if c]
    extra = load_json(directory / "extra.json", {})
    extra_jobs = extra.get("jobs", []) if isinstance(extra, dict) else extra
    have = {j.get("u") for j in data.get("jobs", [])}
    for job in extra_jobs:
        if job.get("u") and job["u"] not in have and job.get("s"):
            data.setdefault("jobs", []).append(job)
            have.add(job["u"])
    for job in data.get("jobs", []):
        job["seen"] = job.get("u") in seen_urls
        company = str(job.get("c", "")).lower()
        if any(a in company for a in pipeline):
            job["pipeline"] = True
            note = job.get("note") or ""
            if "In your pipeline already" not in note:
                job["note"] = ("In your pipeline already · " + note).rstrip(" ·")
    data["jobs"] = sorted(data.get("jobs", []), key=lambda j: -j.get("score", 0))
    data["extra_updated"] = extra.get("updated") if isinstance(extra, dict) else None
    return data
