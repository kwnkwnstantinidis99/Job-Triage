# Job Triage

[![CI](https://github.com/kwnkwnstantinidis99/Job-Triage/actions/workflows/ci.yml/badge.svg)](https://github.com/kwnkwnstantinidis99/Job-Triage/actions/workflows/ci.yml)

A small tool I built for my own job search. It scans company career pages with a headless browser,
scores each posting against my CV (skills, seniority, language), and shows the ranked results in a
local web UI where I can mark postings as reviewed.

## How it works

```
career pages ──► scanner.py (Playwright) ──► scoring.py ──► scan.json ──► server.py ──► web UI
                      │                          ▲                            ▲
                      └─ opens the best matches, reads the full text,         │
                         re-scores against cv.txt (analyze_text, adjust_level) │
                                                        seen.json / extra.json ┘ (store.py)
```

| Module | Responsibility |
|---|---|
| `scoring.py` | Pure functions: title scoring, full-text analysis, level adjustment. No I/O, fully unit-tested. |
| `scanner.py` | Browser automation: pagination, "load more", cookie banners, link extraction, CV-aware enrichment. |
| `store.py` | JSON persistence: seen URLs, pipeline companies, extra postings, merge logic. |
| `server.py` | Standard-library HTTP server with Basic auth, JSON API and static UI. |
| `linkedin.py` | Optional guest-search source, off by default (`JT_LINKEDIN=1`). |
| `config.py` | Data directory and company list (defaults + `companies.json` overrides). |

Each posting gets four sub-scores that add up to its total: skills match (0-40), level (0-25), language (6-20) and a flat 10 for other.
Hard caps keep academic, finance-sector and senior roles from outranking realistic targets.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[scan,linkedin]"
playwright install chromium

export JT_DATA_DIR=./data          # where scan.json, seen.json, cv.txt, .password live
cp examples/companies.example.json data/companies.json   # optional: add your own companies
cp examples/cv.example.txt data/cv.txt                    # or paste your CV in the UI

job-triage            # starts the UI on http://127.0.0.1:8787 (password: JT_PASSWORD or data/.password)
job-triage-scan       # run a scan from the command line (the UI button does the same)
```

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check .
```

CI runs both on Python 3.10 and 3.12 for every push and pull request.

## Notes

- Personal data (CV, scan results, password) lives in `JT_DATA_DIR` and is git-ignored.
- Scraping: respect each site's terms and robots.txt. The scanner paginates politely and the LinkedIn source is opt-in.
- Matching is keyword-based and deliberately transparent, not a model: every score can be traced to a regex.

## Roadmap

- Source adapters per ATS (Workday, SuccessFactors) instead of generic link extraction
- Store results in SQLite instead of JSON files
- Dockerfile and a scheduled scan
