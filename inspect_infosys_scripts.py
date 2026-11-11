
import re
import requests
from urllib.parse import urljoin

BASE = "https://career.infosys.com/"
FILES = [
    "assets/js/env.js",
    "runtime.js",
    "scripts.js",
    "main.js",
]

session = requests.Session()
session.headers["User-Agent"] = "Mozilla/5.0"

patterns = [
    r"""https?://[^"'\\\s<>]+""",
    r"""["']([^"' ]{0,100}(?:api|joblist|job-list|search|graphql)[^"' ]{0,150})["']""",
]

for path in FILES:
    url = urljoin(BASE, path)
    print(f"\n{'=' * 60}\n{path}\n{'=' * 60}")

    try:
        response = session.get(url, timeout=20)
        print("HTTP:", response.status_code, "| Size:", len(response.text))

        if response.status_code != 200:
            continue

        matches = set()
        for pattern in patterns:
            for match in re.findall(pattern, response.text, re.IGNORECASE):
                value = match if isinstance(match, str) else match[0]
                if re.search(r"api|joblist|job-list|search|graphql", value, re.I):
                    matches.add(value[:250])

        for item in sorted(matches)[:50]:
            print(item)

        if not matches:
            print("No likely API/job-search strings found in this file.")

    except requests.RequestException as exc:
        print("Request error:", exc)
