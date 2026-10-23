import json

from job_triage.config import DEFAULT_COMPANIES, load_companies


def test_defaults_without_file(tmp_path):
    assert load_companies(tmp_path) == DEFAULT_COMPANIES


def test_file_overrides_adds_and_disables(tmp_path):
    (tmp_path / "companies.json").write_text(json.dumps({"New Co": "https://new.example", "Ørsted": None, "COWI": "https://x.example"}))
    out = load_companies(tmp_path)
    assert out["New Co"] == "https://new.example"
    assert "Ørsted" not in out
    assert out["COWI"] == "https://x.example"


def test_broken_file_is_ignored(tmp_path):
    (tmp_path / "companies.json").write_text("{oops")
    assert load_companies(tmp_path) == DEFAULT_COMPANIES
