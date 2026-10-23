"""Pure scoring and text-analysis logic: no I/O, no browser, easy to test.

A posting gets four sub-scores [skills, level, language, other] that sum to a 0-100 total.
"""

from __future__ import annotations

import re

JOBISH_HREF = re.compile(r"job|vacanc|position|career|stilling|opening|requisition|apply|posting", re.I)
NAV_TEXT = re.compile(
    r"^(careers?|jobs?|open positions|all jobs|apply( now)?|search|read more|see all.*|early careers|students?|graduates?|job alert.*|learn more|contact.*|login|sign in|home|about.*)$",
    re.I,
)
RELEVANT = re.compile(
    r"renewable|wind|solar|offshore|\bppa\b|offtake|power|green|circular|impact|regulat|polic|data|associate|advis|specialist|project|sustainab|esg|lca|life.?cycle|climate|carbon|ghg|emission|environment|csrd|taxonom|energy|analyst|financ|model|feasib|funding|grant|consult|report|bæredygtig|klima|miljø|energi|economist|strateg|engineer|environmental|epd|ecodesign|product|trading|market|forecast|\bbess\b|storage|batter|electric|balancing|commodit",
    re.I,
)
SENIOR = re.compile(r"\b(senior|sr\.?|head of|director|vp|vice president|principal|chief|lead|manager)\b|\bchef\b|\bleder\b", re.I)
ACADEMIC = re.compile(r"\b(full professor|professor|chair|postdoc|post-doc|lecturer|ph\.?d|doctoral|docent)\b", re.I)
FINANCE_TITLE = re.compile(
    r"valuation|\bm&a\b|corporate finance|\bcredit\b|\baudit\w*|\btax\b|accounting|controller|treasury|underwrit|banking|wealth|insurance|\bcfo\b|financial (analyst|controller|reporting|planning)|fp&a|quant(itative)?\b|trader|trading",
    re.I,
)
SUSTAIN_TITLE = re.compile(
    r"sustainab|\besg\b|\blca\b|climate|carbon|ghg|emission|environment|\bepd\b|circular|bæredygtig|klima|miljø", re.I
)
QUANT = re.compile(r"\bquant(itative)?\b", re.I)
PHD_REQ = re.compile(
    r"(ph\.?d|doctorate)[^.\n]{0,40}(required|must|essential|preferred|is a must)|(required|must|hold|holding)[^.\n]{0,40}(ph\.?d|doctorate)",
    re.I,
)
SENIOR_TEXT = re.compile(
    r"(extensive|significant|proven|substantial|solid|strong)\s+(professional\s+)?(work\s+)?experience|track record|senior-level|many years",
    re.I,
)
JUNIOR = re.compile(r"\b(junior|graduate|intern|internship|trainee|student|entry|associate)\b|studentermedhjælper", re.I)
DANISH = re.compile(r"\b(til|hos|og|med|medarbejder|konsulent|ingeniør|rådgiver|stilling|søger|for)\b", re.I)
SKILLS = [
    (r"sustainab|bæredygtig", 9),
    (r"\besg\b|csrd|taxonom|sfdr", 9),
    (r"\blca\b|life.?cycle", 10),
    (r"ghg|carbon|emission|climate|klima", 8),
    (r"project finance|feasib|funding|grant", 4),
    (r"energy|energi|renewable|wind|solar|offshore|power", 6),
    (r"\bppa\b|offtake|invest|fund|financ", 2),
    (r"analyst|model|economist", 5),
    (r"environment|miljø", 4),
    (r"consult|advis|report", 3),
    (
        r"environmental engineer|sustainability engineer|energy engineer|process engineer|product sustainab|eco.?design|\bepd\b|circular|cbam|ecolabel",
        10,
    ),
    (r"power market|electricity market|day.?ahead|intraday|balancing|price forecast|energy trad|\bbess\b|battery|storage", 4),
    (r"model+ing|forecast|optimi[sz]", 3),
]


def cap_total(sc, cap):
    """Hard ceiling on the total; the skills component absorbs the cut."""
    sc = list(sc)
    excess = sum(sc) - cap
    for i in (0, 1, 3, 2):  # skills first, then level, other, language
        if excess <= 0:
            break
        cut = min(sc[i], excess)
        sc[i] -= cut
        excess -= cut
    return sc


def score(title):
    t = title
    sk = min(40, sum(w for p, w in SKILLS if re.search(p, t, re.I)))
    ex = 15
    if SENIOR.search(t):
        ex -= 8
    if JUNIOR.search(t):
        ex += 8
    ex = max(0, min(25, ex + 2))
    if ACADEMIC.search(t):
        ex = min(ex, 2 if re.search(r"professor|chair", t, re.I) else 5)
    if QUANT.search(t):
        ex = max(0, ex - 8)
    lang = 8 if len(DANISH.findall(t)) >= 2 else 20
    other = 10
    sc = [sk, ex, lang, other]
    if re.search(r"professor|chair", t, re.I):
        sc = cap_total(sc, 35)
    elif ACADEMIC.search(t):
        sc = cap_total(sc, 55)
    elif FINANCE_TITLE.search(t) and not SUSTAIN_TITLE.search(t):
        sc = cap_total(sc, 45)
    elif QUANT.search(t) or SENIOR.search(t):
        sc = cap_total(sc, 65)
    return sc, sum(sc)


CORE_TERMS = [
    "sustainab",
    "esg",
    "lca",
    "life cycle",
    "ghg",
    "carbon",
    "emission",
    "climate",
    "csrd",
    "taxonomy",
    "sfdr",
    "scope 3",
    "iso 14",
    "simapro",
    "environment",
    "epd",
    "circular",
    "eco-design",
    "ecodesign",
    "energy efficiency",
    "decarbon",
]
DOMAIN_TERMS = [
    "sustainab",
    "esg",
    "lca",
    "life cycle",
    "ghg",
    "carbon",
    "emission",
    "climate",
    "csrd",
    "taxonomy",
    "sfdr",
    "scope 3",
    "iso 14",
    "simapro",
    "energy",
    "wind",
    "offshore",
    "solar",
    "heat pump",
    "ppa",
    "cfd",
    "offtake",
    "project finance",
    "feasibility",
    "business case",
    "npv",
    "irr",
    "dscr",
    "monte carlo",
    "environment",
    "epd",
    "circular",
    "decarbon",
    "energy efficiency",
    "python",
    "power bi",
    "matlab",
    "grant",
    "innovation fund",
    "green bond",
    "risk",
    "model",
    "analyst",
    "reporting",
    "data",
    "excel",
    "commodit",
]
MARKET_TERMS = [
    "power market",
    "electricity market",
    "day-ahead",
    "day ahead",
    "intraday",
    "balancing",
    "bess",
    "battery",
    "storage",
    "price forecast",
    "forecasting",
    "energy trading",
    "trading",
    "commodit",
    "optimis",
    "optimiz",
    "modelling",
    "modeling",
]
NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "ten": 10}
YEARS_RE = re.compile(
    r"(?:at least|minimum|min\.?|mindst)?\s*(\d{1,2}|one|two|three|four|five|six|seven|eight|ten)\s*\+?\s*(?:[-–]\s*\d{1,2}\s*)?(?:years?|års?)\b[^.\n]{0,70}?(?:experience|erfaring)",
    re.I,
)
DK_REQUIRED = re.compile(
    r"(fluent|proficien\w*|professional|excellent)[^.\n]{0,30}danish|danish[^.\n]{0,40}(required|a must|essential|fluent|necessary)|(flydende|godt|stærkt)\s+dansk|dansk[^.\n]{0,25}(i skrift|og tale|sprog)",
    re.I,
)
DK_ADVANTAGE = re.compile(r"danish[^.\n]{0,40}(advantage|plus|beneficial|desirable|nice to have)", re.I)
DK_WORDS = re.compile(r"\b(og|til|du|vi|med|der|som|er|på|vil|dig|din|har)\b", re.I)


def cv_active_terms(cv_text: str) -> list[str]:
    """Domain terms that appear in the CV, plus market terms, used to match postings against it."""
    txt = cv_text.lower()
    base = [t for t in DOMAIN_TERMS if t in txt] if txt else DOMAIN_TERMS[:20]
    return base + [t for t in MARKET_TERMS if t not in base]


def analyze_text(text, active):
    t = text.lower()
    matched = [x for x in active if x in t]
    core = [x for x in matched if x in CORE_TERMS]
    skills = min(40, 6 + 4 * len(core) + len(matched) - len(core))
    years = 0
    for m in YEARS_RE.finditer(text):
        v = m.group(1).lower()
        years = max(years, int(v) if v.isdigit() else NUM_WORDS.get(v, 0))
    exp = 20 if years == 0 else (16 if years <= 2 else (8 if years <= 4 else 3))
    if re.search(r"\b(graduate|junior|trainee|entry.level|recent graduate|newly graduated|nyuddannet)\b", t):
        exp = min(25, exp + 5)
    words = max(1, len(t.split()))
    danish_text = len(DK_WORDS.findall(text)) / words > 0.06
    if DK_REQUIRED.search(text) or danish_text:
        lang = 6
    elif DK_ADVANTAGE.search(text):
        lang = 14
    else:
        lang = 20
    notes = [f"CV match: {len(core)} sustainability + {len(matched) - len(core)} other terms"]
    if years:
        notes.append(f"asks {years}+ yrs")
    if danish_text:
        notes.append("Danish-language posting")
    elif DK_REQUIRED.search(text):
        notes.append("Danish required")
    return [skills, exp, lang, 10], " · ".join(notes)


def adjust_level(title, text, sc, note):
    """Full-text scoring defaults to 'entry level' when no '3+ years' phrase is found. Correct that with
    what the title and text say about seniority, academic level and PhD requirements."""
    skills, ex, lang, other = sc
    flags = []
    if SENIOR.search(title):
        ex = max(0, ex - 8)
        flags.append("senior title")
    if SENIOR_TEXT.search(text):
        ex = max(0, ex - 5)
        flags.append("asks for proven/extensive experience")
    if QUANT.search(title):
        ex = max(0, ex - 8)
        flags.append("quant role (usually PhD or years of experience)")
    if ACADEMIC.search(title):
        ex = min(ex, 2 if re.search(r"professor|chair", title, re.I) else 5)
        flags.append("academic role")
    elif PHD_REQ.search(text):
        ex = min(ex, 5)
        flags.append("PhD asked for")
    if re.search(r"\b(graduate|junior|trainee|entry.level|student|nyuddannet)\b", title, re.I):
        ex = min(25, ex + 5)
    sc = [skills, ex, lang, other]
    if re.search(r"professor|chair", title, re.I):
        sc = cap_total(sc, 35)
    elif ACADEMIC.search(title) or PHD_REQ.search(text):
        sc = cap_total(sc, 55)
    elif FINANCE_TITLE.search(title) and not SUSTAIN_TITLE.search(title):
        sc = cap_total(sc, 45)
        flags.append("finance-sector role")
    elif QUANT.search(title) or SENIOR.search(title):
        sc = cap_total(sc, 65)
    return sc, (note + (" · level: " + ", ".join(flags) if flags else ""))
