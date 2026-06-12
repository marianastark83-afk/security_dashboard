"""
Keyword-based classifier for news articles.

Pipeline:
  1. detect_countries()  — which of the 5 monitored countries appear in text
  2. detect_threat_type() — map keywords → dashboard threat category
  3. detect_severity()   — estimate Critical / High / Medium
  4. detect_region()     — sub-national location within the country
  5. score_confidence()  — 0.0–1.0 composite reliability score
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

# ── COUNTRY PATTERNS ────────────────────────────────────────────────────────
# Include patterns fire on a match; exclude patterns veto that match.
# Order matters for the exclude list: check "South Sudan" before "Sudan".

_COUNTRY_INCLUDE_RAW = {
    "Sudan": [
        r"\bsudan(?:ese)?\b", r"\bkhartoum\b", r"\bomdurman\b",
        r"\brsf\b", r"\bsaf\b", r"\bdarfur\b", r"\bjebel awliya\b",
        r"\bblue nile state\b", r"\bnorth kordofan\b", r"\bkassala\b",
        r"\brapid support forces\b", r"\bport sudan\b", r"\bgedaref\b",
        r"\bel fasher\b", r"\bnyala\b", r"\bel geneina\b",
    ],
    "South Sudan": [
        r"\bsouth sudan(?:ese)?\b", r"\bjuba\b", r"\bjonglei\b",
        r"\bsspdf\b", r"\brjmec\b", r"\bupper nile\b", r"\bwarrap\b",
        r"\blakes state\b", r"\briek\s+machar\b", r"\bmachar\b",
        r"\bunity state\b", r"\bbentiu\b", r"\bmalakal\b",
    ],
    "DRC": [
        r"\bdr\.?\s*congo\b", r"\bdemocratic republic.{0,15}congo\b",
        r"\bdrc\b", r"\bm23\b", r"\bcodeco\b", r"\bituri\b",
        r"\bgoma\b", r"\bnorth kivu\b", r"\bsouth kivu\b",
        r"\bfardc\b", r"\bmonusco\b", r"\bkinshasa\b", r"\bbukavu\b",
        r"\bbeni\b", r"\bwazalendo\b", r"\brutshuru\b",
        r"\bcongolese\b", r"\bdjugu\b", r"\bruzizi\b", r"\bbassa\b",
        r"\bbunia\b",
    ],
    "Somalia": [
        r"\bsomal(?:ia|i)\b", r"\bmogadishu\b", r"\bal-?shabaab\b",
        r"\bpuntland\b", r"\bjubaland\b", r"\batmis\b", r"\baussom\b",
        r"\bmiddle shabelle\b", r"\blower shabelle\b",
        r"\bhiraan\b", r"\bgedo\b", r"\bkismayo\b", r"\bgarowe\b",
        r"\bbeledweyne\b",
    ],
    "Ethiopia": [
        r"\bethiopi(?:a|an)\b", r"\btigray\b", r"\btplf\b",
        r"\baddis ababa\b", r"\bamhara\b", r"\boromia\b",
        r"\bola\b", r"\bendf\b", r"\btdf\b",
        r"\bpretoria\s+(?:peace\s+)?agreement\b",
        r"\bafar\b", r"\bshire\s+district\b", r"\baxum\b",
        r"\bwag hamra\b", r"\babiy ahmed\b", r"\bnirak\b",
    ],
}

# These patterns veto a country match even if include patterns fired.
_COUNTRY_EXCLUDE_RAW = {
    "Sudan":      [r"\bsouth sudan\b"],   # "South Sudan" must not trigger "Sudan"
    "South Sudan": [],
    "DRC":        [],
    "Somalia":    [],
    "Ethiopia":   [],
}

# ── THREAT TYPE RULES (evaluated in order — first match wins) ───────────────
_THREAT_RULES_RAW = [
    ("Drone Attack", [
        r"\bdrone\s+(?:strike|attack|bomb)\b",
        r"\buav\s+(?:strike|attack)\b",
        r"\bunmanned\s+aerial\b",
        r"\bdrone\s+campaign\b",
    ]),
    ("Terrorism", [
        r"\bal-?shabaab\b",
        r"\bimprovis\w+\s+explosive\b", r"\bied\b",
        r"\bsuicide\s+bomb\b", r"\bcar\s+bomb\b", r"\bvbied\b",
        r"\bterror(?:ist)?\s+attack\b",
    ]),
    ("Natural Hazard", [
        r"\bflood(?:ing)?\b", r"\bdrought\b", r"\bfamine\b",
        r"\bacute\s+hunger\b", r"\bfood\s+insecurity\b",
        r"\bstarvat\w+\b", r"\bcholera\b", r"\bmalnutrition\b",
        r"\bdisease\s+outbreak\b",
    ]),
    ("Civil Unrest", [
        r"\bprotest(?:s|ers)?\b", r"\bdemonstrat\w+\b", r"\briot(?:s|ers)?\b",
        r"\bhumanitarian\s+crisis\b", r"\bmass\s+displace\w+\b",
    ]),
    ("Political Instability", [
        r"\bpeace\s+(?:deal|agreement|talks|process)\b",
        r"\bcoup\b", r"\bceasefire\b",
        r"\bdiplomatic\s+(?:crisis|tensions?|row)\b",
        r"\bsanctions?\b", r"\bpolitical\s+(?:crisis|instability)\b",
        r"\bpower.sharing\b",
    ]),
    # Armed Conflict is the catch-all and must be last.
    ("Armed Conflict", [
        r"\b(?:kill|killed|kills)\b", r"\battack(?:s|ed)?\b",
        r"\bfight(?:ing)?\b", r"\bbattle\b", r"\boffensive\b",
        r"\bclash(?:es)?\b", r"\bairstrike\b", r"\btroops\b",
        r"\bmilitary\s+(?:operation|offensive|strike)\b",
        r"\bmilitia\b", r"\barmed\s+group\b", r"\bartillery\b",
        r"\bseize(?:d)?\b", r"\bretake\b", r"\bcapture(?:d)?\b",
        r"\bgunfire\b", r"\bshell(?:ing)?\b",
    ]),
]

# ── REGION LOOKUP ────────────────────────────────────────────────────────────
_REGION_RULES_RAW = {
    "Sudan": [
        ("Khartoum",        [r"\bkhartoum\b", r"\bomdurman\b"]),
        ("Darfur",          [r"\bdarfur\b", r"\bel fasher\b", r"\bnyala\b", r"\bel geneina\b"]),
        ("Blue Nile State", [r"\bblue nile\b"]),
        ("Jebel Awliya",    [r"\bjebel awliya\b"]),
        ("Port Sudan",      [r"\bport sudan\b"]),
        ("Kassala",         [r"\bkassala\b"]),
        ("North Kordofan",  [r"\bkordofan\b", r"\bel obeid\b"]),
        ("Gedaref",         [r"\bgedaref\b"]),
    ],
    "South Sudan": [
        ("Jonglei State",  [r"\bjonglei\b"]),
        ("Juba",           [r"\bjuba\b"]),
        ("Upper Nile",     [r"\bupper nile\b", r"\bmalakal\b"]),
        ("Unity State",    [r"\bunity state\b", r"\bbentiu\b"]),
        ("Warrap",         [r"\bwarrap\b", r"\bkuajok\b"]),
        ("Lakes State",    [r"\blakes state\b"]),
    ],
    "DRC": [
        ("Ituri Province", [r"\bituri\b", r"\bbunia\b", r"\bdjugu\b", r"\bbassa\b"]),
        ("North Kivu",     [r"\bnorth kivu\b", r"\bgoma\b", r"\brutshuru\b", r"\bnyamilima\b"]),
        ("South Kivu",     [r"\bsouth kivu\b", r"\bbukavu\b", r"\bruzizi\b"]),
        ("Eastern DRC",    [r"\beastern\s+(?:congo|drc)\b", r"\beast\s+congo\b"]),
        ("Kinshasa",       [r"\bkinshasa\b"]),
    ],
    "Somalia": [
        ("Mogadishu",         [r"\bmogadishu\b"]),
        ("Middle Shabelle",   [r"\bmiddle shabelle\b"]),
        ("Lower Shabelle",    [r"\blower shabelle\b"]),
        ("Mogadishu–Afgoye",  [r"\bafgoye\b"]),
        ("Jubbaland",         [r"\bjubaland\b", r"\bkismayo\b"]),
        ("Central Somalia",   [r"\bcentral somalia\b", r"\bhiraan\b", r"\bbeledweyne\b"]),
        ("Puntland",          [r"\bpuntland\b", r"\bgarowe\b"]),
    ],
    "Ethiopia": [
        ("Tigray Region",      [r"\btigray\b", r"\bmekelle\b", r"\bshire\b", r"\baxum\b"]),
        ("Wag Hamra Zone, Amhara", [r"\bwag hamra\b", r"\bnirak\b"]),
        ("Amhara Region",      [r"\bamhara\b"]),
        ("Oromia",             [r"\boromia\b"]),
        ("Addis Ababa",        [r"\baddis ababa\b"]),
        ("Afar Region",        [r"\bafar\b"]),
        ("Tigray / Amhara Border", [r"\btigray.amhara border\b", r"\bshire district\b"]),
    ],
}

# ── SEVERITY PATTERNS ────────────────────────────────────────────────────────
# Critical: direct mass-casualty indicators, city/territory seizure, explicit
# fatality descriptors, and high-intensity combat language.
_CRITICAL_RAW = [
    # Numeric or quantified casualties
    r"\b\d+\s+(?:people\s+)?(?:killed|dead|deaths)\b",
    r"\b(?:several|dozens?\s+of|multiple|scores\s+of)\s+(?:soldiers?|troops?|fighters?|civilians?|people|persons?)\s+(?:killed|dead|died)\b",
    # Fatality / severity descriptors
    r"\bdeadly\b",
    r"\bfatalit\w+\b",
    r"\bfatal\s+(?:attack|clash|shooting|incident|assault)\b",
    # Classic war-crimes / mass-violence
    r"\bmassacre\b", r"\bgenocide\b", r"\bwar\s+crime\b",
    r"\bbombing\b", r"\bcivilians?\s+killed\b",
    r"\batrocit\w+\b", r"\bblockade\b",
    r"\bhospital\s+(?:attacked|bombed|struck)\b",
    r"\bcatastroph\w+\b",
    # Combat intensity — indicates ongoing significant violence
    r"\bheavy\s+(?:casualties?|fighting|clashes?|losses?|shelling|bombardment)\b",
    r"\bopen(?:ed)?\s+fire\b",
    r"\bgunfight\b", r"\bfirefight\b",
    # Territorial seizure — strategic escalation
    r"\bseized?\s+(?:control\s+of\s+)?(?:city|town|village|district|area|base|airport|compound)\b",
    r"\boverrun\b",
    r"\bunder\s+(?:heavy\s+)?(?:attack|siege|bombardment)\b",
]
_HIGH_RAW = [
    r"\battack(?:s|ed)?\b", r"\boffensive\b",
    r"\b(?:thousands|hundreds)\s+(?:displaced|fleeing|killed)\b",
    r"\bfight(?:ing)?\b", r"\bclash(?:es)?\b",
    r"\bartillery\b", r"\bescalat\w+\b",
    r"\bcivilian\s+casualt\w+\b",
    # Additional High-level indicators
    r"\braid\b", r"\bshoot(?:ing|out)\b",
    r"\bconfront(?:ation)?\b", r"\bskirmish\w*\b",
    r"\bguns?\s+(?:fire|battle)\b",
    r"\bkill(?:ed|ing)\b",           # any killing mention (without numeric)
    r"\bcasualt\w+\b",               # casualties (generic)
    r"\bwound(?:ed|ing)\b",          # wounded
    r"\binjur\w+\b",                 # injured
]


# ── COMPILE EVERYTHING ───────────────────────────────────────────────────────
def _c(patterns: list) -> list:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


_INC   = {c: _c(ps) for c, ps in _COUNTRY_INCLUDE_RAW.items()}
_EXC   = {c: _c(ps) for c, ps in _COUNTRY_EXCLUDE_RAW.items()}
_THRTS = [(t, _c(ps)) for t, ps in _THREAT_RULES_RAW]
_REGS  = {c: [(r, _c(ps)) for r, ps in rps] for c, rps in _REGION_RULES_RAW.items()}
_CRIT  = _c(_CRITICAL_RAW)
_HIGH  = _c(_HIGH_RAW)

_MONITORED = {"Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"}


# ── PUBLIC API ───────────────────────────────────────────────────────────────

def detect_countries(text: str) -> list:
    """Return list of monitored country names found in *text* (may be empty)."""
    matched = []
    for country, includes in _INC.items():
        if any(p.search(text) for p in includes):
            if not any(p.search(text) for p in _EXC.get(country, [])):
                matched.append(country)
    return matched


def detect_threat_type(text: str) -> tuple:
    """Return (threat_type_str, is_specific_match).
    is_specific_match is False only when we fell through to the Armed Conflict default.
    """
    for threat_type, patterns in _THRTS[:-1]:     # skip last (Armed Conflict catch-all)
        if any(p.search(text) for p in patterns):
            return threat_type, True
    # Check Armed Conflict patterns explicitly
    for p in _THRTS[-1][1]:
        if p.search(text):
            return "Armed Conflict", False         # matched, but non-specific
    return "Armed Conflict", False


def detect_severity(text: str) -> str:
    """Return 'Critical', 'High', or 'Medium'."""
    if any(p.search(text) for p in _CRIT):
        return "Critical"
    if any(p.search(text) for p in _HIGH):
        return "High"
    return "Medium"


def detect_region(text: str, country: str) -> str:
    """Return the most specific region name for *country* found in *text*."""
    for region_name, patterns in _REGS.get(country, []):
        if any(p.search(text) for p in patterns):
            return region_name
    return "National"


def score_confidence(
    countries_matched: list,
    source_countries: list,
    threat_specific: bool,
    severity: str,
) -> float:
    """
    Compute a composite confidence score 0.0–1.0.

    Breakdown:
      • Country match quality  (0.20–0.45)
      • Source specificity     (+0.15 if source is dedicated to the country)
      • Threat type clarity    (0.10 or 0.20)
      • Severity signal        (0.05–0.20)
    """
    if not countries_matched:
        return 0.0

    score = 0.25  # base for having any country match

    # Source specialization bonus
    dedicated = len(source_countries) <= 2   # source covers 1–2 countries
    if dedicated and any(c in source_countries for c in countries_matched):
        score += 0.25
    elif any(c in source_countries for c in countries_matched):
        score += 0.10

    # Threat type clarity
    score += 0.20 if threat_specific else 0.10

    # Severity signal
    if severity == "Critical":
        score += 0.20
    elif severity == "High":
        score += 0.15
    else:
        score += 0.05

    return round(min(score, 1.0), 2)


def classify_article(
    title: str,
    description: str,
    source_name: str,
    source_countries: list,
    pub_date: Optional[str],
    url: str,
    max_age_days: int = 30,
) -> Optional[dict]:
    """
    Classify a single article into an incident candidate dict.
    Returns None if the article is irrelevant or too old.

    The returned dict has all fields required by INCIDENTS in data.py,
    plus internal fields prefixed with '_' (stripped before dashboard injection).
    """
    combined = f"{title} {description}"

    # ── Date filter ───────────────────────────────────────────────────────
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if pub_date:
        try:
            # Handle both ISO and datetime objects
            if isinstance(pub_date, datetime):
                pub_dt = pub_date.replace(tzinfo=timezone.utc) if pub_date.tzinfo is None else pub_date
            else:
                pub_dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            if pub_dt < cutoff:
                return None
            date_str = pub_dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError, AttributeError):
            pass

    # ── Country detection ─────────────────────────────────────────────────
    countries = detect_countries(combined)

    # For dedicated sources, restrict matches to their covered countries.
    if len(source_countries) <= 3:
        countries = [c for c in countries if c in source_countries]

    if not countries:
        return None

    country = countries[0]   # primary country (first detected)

    # ── Classification ────────────────────────────────────────────────────
    threat_type, threat_specific = detect_threat_type(combined)
    severity = detect_severity(combined)
    region   = detect_region(combined, country)

    confidence = score_confidence(
        countries_matched=countries,
        source_countries=source_countries,
        threat_specific=threat_specific,
        severity=severity,
    )

    # Clean description: use title as primary, strip excess whitespace
    description_clean = re.sub(r"\s+", " ", title).strip()
    if len(description_clean) > 220:
        description_clean = description_clean[:217] + "..."

    return {
        # ── Dashboard-compatible fields ───────────────────────────────────
        "country":     country,
        "region":      region,
        "date":        date_str,
        "type":        threat_type,
        "description": description_clean,
        "severity":    severity,
        "source":      source_name,
        "sourceUrl":   url,
        # ── Internal metadata (stripped before dashboard injection) ───────
        "_confidence":     confidence,
        "_threat_specific": threat_specific,
        "_all_countries":  countries,
        "_raw_title":      title,
    }
