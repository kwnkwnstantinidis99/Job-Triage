"""Scan company career pages with a headless browser, then score what was found.

Needs: pip install "job-triage[scan]" && playwright install chromium
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from . import linkedin, store
from .config import data_dir, load_companies
from .scoring import JOBISH_HREF, NAV_TEXT, RELEVANT, adjust_level, analyze_text, cv_active_terms, score

MAX_PAGES = 12

EXTRACT_JS = """
() => {
  const GENERIC = /^(deadline.*|\\d{1,2}[./-]\\d{1,2}[./-]\\d{2,4}|go to job|view (vacancy|job)\\b.*|apply( now)?|read more|learn more|see (job|vacancy)|se job|læs mere|ansøg)$/i;
  return [...document.querySelectorAll('a[href]')].map(a => {
    let text = (a.innerText || '').trim().split('\\n')[0].trim();
    text = text.replace(/^(view (vacancy|job):\\s*)/i, '');
    const box = a.closest('li,article,tr,[class*=card],[class*=job],div');
    if (!text || GENERIC.test(text)) {
      let h = null, n = a;
      for (let i = 0; i < 5 && n && !h; i++, n = n.parentElement) h = n.querySelector('h1,h2,h3,h4,h5,[class*=title],[class*=Title]');
      text = h ? h.innerText.trim().split('\\n')[0] : text;
      if (!h || !text || GENERIC.test(text)) {
        const seg = decodeURIComponent((new URL(a.href).pathname.split('/').filter(Boolean).pop() || '')).replace(/\\.[a-z]{2,5}$/i,'');
        const slug = seg.replace(/[-_]+/g,' ').replace(/\\b\\d{4,}\\b/g,'').trim();
        if (slug.split(' ').length >= 2) text = slug.charAt(0).toUpperCase() + slug.slice(1);
      }
    }
    return {text, href: a.href, loc: ((box || {}).innerText || '').replace(/\\s+/g, ' ').slice(0, 200)};
  });
}
"""

NEXT_SELECTORS = [
    "a[rel=next]",
    "a[aria-label*='next' i]",
    "button[aria-label*='next' i]",
    "a[title*='next' i]",
    "li.next a",
    "a:has-text('Next')",
    "button:has-text('Next')",
    "a:has-text('Næste')",
    "a:has-text('›')",
    "button:has-text('›')",
]


def _collect(page):
    try:
        page.wait_for_load_state("networkidle", timeout=12000)
    except Exception:
        pass
    for _ in range(4):
        try:
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(400)
        except Exception:
            break
    for _ in range(5):
        try:
            page.click(
                "button:has-text('Load more'), button:has-text('Show more'), button:has-text('Se flere'), a:has-text('Load more')",
                timeout=1200,
            )
            page.wait_for_timeout(900)
        except Exception:
            break
    out = page.evaluate(EXTRACT_JS)
    for fr in page.frames:
        if fr == page.main_frame:
            continue
        try:
            out += fr.evaluate(EXTRACT_JS)
        except Exception:
            pass
    return out


def _go_next(page):
    for sel in NEXT_SELECTORS:
        try:
            loc = page.locator(sel).first
            if loc.count() == 0 or not loc.is_visible():
                continue
            if loc.get_attribute("disabled") is not None or (loc.get_attribute("aria-disabled") or "") == "true":
                continue
            loc.click(timeout=3000)
            page.wait_for_timeout(1200)
            return True
        except Exception:
            continue
    return False


def scan_company(page, name, url):
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    for sel in [
        "button:has-text('Accept all')",
        "button:has-text('Allow all')",
        "button:has-text('Accept')",
        "button:has-text('Tillad alle')",
    ]:
        try:
            page.click(sel, timeout=1200)
            break
        except Exception:
            pass
    raw, seen_href, pages = [], set(), 0
    for _ in range(MAX_PAGES):
        batch = _collect(page)
        new = [r for r in batch if r["href"] not in seen_href]
        pages += 1
        if not new:
            break
        for r in new:
            seen_href.add(r["href"])
        raw += new
        if "jobindex.dk" in url:
            break  # robots.txt disallows page= pagination: first page only
        if not _go_next(page):
            break
    seen, jobs, sample = set(), [], []
    for r in raw:
        t, h = r["text"], r["href"]
        if not (12 <= len(t) <= 140) or NAV_TEXT.match(t) or not JOBISH_HREF.search(h) or h in seen:
            continue
        if len(sample) < 6:
            sample.append(t)
        if not RELEVANT.search(t):
            continue
        seen.add(h)
        sc, total = score(t)
        jobs.append({"t": t, "c": name, "u": h, "s": sc, "score": total, "loc": r["loc"]})
    return len(raw), jobs, sample, pages


def enrich(ctx, jobs: list[dict], directory: Path, limit: int = 25, floor: int = 30) -> None:
    """Open the best title matches, read the full posting and re-score against the CV."""
    cv_file = directory / "cv.txt"
    active = cv_active_terms(cv_file.read_text(errors="ignore") if cv_file.exists() else "")
    seen_urls = store.load_seen_urls(directory)
    candidates = [j for j in sorted(jobs, key=lambda x: -x["score"]) if j["score"] >= floor and j["u"] not in seen_urls][:limit]
    for job in candidates:
        page = ctx.new_page()
        try:
            page.goto(job["u"], wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            text = page.inner_text("body")[:25000]
            if len(text) < 400:
                continue
            sc, note = analyze_text(text, active)
            sc, note = adjust_level(job["t"], text, sc, note)
            job["s"], job["score"], job["note"], job["full"] = sc, sum(sc), note, True
        except Exception:
            pass
        finally:
            page.close()


def run(only: list[str] | None = None) -> dict:
    from playwright.sync_api import sync_playwright

    directory = data_dir()
    out = directory / "scan.json"
    prev = store.previous_urls(out)
    result: dict = {"started": datetime.now().isoformat(timespec="seconds"), "companies": {}, "jobs": []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36", locale="en-GB"
        )
        for name, url in load_companies(directory).items():
            if only and name not in only:
                continue
            urls = url if isinstance(url, list) else [url]
            total_links, found, sample, errs, seen_u, pages_total = 0, [], [], [], set(), 0
            for u in urls:
                page = ctx.new_page()
                try:
                    n, jobs, smp, npg = scan_company(page, name, u)
                    total_links += n
                    sample += smp
                    pages_total += npg
                    for job in jobs:
                        if job["u"] not in seen_u:
                            seen_u.add(job["u"])
                            found.append(job)
                except Exception as exc:
                    errs.append(str(exc)[:120])
                finally:
                    page.close()
            if errs and len(errs) == len(urls):
                result["companies"][name] = {"ok": False, "error": errs[0], "url": urls[0]}
            else:
                result["companies"][name] = {
                    "ok": True,
                    "links_seen": total_links,
                    "matches": len(found),
                    "url": urls[0],
                    "pages": pages_total,
                    "sample": sample[:6],
                }
                result["jobs"] += found
            out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        enrich(ctx, result["jobs"], directory)
        browser.close()

    if linkedin.enabled():
        print("Fetching LinkedIn (guest)...")
        li_jobs = linkedin.fetch_jobs()
        for job in li_jobs:
            if RELEVANT.search(job["t"]):
                job["s"], job["score"] = score(job["t"])
                result["jobs"].append(job)
        result["companies"]["LinkedIn"] = {
            "ok": True,
            "links_seen": len(li_jobs),
            "matches": sum(1 for j in result["jobs"] if j.get("src") == "LI"),
            "url": "https://www.linkedin.com/jobs/",
            "pages": linkedin.MAX_PAGES,
            "sample": [j["t"] for j in li_jobs[:6]],
        }

    if prev:
        for job in result["jobs"]:
            job["new"] = job["u"] not in prev
    result["finished"] = datetime.now().isoformat(timespec="seconds")
    result["jobs"].sort(key=lambda j: -j["score"])
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> None:
    r = run((argv if argv is not None else sys.argv[1:]) or None)
    ok = sum(1 for c in r["companies"].values() if c["ok"])
    print(f"{len(r['jobs'])} matching jobs from {ok}/{len(r['companies'])} sites")


if __name__ == "__main__":
    main()
