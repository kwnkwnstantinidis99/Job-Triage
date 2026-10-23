"""Paths and default settings. All user data lives in one directory (JT_DATA_DIR, default ./data)."""

from __future__ import annotations

import json
import os
from pathlib import Path

KEYWORDS = ["sustainability", "ESG", "climate", "LCA", "analyst", "energy", "finance", "reporting", "strategy", "modelling", "trading"]

# A few defaults; users override or extend them with companies.json in the data directory.
DEFAULT_COMPANIES: dict[str, str | list[str]] = {
    "Ørsted": "https://orsted.com/en/careers/vacancies-list",
    "Vestas": [f"https://careers.vestas.com/search/?q={k}&locationsearch=Denmark" for k in KEYWORDS],
    "Energinet": "https://www.energinet.dk/karriere/ledige-job/",
    "Ramboll": "https://www.ramboll.com/careers",
    "COWI": "https://www.cowi.com/careers/",
}


def data_dir() -> Path:
    d = Path(os.environ.get("JT_DATA_DIR", "data")).resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_companies(directory: Path | None = None) -> dict[str, str | list[str]]:
    """Defaults merged with <data dir>/companies.json (a falsy value there disables a default)."""
    directory = directory or data_dir()
    companies = dict(DEFAULT_COMPANIES)
    path = directory / "companies.json"
    if path.exists():
        try:
            for name, url in json.loads(path.read_text(encoding="utf-8")).items():
                if url:
                    companies[name] = url
                else:
                    companies.pop(name, None)
        except (OSError, ValueError) as exc:
            print("companies.json ignored:", exc)
    return companies
