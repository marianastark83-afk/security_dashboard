"""
Incident quality filter for scraped results.

Removes noise (diplomacy, sports, governance) and keeps genuine
security-relevant articles. Applied automatically by the pipeline.
"""

import re

# ── Patterns that signal noise (exclude unless KEEP overrides) ────────────────
_EXCLUDE = re.compile(
    r'\b(eid|congratulat|celebrat|festival|prayer|ramadan|graduation|'
    r'wedding|sport|football|match|cup|champion|award|scholarship|'
    r'inaugurat|trade deal|investment forum|summit communiqu|'
    r'signed agreement|bilateral|memorandum of understanding|mou signed|'
    r'university|exam|education budget|health budget|'
    r'weather forecast|rain season|suez university)\b',
    re.IGNORECASE,
)

# ── Patterns that confirm security relevance ───────────────────────────────────
_KEEP = re.compile(
    r'\b(kill|killed|dead|death|attack|attacke|strike|struck|bomb|'
    r'clash|clashes|fighting|fighter|armed|militia|troops|soldier|'
    r'military|forces|offensive|operation|rebel|insurgent|'
    r'displaced|displacement|refugee|humanitarian|crisis|'
    r'artillery|shelling|airstrike|drone|explosion|ambush|'
    r'abduct|kidnap|massacre|civilian|casualt|wound|injur|'
    r'al.?shabaab|rsf|saf|m23|tplf|ola |sspdf|codeco|fdlr|'
    r'blockade|siege|ceasefire|peace deal|collapse|breakdown|'
    r'famine|hunger|starvat|malnutrit|cholera|ebola|outbreak|'
    r'arrest|detain|prison|coup|unrest|protest|demonstrat|'
    r'threat|security|risk|danger|hostage|ransom|sanction|'
    r'briefing|solidarity|missile|biosecurity|quarantine)\b',
    re.IGNORECASE,
)

# ── Type corrections for obvious misclassifications ───────────────────────────
_TYPE_FIXES = [
    (re.compile(r'\bebola\b|\boutbreak\b|\bbiosecurity\b|\bquarantine\b', re.IGNORECASE), "Natural Hazard"),
    (re.compile(r'\bsanction|un security council|peace deal\b', re.IGNORECASE),            "Political Instability"),
    (re.compile(r'\bsolidarity\b|\bdelegation\b|\bcooperation\b', re.IGNORECASE),          "Political Instability"),
]


def apply(incidents: list) -> list:
    """
    Filter a list of raw incident dicts and return only security-relevant ones.
    Also corrects obvious threat-type misclassifications.
    """
    kept = []
    for inc in incidents:
        text = inc.get("description", "") + " " + inc.get("type", "")
        if _EXCLUDE.search(text) and not _KEEP.search(text):
            continue
        if not _KEEP.search(text):
            continue
        # Fix type if clearly wrong
        for pattern, correct_type in _TYPE_FIXES:
            if pattern.search(text):
                inc = dict(inc)        # don't mutate original
                inc["type"] = correct_type
                break
        kept.append(inc)
    return kept
