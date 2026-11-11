"""Catalog of job portals shown in V4Career.

Catalog presence makes a portal discoverable in the UI; it does not mean a
collector is configured or authorized. Configure and test an Actor/API/feed
before enabling collection. Popular portals are ordered first for sidebar UX.
"""
JOB_PORTALS = [
    {'name': 'LinkedIn', 'base_url': 'https://www.linkedin.com/jobs/', 'key': 'LINKEDIN_JOBS', 'popular': True, 'method': 'JobSpy'},
    {'name': 'Glassdoor', 'base_url': 'https://www.glassdoor.co.in/Job', 'key': 'GLASSDOOR', 'popular': True, 'method': 'JobSpy'},
    {'name': 'Naukri', 'base_url': 'https://www.naukri.com', 'key': 'NAUKRI', 'popular': True, 'method': 'JobSpy'},
    {'name': 'Indeed', 'base_url': 'https://in.indeed.com', 'key': 'INDEED', 'popular': True, 'method': 'JobSpy'},
    {'name': 'Foundit', 'base_url': 'https://www.foundit.in', 'key': 'FOUNDIT', 'popular': False, 'method': 'Apify'},
    {'name': 'Internshala', 'base_url': 'https://internshala.com', 'key': 'INTERNSHALA', 'popular': False, 'method': 'Apify'},
    {'name': 'TimesJobs', 'base_url': 'https://www.timesjobs.com', 'key': 'TIMESJOBS', 'popular': False, 'method': 'Apify'},
    {'name': 'Wellfound', 'base_url': 'https://wellfound.com', 'key': 'WELLFOUND', 'popular': False, 'method': 'Apify'},
    {'name': 'CutShort', 'base_url': 'https://cutshort.io/', 'key': 'CUTSHORT', 'popular': False, 'method': 'Apify'},
    {'name': 'Hirist', 'base_url': 'https://www.hirist.tech/', 'key': 'HIRIST', 'popular': False, 'method': 'Apify'},
    {'name': 'Instahyre', 'base_url': 'https://www.instahyre.com/', 'key': 'INSTAHYRE', 'popular': False, 'method': 'Apify'},
    {'name': 'Freshersworld', 'base_url': 'https://www.freshersworld.com/', 'key': 'FRESHERSWORLD', 'popular': False, 'method': 'Apify'},
    {'name': 'Unstop', 'base_url': 'https://unstop.com/', 'key': 'UNSTOP', 'popular': False, 'method': 'Apify'},
    {'name': 'Bayt', 'base_url': 'https://www.bayt.com/', 'key': 'BAYT', 'popular': False, 'method': 'JobSpy'},
    {'name': 'Shine', 'base_url': 'https://www.shine.com/', 'key': 'SHINE_COM', 'popular': False, 'method': 'Apify'},
]

# Display exactly the 15 selected portals in the Job Portal sidebar.
UI_PORTAL_KEYS = {item['key'] for item in JOB_PORTALS}

# Default Actor IDs are candidates; each portal still requires valid credentials,
# actor input configuration, and approval before collection can run.
DEFAULT_APIFY_ACTORS = {
    'FOUNDIT': 'deriverge~foundit-jobs-scraper',
    'INTERNSHALA': 'automation-lab~internshala-scraper',
    'TIMESJOBS': 'unfenced-group~timesjobs-scraper',
    'WELLFOUND': 'cprussin~wellfound-jobs',
    'CUTSHORT': 'silentflow~cutshort-jobs-scraper',
    'HIRIST': 's_actors~hirist-jobs-scraper',
    'INSTAHYRE': 'themineworks~instahyre-jobs-scraper',
    'FRESHERSWORLD': 'shahidirfan~freshersworld-jobs-scraper',
    'UNSTOP': 'data_daemon~unstop-scraper',
    'SHINE_COM': 'bovi~shine-scraper',
}


PORTAL_BY_KEY = {item["key"].lower(): item for item in JOB_PORTALS}
PORTAL_BY_NAME = {item["name"].strip().lower(): item for item in JOB_PORTALS}

# Community Actor candidates already used by this project. These are not
# pre-approved; collection still requires APIFY_ACCESS_APPROVED_<KEY>=true.
DEFAULT_APIFY_ACTORS = {
    "NAUKRI": "automation-lab~naukri-scraper",
    "INDEED": "unfenced-group~indeed-in-scraper",
    "FOUNDIT": "deriverge~foundit-jobs-scraper",
    "INTERNSHALA": "automation-lab~internshala-scraper",
    "TIMESJOBS": "unfenced-group~timesjobs-scraper",
    "WELLFOUND": "cprussin~wellfound-jobs",
    # Additional public Actor candidates; each remains approval-gated.
    "CUTSHORT": "silentflow~cutshort-jobs-scraper",
    "INSTAHYRE": "themineworks~instahyre-jobs-scraper",
    "HIRIST": "s_actors~hirist-jobs-scraper",
    "APNA": "automation-lab~apna-india-job-listings-scraper",
    "SHINE_COM": "bovi~shine-scraper",
    "IIMJOBS": "silentflow~iimjobs-scraper",
    "WORKINDIA": "jobsapi~workindia-jobs-search-scraper",
    "GLASSDOOR": "hgservices~glassdoor-jobs-scraper",
    # Additional candidates discovered in public Apify Store listings; not live-tested.
    "LINKEDIN_JOBS": "keklik~linkedin-jobs-scraper",
    "FRESHERSWORLD": "shahidirfan~freshersworld-jobs-scraper",
    "NATIONAL_CAREER_SERVICE_NCS": "jobsapi~ncs-jobs-search-scraper",
    "JOOBLE": "ahmed_jasarevic~jooble-scraper",
    "QUIKRJOBS": "jobsapi~quikr-jobs-search-scraper",
    "JORA": "scrapeai~jora-jobs-scraper",
    "PLACEMENTINDIA": "fervent_bus~placementindia-scraper",
}


# Apify estimated price per 1,000 jobs (USD) and account assignment from the user's sheet.
APIFY_PORTAL_BILLING = {
    "CUTSHORT": {"usd_per_1000": 0.80, "account": "COLLECTOR1"},
    "WELLFOUND": {"usd_per_1000": 0.50, "account": "COLLECTOR1"},
    "UNSTOP": {"usd_per_1000": 1.50, "account": "COLLECTOR1"},
    "FOUNDIT": {"usd_per_1000": 1.80, "account": "COLLECTOR1"},
    "TIMESJOBS": {"usd_per_1000": 1.99, "account": "COLLECTOR2"},
    "HIRIST": {"usd_per_1000": 1.99, "account": "COLLECTOR2"},
    "INSTAHYRE": {"usd_per_1000": 1.35, "account": "COLLECTOR3"},
    "FRESHERSWORLD": {"usd_per_1000": 0.79, "account": "COLLECTOR3"},
    "INTERNSHALA": {"usd_per_1000": None, "account": "COLLECTOR3"},
    "SHINE_COM": {"usd_per_1000": None, "account": "COLLECTOR3"},
}
