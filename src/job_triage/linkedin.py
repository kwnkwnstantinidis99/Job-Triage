"""Optional LinkedIn guest-search source. Off by default: enable with JT_LINKEDIN=1.

Check the site's terms and robots.txt before using this; keep the delay between requests generous.
"""

from __future__ import annotations

import os
import random
import time

KEYWORDS = ["sustainability", "ESG", "LCA", "energy transition", "renewable energy"]
LOCATION = "Denmark"
DELAY = 3.5
MAX_PAGES = 2
BASE = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}


def enabled() -> bool:
    return os.environ.get("JT_LINKEDIN") == "1"


def parse_cards(html: str) -> list[dict]:
    """Extract {t, c, u, src, loc} from a guest-search result page."""
    from bs4 import BeautifulSoup

    jobs = []
    for li in BeautifulSoup(html, "html.parser").select("li"):
        a = li.select_one("a.base-card__full-link, a.job-card-list__title")
        if not a or not a.get("href"):
            continue
        title = (a.get_text(strip=True) or "").split("\n")[0].strip()
        if not 12 <= len(title) <= 140:
            continue
        company = li.select_one(".base-search-card__subtitle, .job-card-container__company-name")
        jobs.append(
            {
                "t": title,
                "c": company.get_text(strip=True) if company else "LinkedIn",
                "u": a["href"].split("?")[0],
                "src": "LI",
                "loc": LOCATION,
            }
        )
    return jobs


def fetch_jobs() -> list[dict]:
    if not enabled():
        return []
    import requests

    found: dict[str, dict] = {}
    for kw in KEYWORDS:
        for page in range(MAX_PAGES):
            params = {"keywords": kw, "location": LOCATION, "start": page * 25, "f_TPR": "r2592000"}
            try:
                r = requests.get(BASE, params=params, headers=HEADERS, timeout=15)
                if r.status_code != 200:
                    print(f"LinkedIn {kw} page {page}: status {r.status_code}")
                    break
                for job in parse_cards(r.text):
                    found.setdefault(job["u"], job)
                time.sleep(DELAY + random.uniform(0.3, 1.2))
            except Exception as exc:  # network errors should not kill a scan
                print(f"LinkedIn error ({kw}): {exc}")
                break
    return list(found.values())
