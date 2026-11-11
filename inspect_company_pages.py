
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

PAGES = {
    "INFOSYS": "https://career.infosys.com/jobs?countrycode=IN",
    "AMAZON": "https://www.amazon.jobs/en/search?base_query=&country=IND",
    "WIPRO": "https://careers.wipro.com/go/India/9649255/",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

for company, url in PAGES.items():
    print(f"\n{'=' * 65}\n{company}\n{'=' * 65}")

    try:
        response = requests.get(
            url, headers=headers, timeout=20, allow_redirects=True
        )
        soup = BeautifulSoup(response.text, "html.parser")

        print("HTTP:", response.status_code)
        print("Final URL:", response.url)

        print("\nJavaScript files:")
        for tag in soup.find_all("script", src=True)[:25]:
            print("-", tag["src"])

        print("\nEmbedded data markers:")
        markers = (
            "api/", "/api", "graphql", "joblist", "job-list",
            "jobsearch", "job-search", "requisition", "jobId",
            "job_id", "searchresults", "search-results",
        )
        lower = response.text.lower()
        for marker in markers:
            count = lower.count(marker.lower())
            if count:
                print(f"- {marker}: {count} occurrence(s)")

        print("\nPotential job-related links:")
        count = 0
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            label = tag.get_text(" ", strip=True)
            combined = f"{label} {href}".lower()
            if any(word in combined for word in (
                "jobid", "job-id", "jobdetail", "job-detail",
                "jobposting", "requisition", "joblist", "job-list",
            )):
                print("-", label[:100], "->", href)
                count += 1
                if count >= 15:
                    break
        if count == 0:
            print("- No matching links found in returned HTML")

        filename = f"inspect_{company.lower()}.html"
        with open(filename, "w", encoding="utf-8") as file:
            file.write(response.text)
        print("\nSaved response for local inspection:", filename)

    except requests.RequestException as exc:
        print("REQUEST ERROR:", exc)
