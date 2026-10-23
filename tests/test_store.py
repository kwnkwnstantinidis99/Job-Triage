from job_triage import store


def job(url, score=50, company="Acme", **kw):
    return {"t": "Sustainability Analyst", "c": company, "u": url, "s": [10, 10, 10, 10], "score": score, **kw}


def test_load_json_defaults_on_missing_or_broken(tmp_path):
    assert store.load_json(tmp_path / "nope.json", {"x": 1}) == {"x": 1}
    (tmp_path / "bad.json").write_text("{not json")
    assert store.load_json(tmp_path / "bad.json", []) == []


def test_set_seen_roundtrip(tmp_path):
    store.set_seen(tmp_path, "https://a.example/1", True)
    store.set_seen(tmp_path, "https://a.example/2", True)
    assert store.load_seen_urls(tmp_path) == {"https://a.example/1", "https://a.example/2"}
    store.set_seen(tmp_path, "https://a.example/1", False)
    assert store.load_seen_urls(tmp_path) == {"https://a.example/2"}


def test_set_seen_keeps_other_keys(tmp_path):
    store.save_json(tmp_path / "seen.json", {"urls": [], "applied_companies": ["Acme"]})
    store.set_seen(tmp_path, "https://a.example/1", True)
    assert store.load_json(tmp_path / "seen.json", {})["applied_companies"] == ["Acme"]


def test_previous_urls_only_from_finished_scans(tmp_path):
    p = tmp_path / "scan.json"
    store.save_json(p, {"jobs": [job("https://a.example/1")]})
    assert store.previous_urls(p) == set()
    store.save_json(p, {"jobs": [job("https://a.example/1")], "finished": "2026-10-23T10:00:00"})
    assert store.previous_urls(p) == {"https://a.example/1"}


def test_merge_scan_flags_seen_pipeline_and_sorts(tmp_path):
    store.save_json(tmp_path / "seen.json", {"urls": ["https://a.example/1"], "applied_companies": ["acme"]})
    data = {"jobs": [job("https://a.example/1", 40), job("https://b.example/2", 80, company="Other")]}
    out = store.merge_scan(data, tmp_path)
    assert [j["u"] for j in out["jobs"]] == ["https://b.example/2", "https://a.example/1"]
    seen_job = out["jobs"][1]
    assert seen_job["seen"] is True and seen_job["pipeline"] is True
    assert seen_job["note"].startswith("In your pipeline already")
    assert out["jobs"][0]["seen"] is False and "pipeline" not in out["jobs"][0]


def test_merge_scan_adds_extra_jobs_without_duplicates(tmp_path):
    store.save_json(
        tmp_path / "extra.json",
        {"updated": "today", "jobs": [job("https://a.example/1", 99), job("https://c.example/3", 70), {"u": "https://d.example/4"}]},
    )
    data = {"jobs": [job("https://a.example/1", 10)]}
    out = store.merge_scan(data, tmp_path)
    urls = [j["u"] for j in out["jobs"]]
    assert sorted(urls) == ["https://a.example/1", "https://c.example/3"]  # no dupe, no job without scores
    assert out["extra_updated"] == "today"
