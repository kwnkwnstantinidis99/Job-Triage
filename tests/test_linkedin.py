import pytest

pytest.importorskip("bs4")

from job_triage import linkedin  # noqa: E402

HTML = """
<ul>
 <li><a class="base-card__full-link" href="https://linkedin.com/jobs/view/1?trk=x">Sustainability Analyst</a>
     <h4 class="base-search-card__subtitle">Acme</h4></li>
 <li><a class="base-card__full-link" href="https://linkedin.com/jobs/view/2">Hi</a></li>
 <li><span>no link</span></li>
</ul>
"""


def test_parse_cards_extracts_valid_and_strips_tracking():
    jobs = linkedin.parse_cards(HTML)
    assert len(jobs) == 1
    assert jobs[0]["c"] == "Acme" and jobs[0]["u"] == "https://linkedin.com/jobs/view/1"


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("JT_LINKEDIN", raising=False)
    assert linkedin.enabled() is False and linkedin.fetch_jobs() == []
