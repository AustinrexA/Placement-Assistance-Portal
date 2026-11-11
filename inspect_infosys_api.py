
import re
import requests

BASE = "https://career.infosys.com/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

files = {
    "env.js": "assets/js/env.js",
    "main.js": "main.js",
}

needles = [
    "MongoApiUrl",
    "getCareerSearchJobs",
    "getSearchJobs",
    "BATCH_SIZE",
    "sourceId",
]

for name, path in files.items():
    print(f"\n{'=' * 60}\n{name}\n{'=' * 60}")
    response = requests.get(BASE + path, headers=HEADERS, timeout=30)
    print("HTTP:", response.status_code)

    if response.status_code != 200:
        continue

    content = response.text
    if name == "env.js":
        print(content[:12000])
        continue

    for needle in needles:
        print(f"\n--- {needle} ---")
        matches = list(re.finditer(re.escape(needle), content, re.I))
        print("Occurrences:", len(matches))

        for match in matches[:3]:
            start = max(0, match.start() - 500)
            end = min(len(content), match.end() + 1000)
            print(content[start:end])
            print("-" * 30)
