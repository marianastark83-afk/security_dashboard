"""
Dynamic country profile builder.

Generates the COUNTRIES list from live incidents instead of using
static curated data. Called automatically by the pipeline each run.
"""

from datetime import datetime, timezone

# ── Severity ordering ─────────────────────────────────────────────────────────
_SEV_ORDER = {"Critical": 0, "High": 1, "Medium": 2}


def _worst_severity(incidents: list) -> str:
    if not incidents:
        return "Medium"
    return min(incidents, key=lambda i: _SEV_ORDER.get(i.get("severity", "Medium"), 2))["severity"]


def _unique_ordered(values: list) -> list:
    seen = set()
    out = []
    for v in values:
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


# ── Implication templates keyed by threat type ────────────────────────────────
_IMPLICATIONS = {
    "Armed Conflict": [
        "Active armed clashes confirmed in {region} — suspend all non-essential personnel movement",
        "Road and transit routes through {region} are unsafe — implement alternate routing or armed escort",
    ],
    "Terrorism": [
        "Terrorist/militia activity confirmed — heighten compound security posture and access control",
        "Opportunistic attack risk elevated — avoid predictable movement patterns and public spaces",
    ],
    "Political Instability": [
        "Political crisis generating armed incidents — security force posture is unpredictable",
        "Government stability under pressure — rapid policy shifts may affect operations without notice",
    ],
    "Natural Hazard": [
        "Active disease/health emergency — all field personnel must follow WHO/CDC protocols immediately",
        "Health system under strain from dual conflict and outbreak pressure — access to care restricted",
    ],
    "Civil Unrest": [
        "Civil unrest confirmed — public gatherings and demonstrations carry elevated risk",
        "Security force response to protests may be disproportionate — avoid demonstration areas",
    ],
    "Drone Attack": [
        "Drone strike activity confirmed — maintain minimum safe distance from military infrastructure",
        "Airport and military installations are priority targets — assess air operations risk",
    ],
    "IED/Mines": [
        "IED/mine threat confirmed on road corridors — all vehicle movement requires prior route clearance",
    ],
}

_DEFAULT_IMPLICATION = "Security incident reported — assess risk before any movement in affected area"

# ── Action templates keyed by severity ────────────────────────────────────────
_ACTIONS_BY_SEV = {
    "Critical": [
        "Implement immediate movement restrictions for all personnel in affected areas",
        "Activate emergency communications protocols and verify staff accountability",
        "Brief senior leadership within 24 hours with situation update",
        "Coordinate with UNMISS/MONUSCO/local authorities for movement security clearances",
    ],
    "High": [
        "Restrict non-essential movement in affected regions until further assessment",
        "Issue staff security advisory and verify safe locations of all field personnel",
        "Monitor situation closely — reassess within 48 hours or upon new developments",
    ],
    "Medium": [
        "Maintain heightened situational awareness in affected areas",
        "Verify field personnel are aware of current threat and have emergency contacts active",
        "Continue monitoring and reassess if situation escalates",
    ],
}

_ACTIONS_NO_INCIDENTS = [
    "Maintain existing security posture — no new incidents to assess",
    "Monitor key sources daily for any new developments in this country",
    "Do not interpret absence of reporting as de-escalation — verify with field contacts",
]


def _build_summary(name: str, incidents: list, cutoff_date: str, today: str) -> str:
    if not incidents:
        return (
            f"No incidents reported in this reporting window ({cutoff_date} – {today}). "
            f"Underlying conflict and security threats remain active — absence of reporting "
            f"does not indicate de-escalation. Maintain existing security posture and monitor key sources."
        )

    n = len(incidents)
    crit = [i for i in incidents if i["severity"] == "Critical"]
    high = [i for i in incidents if i["severity"] == "High"]
    med  = [i for i in incidents if i["severity"] == "Medium"]

    parts = []
    if crit:
        parts.append(f"{len(crit)} Critical")
    if high:
        parts.append(f"{len(high)} High")
    if med:
        parts.append(f"{len(med)} Medium")
    sev_str = ", ".join(parts)

    # Lead with the most severe incident
    lead_inc = sorted(incidents, key=lambda i: _SEV_ORDER.get(i.get("severity","Medium"), 2))[0]
    lead = lead_inc.get("description", "")

    # Supporting incidents (next 1-2 unique descriptions)
    supporting = [
        i["description"] for i in incidents
        if i["description"] != lead and i["severity"] in ("Critical", "High")
    ][:2]

    summary = (
        f"{n} incident{'s' if n > 1 else ''} reported ({cutoff_date}–{today}) — "
        f"{sev_str} severity. "
        f"Lead: {lead}."
    )
    if supporting:
        summary += " Also: " + "; ".join(supporting) + "."
    return summary


def _build_implications(incidents: list) -> list:
    seen_types = _unique_ordered([i.get("type","") for i in incidents])
    implications = []
    for threat_type in seen_types:
        region = next(
            (i.get("region","the area") for i in incidents if i.get("type") == threat_type),
            "the area",
        )
        region = region if region and region != "National" else "the area"
        templates = _IMPLICATIONS.get(threat_type, [_DEFAULT_IMPLICATION])
        for tpl in templates[:2]:
            implications.append(tpl.format(region=region))
    return implications[:5]  # cap at 5


def _build_actions(incidents: list, severity: str) -> list:
    if not incidents:
        return _ACTIONS_NO_INCIDENTS
    base = list(_ACTIONS_BY_SEV.get(severity, _ACTIONS_BY_SEV["Medium"]))
    # Add type-specific actions
    seen_types = _unique_ordered([i.get("type","") for i in incidents])
    extras = {
        "Natural Hazard":      "Enforce disease prevention protocols and coordinate with Africa CDC before deployment",
        "Drone Attack":        "Issue staff advisories on drone threat — avoid proximity to military installations",
        "Terrorism":           "Review compound security measures and ensure all staff have emergency contact protocols active",
        "Political Instability": "Monitor official government and military communications for rapid posture changes",
    }
    for t in seen_types:
        if t in extras and extras[t] not in base:
            base.append(extras[t])
    return base[:5]


def _build_sources(incidents: list, default_sources: list) -> list:
    # Build from incident URLs, fall back to defaults
    seen = set()
    sources = []
    for inc in incidents:
        name = inc.get("source", "")
        url  = inc.get("sourceUrl", "")
        if url and url not in seen and name:
            seen.add(url)
            sources.append({"name": name, "url": url})
    if not sources:
        return default_sources
    return sources[:4]


# ── Public API ────────────────────────────────────────────────────────────────

def build_country_profiles(
    incidents: list,
    country_meta: list,
    days: int = 3,
) -> list:
    """
    Build a COUNTRIES list dynamically from the current incident set.

    Args:
        incidents:    Filtered, deduplicated incidents for the reporting window.
        country_meta: COUNTRY_META list from data.py (id, name, flag, defaultSources).
        days:         Reporting window in days (used in summary text).

    Returns:
        List of country profile dicts ready for injection into the dashboard.
    """
    now_utc    = datetime.now(timezone.utc)
    today      = now_utc.strftime("%d %b %Y")
    cutoff_dt  = now_utc
    from datetime import timedelta
    cutoff_str = (cutoff_dt - timedelta(days=days)).strftime("%d %b %Y")

    profiles = []
    for meta in country_meta:
        name = meta["name"]
        c_incs = [i for i in incidents if i.get("country") == name]

        # Sort: Critical first, then date desc
        c_incs.sort(
            key=lambda i: (_SEV_ORDER.get(i.get("severity","Medium"), 2), i.get("date","")),
        )

        severity      = _worst_severity(c_incs)
        summary       = _build_summary(name, c_incs, cutoff_str, today)
        key_regions   = _unique_ordered(
            [i.get("region","") for i in c_incs if i.get("region") and i.get("region") != "National"]
        )[:5] or ["National"]
        threats       = _unique_ordered([i.get("type","") for i in c_incs])
        op_implications = _build_implications(c_incs)
        actions       = _build_actions(c_incs, severity)
        sources       = _build_sources(c_incs, meta.get("defaultSources", []))

        profiles.append({
            "id":             meta["id"],
            "name":           name,
            "flag":           meta["flag"],
            "severity":       severity,
            "summary":        summary,
            "keyRegions":     key_regions,
            "threats":        threats,
            "opImplications": op_implications,
            "actions":        actions,
            "sources":        sources,
        })

    return profiles
