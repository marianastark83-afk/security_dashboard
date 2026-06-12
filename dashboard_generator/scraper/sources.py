"""
RSS feed configurations for all monitored news sources.

Each source entry:
  name        - display name used in incident records
  rss         - primary RSS/Atom feed URL
  rss_alt     - fallback URL if primary fails (optional)
  countries   - which of the 5 monitored countries this source covers
                (shorter list = higher classification confidence)
  language    - 'en' (default) or 'fr' for French-language sources

X / Twitter accounts
--------------------
X accounts are fetched via the Xquik REST API (https://xquik.com). The
`_x()` helper marks the source with `x_handle`; the fetcher dispatcher
routes it to scraper.xquik_fetcher.fetch_xquik_user.

Requires environment variable XQUIK_API_KEY. If not set, X sources
silently return no tweets and the pipeline continues with RSS only.

Accounts that maintain their own news websites use those RSS feeds
directly as more reliable alternatives — see Sudan War Monitor, Addis
Standard, etc.
"""


def _x(handle: str, name: str, countries: list, language: str = "en") -> dict:
    """Build a source config entry for a Twitter/X account fetched via Xquik."""
    username = handle.lstrip("@")
    return {
        "name":      name,
        "x_handle":  username,
        "countries": countries,
        "language":  language,
    }


SOURCES = [

    # ══════════════════════════════════════════════════════════════════════════
    # MULTI-COUNTRY — General Africa coverage
    # ══════════════════════════════════════════════════════════════════════════
    {
        "name": "Al Jazeera Africa",
        "rss":  "https://www.aljazeera.com/xml/rss/all.xml",
        "countries": ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"],
    },
    {
        "name": "AllAfrica",
        "rss":  "https://allafrica.com/tools/headlines/rss.xml",
        "countries": ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"],
    },
    {
        "name": "The East African",
        "rss":     "https://www.theeastafrican.co.ke/tea/rss",
        "rss_alt": "https://www.theeastafrican.co.ke/rss",
        "countries": ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"],
    },
    {
        "name": "The Africa Report",
        "rss":  "https://www.theafricareport.com/feed/",
        "countries": ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"],
    },
    {
        "name": "Daily Nation Africa",
        "rss":     "https://nation.africa/africa/rss",
        "rss_alt": "https://nation.africa/rss",
        "countries": ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"],
    },
    {
        "name": "CFR Global Conflict Tracker",
        "rss":     "https://www.cfr.org/rss.xml",
        "rss_alt": "https://www.cfr.org/region/sub-saharan-africa/rss.xml",
        "countries": ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"],
    },
    {
        "name": "Critical Threats",
        "rss":  "https://www.criticalthreats.org/feed/",
        "countries": ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"],
    },
    {
        "name": "NewsNow World News",
        "rss":  "https://www.newsnow.co.uk/h/World+News?rss",
        "countries": ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"],
    },
    # @Reuters — Reuters Africa wire feed
    {
        "name":    "Reuters",
        "rss":     "https://feeds.reuters.com/reuters/worldnews",
        "rss_alt": "https://feeds.reuters.com/Reuters/worldNews",
        "countries": ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"],
    },
    # @trtafrika — TRT Afrika regional coverage
    {
        "name":    "TRT Afrika",
        "rss":     "https://www.trtafrika.com/feed/",
        "countries": ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"],
    },
    # @AfricaCDC — Africa Centres for Disease Control (health + crisis alerts)
    {
        "name":    "Africa CDC",
        "rss":     "https://africacdc.org/feed/",
        "countries": ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"],
    },
    # @ForeignAffairs — policy analysis and strategic context
    {
        "name":    "Foreign Affairs",
        "rss":     "https://www.foreignaffairs.com/rss.xml",
        "countries": ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SUDAN
    # ══════════════════════════════════════════════════════════════════════════
    # @sudan_war — Sudan War Monitor (Substack)
    {
        "name":    "Sudan War Monitor",
        "rss":     "https://sudanwarmonitor.substack.com/feed",
        "countries": ["Sudan"],
    },
    {
        "name": "Sudan Tribune",
        "rss":  "https://sudantribune.com/feed/",
        "countries": ["Sudan"],
    },
    {
        "name":    "Sudans Post",
        "rss":     "https://www.sudanspost.com/feed/",
        "countries": ["Sudan", "South Sudan"],
    },
    # @thesudantimes — The Sudan Times
    {
        "name":    "The Sudan Times",
        "rss":     "https://thesudantimes.net/feed/",
        "countries": ["Sudan"],
    },
    # @Sudan_tweet — Sudan news aggregator (X/Nitter only)
    _x("Sudan_tweet", "Sudan Tweet", ["Sudan"]),

    # ══════════════════════════════════════════════════════════════════════════
    # SOUTH SUDAN
    # ══════════════════════════════════════════════════════════════════════════
    {
        "name":    "Radio Tamazuj",
        "rss":     "https://radiotamazuj.org/en/rss.xml",
        "rss_alt": "https://radiotamazuj.org/en/feed",
        "countries": ["South Sudan"],
    },
    {
        "name":    "NewsNow South Sudan",
        "rss":     "https://www.newsnow.co.uk/h/World+News/Africa/South+Sudan?rss",
        "countries": ["South Sudan"],
    },
    # @SouthSudanNews6 — South Sudan News (X/Nitter)
    _x("SouthSudanNews6", "South Sudan News", ["South Sudan"]),
    # @SSGglobal — South Sudan Government Global (X/Nitter)
    _x("SSGglobal", "SSG Global", ["South Sudan"]),
    # @ssemtv — SSEM TV South Sudan (X/Nitter)
    _x("ssemtv", "SSEM TV", ["South Sudan"]),
    # @MSF_SouthSudan — MSF South Sudan
    {
        "name":    "MSF South Sudan",
        "rss":     "https://www.msf.org/rss/news",
        "countries": ["South Sudan"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ETHIOPIA
    # ══════════════════════════════════════════════════════════════════════════
    {
        "name":    "The Reporter Ethiopia",
        "rss":     "https://www.thereporterethiopia.com/feed/",
        "countries": ["Ethiopia"],
    },
    {
        "name":    "AllAfrica Ethiopia",
        "rss":     "https://allafrica.com/ethiopia/tools/headlines/rss.xml",
        "countries": ["Ethiopia"],
    },
    {
        "name":    "NewsNow Ethiopia",
        "rss":     "https://www.newsnow.co.uk/h/World+News/Africa/Ethiopia?rss",
        "countries": ["Ethiopia"],
    },
    # @EthiopianNewsA — Ethiopian News Agency (state media)
    {
        "name":    "Ethiopian News Agency",
        "rss":     "https://www.ena.et/en/?feed=rss2",
        "countries": ["Ethiopia"],
    },
    # @addisstandard — Addis Standard (independent journalism)
    {
        "name":    "Addis Standard",
        "rss":     "https://addisstandard.com/feed/",
        "countries": ["Ethiopia"],
    },
    # @EthiopiaNews3 — Ethiopia News (X/Nitter)
    _x("EthiopiaNews3", "Ethiopia News", ["Ethiopia"]),
    # @AmharaWarUpdate — Amhara conflict tracker (X/Nitter)
    _x("AmharaWarUpdate", "Amhara War Update", ["Ethiopia"]),

    # ══════════════════════════════════════════════════════════════════════════
    # SOMALIA
    # ══════════════════════════════════════════════════════════════════════════
    {
        "name":    "Somali Guardian",
        "rss":     "https://www.somaliguardian.com/feed/",
        "countries": ["Somalia"],
    },
    {
        "name":    "SONNA Somalia",
        "rss":     "https://sonna.so/en/feed/",
        "rss_alt": "https://sonna.so/feed/",
        "countries": ["Somalia"],
    },
    {
        "name":    "Horseed Media",
        "rss":     "https://horseedmedia.net/feed/",
        "countries": ["Somalia"],
    },
    # @SomaliaNewsroom — Somalia Newsroom (X/Nitter)
    _x("SomaliaNewsroom", "Somalia Newsroom", ["Somalia"]),
    # @somalianews — Somalia News (X/Nitter)
    _x("somalianews", "Somalia News", ["Somalia"]),
    # @SomaliFederalN — Somali Federal Network (X/Nitter)
    _x("SomaliFederalN", "Somali Federal Network", ["Somalia"]),

    # ══════════════════════════════════════════════════════════════════════════
    # DRC
    # ══════════════════════════════════════════════════════════════════════════
    {
        "name":    "Radio Okapi",
        "rss":     "https://www.radiookapi.net/rss.xml",
        "rss_alt": "https://www.radiookapi.net/feed/",
        "countries": ["DRC"],
        "language": "fr",
    },
    {
        "name":    "The Africa Report – DRC",
        "rss":     "https://www.theafricareport.com/country/democratic-republic-of-congo/feed/",
        "countries": ["DRC"],
    },
    {
        "name":    "NewsNow DRC",
        "rss":     "https://www.newsnow.co.uk/h/World+News/Africa/DR+Congo?rss",
        "countries": ["DRC"],
    },
    {
        "name":    "AllAfrica DRC",
        "rss":     "https://allafrica.com/drc/tools/headlines/rss.xml",
        "rss_alt": "https://allafrica.com/democraticrepublicofcongo/tools/headlines/rss.xml",
        "countries": ["DRC"],
    },
    # @BreakingN_RDC — Breaking News RDC (X/Nitter)
    _x("BreakingN_RDC", "Breaking News RDC", ["DRC"]),
    # @MONUSCO — UN peacekeeping mission DRC
    {
        "name":    "MONUSCO",
        "rss":     "https://monusco.unmissions.org/en/rss.xml",
        "countries": ["DRC"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ADDITIONAL WEB SOURCES (2026-06)
    # ══════════════════════════════════════════════════════════════════════════

    # ── Sudan / regional humanitarian ─────────────────────────────────────────
    {
        "name":    "Dabanga Sudan",
        "rss":     "https://www.dabangasudan.org/en/feed",
        "rss_alt": "https://www.dabangasudan.org/en/all-news/feed",
        "countries": ["Sudan"],
    },
    {
        "name":    "Nuba Reports",
        "rss":     "https://nubareports.org/feed/",
        "countries": ["Sudan"],
    },
    {
        "name":    "The New Humanitarian – Sudan",
        "rss":     "https://www.thenewhumanitarian.org/rss/section/233.xml",
        "rss_alt": "https://www.thenewhumanitarian.org/africa/east-africa/sudan",  # TODO: verify RSS
        "countries": ["Sudan", "South Sudan", "Ethiopia"],
    },
    {
        "name":    "BBC Sudan",
        "rss":     "https://feeds.bbci.co.uk/news/topics/cq23pdgvgm8t/rss.xml",
        "rss_alt": "https://www.bbc.com/news/topics/cq23pdgvgm8t",  # TODO: verify RSS
        "countries": ["Sudan"],
    },
    {
        "name":    "ReliefWeb",
        "rss":     "https://reliefweb.int/updates/rss.xml",
        "countries": ["Sudan", "South Sudan", "DRC", "Somalia", "Ethiopia"],
    },

    # ── South Sudan ───────────────────────────────────────────────────────────
    {
        "name":    "Eye Radio",
        "rss":     "https://www.eyeradio.org/feed/",
        "countries": ["South Sudan"],
    },
    {
        "name":    "Pachodo",
        "rss":     "https://pachodo.org/feed",
        "rss_alt": "https://pachodo.org/news-from-various-sources",  # TODO: verify RSS
        "countries": ["South Sudan"],
    },
    {
        "name":    "The Africa Report – South Sudan",
        "rss":     "https://www.theafricareport.com/country/south-sudan/feed/",
        "countries": ["South Sudan"],
    },

    # ── DRC (French) ──────────────────────────────────────────────────────────
    {
        "name":    "Afrik.com RDC",
        "rss":     "https://www.afrik.com/rdc/feed",
        "rss_alt": "https://www.afrik.com/feed",
        "countries": ["DRC"],
        "language": "fr",
    },

    # ── Ethiopia ──────────────────────────────────────────────────────────────
    {
        "name":    "Ethiopia Observer",
        "rss":     "https://www.ethiopiaobserver.com/feed/",
        "countries": ["Ethiopia"],
    },
    {
        "name":    "The Africa Report – Ethiopia",
        "rss":     "https://www.theafricareport.com/country/ethiopia/feed/",
        "countries": ["Ethiopia"],
    },
    {
        "name":    "Borkena",
        "rss":     "https://borkena.com/feed/",
        "countries": ["Ethiopia"],
    },
    {
        "name":    "Ethiopia Insight",
        "rss":     "https://www.ethiopia-insight.com/feed/",
        "countries": ["Ethiopia"],
    },
    {
        "name":    "Ethiopian Monitor",
        "rss":     "https://ethiopianmonitor.com/feed/",
        "countries": ["Ethiopia"],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # ADDITIONAL X ACCOUNTS (2026-06) — Nitter RSS
    # ══════════════════════════════════════════════════════════════════════════

    # ── Sudan ─────────────────────────────────────────────────────────────────
    _x("24Darfur",       "24 Darfur",        ["Sudan"]),
    _x("SudanPlusNews",  "Sudan Plus News",  ["Sudan"]),
    _x("SudanTribune",   "Sudan Tribune (X)", ["Sudan"]),
    _x("martinplaut",    "Martin Plaut",     ["Sudan", "Ethiopia"]),

    # ── South Sudan ───────────────────────────────────────────────────────────
    _x("SSudanNews",     "South Sudan News (X)", ["South Sudan"]),
    _x("EyeRadioJuba",   "Eye Radio Juba",       ["South Sudan"]),
    _x("SouthSudanGov",  "South Sudan Gov",      ["South Sudan"]),
    _x("PonnieSheila",   "Ponnie Sheila",        ["South Sudan"]),

    # ── Ethiopia ──────────────────────────────────────────────────────────────
    _x("TheReporterET",  "The Reporter ET (X)",  ["Ethiopia"]),
    _x("EthiopiaInsight","Ethiopia Insight (X)", ["Ethiopia"]),
    _x("PMEthiopia",     "PM Ethiopia",          ["Ethiopia"]),
    _x("EthioReporter",  "Ethio Reporter",       ["Ethiopia"]),

    # ── Somalia ───────────────────────────────────────────────────────────────
    _x("SMSSomaliTV1",   "SMS Somali TV",        ["Somalia"]),
    _x("Baidoaonline",   "Baidoa Online",        ["Somalia"]),
    _x("ADFmagazine",    "ADF Magazine",         ["Somalia"]),
    _x("SomaliGuardian", "Somali Guardian (X)",  ["Somalia"]),
    _x("Hornpostnews",   "Horn Post News",       ["Somalia"]),
    _x("Eye_on_Somalia", "Eye on Somalia",       ["Somalia"]),
    _x("DawanAfrica",    "Dawan Africa",         ["Somalia"]),
    _x("SouthwestWatxh", "Southwest Watch",      ["Somalia"]),
    _x("GaroweOnline",   "Garowe Online",        ["Somalia"]),
    _x("FrontierOnlineK","Frontier Online K",    ["Somalia"]),
    _x("SONNALIVE",      "SONNA Live",           ["Somalia"]),
    _x("TheDailySomalia","The Daily Somalia",    ["Somalia"]),
    _x("AnalystSomalia", "Somalia Analyst",      ["Somalia"]),

    # ── DRC ───────────────────────────────────────────────────────────────────
    _x("FelixUdps",       "Felix UDPS",           ["DRC"], language="fr"),
    _x("life_Info_",      "Life Info",            ["DRC"], language="fr"),
    _x("VoiceOfCongo",    "Voice of Congo",       ["DRC"]),
    _x("thetimesplus",    "The Times Plus",       ["DRC"]),
    _x("alternancecd",    "Alternance CD",        ["DRC"], language="fr"),
    _x("mediacongo",      "Media Congo",          ["DRC"], language="fr"),
    _x("CACAP_NEWS",      "CACAP News",           ["DRC"], language="fr"),
    _x("KongoMediaRDC",   "Kongo Media RDC",      ["DRC"], language="fr"),
    _x("radiookapi",      "Radio Okapi (X)",      ["DRC"], language="fr"),
    _x("rtncofficielle1", "RTNC Officielle",      ["DRC"], language="fr"),

    # ── Regional / analysts ───────────────────────────────────────────────────
    _x("africaupdates",   "Africa Updates",       ["Sudan","South Sudan","DRC","Somalia","Ethiopia"]),
    _x("_AfricanUnion",   "African Union",        ["Sudan","South Sudan","DRC","Somalia","Ethiopia"]),
    _x("jeune_afrique",   "Jeune Afrique",        ["Sudan","South Sudan","DRC","Somalia","Ethiopia"], language="fr"),
    _x("RFI",             "RFI",                  ["Sudan","South Sudan","DRC","Somalia","Ethiopia"], language="fr"),
    _x("AfricaViewFacts", "Africa View Facts",    ["Sudan","South Sudan","DRC","Somalia","Ethiopia"]),
    _x("ThomasVLinge",    "Thomas van Linge",     ["Sudan","Ethiopia"]),
    _x("LarryMadowo",     "Larry Madowo",         ["Sudan","South Sudan","DRC","Somalia","Ethiopia"]),
    _x("Lattif",          "Lattif",               ["Sudan","Somalia","Ethiopia"]),
    _x("samirasawlani",   "Samira Sawlani",       ["Sudan","South Sudan","DRC","Somalia","Ethiopia"]),
    _x("johnnallannamu",  "John Allan Namu",      ["Sudan","South Sudan","DRC","Somalia","Ethiopia"]),
    _x("Afuncensored",    "Africa Uncensored",    ["Sudan","South Sudan","DRC","Somalia","Ethiopia"]),
    _x("Nairobi_News",    "Nairobi News",         ["Sudan","South Sudan","DRC","Somalia","Ethiopia"]),
    _x("Kalinaki",        "Daniel Kalinaki",      ["Sudan","South Sudan","DRC","Somalia","Ethiopia"]),
    _x("JewelKiriungi",   "Jewel Kiriungi",       ["Sudan","South Sudan","DRC","Somalia","Ethiopia"]),
    _x("bella_twine",     "Bella Twine",          ["Sudan","South Sudan","DRC","Somalia","Ethiopia"]),
    _x("WorldBankAfrica", "World Bank Africa",    ["Sudan","South Sudan","DRC","Somalia","Ethiopia"]),
]
