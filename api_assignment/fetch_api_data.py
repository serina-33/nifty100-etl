"""
fetch_api_data.py — Week 2 deliverable: REST APIs & JSON
Calls a public REST API (GitHub Search API), inspects the JSON response,
and converts the relevant fields into a CSV for analysis.
"""
import csv
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent

API_URL = "https://api.github.com/search/repositories"
PARAMS = {
    "q": "topic:stock-market language:python",
    "sort": "stars",
    "order": "desc",
    "per_page": "10",
}


def call_api(retries=3, backoff=5):
    url = f"{API_URL}?{urllib.parse.urlencode(PARAMS)}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "bluestock-internship-assignment",
    }
    last_err = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            last_err = e
            print(f"Attempt {attempt} failed ({e}); retrying in {backoff}s...")
            time.sleep(backoff)
    raise last_err


def main():
    data = call_api()

    raw_path = OUT_DIR / "api_response_raw.json"
    raw_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved raw JSON response -> {raw_path}")
    print(f"total_count reported by API: {data.get('total_count')}")

    items = data.get("items", [])
    csv_path = OUT_DIR / "github_fintech_repos.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["repo_name", "owner", "stars", "forks", "language",
                          "open_issues", "url", "description"])
        for item in items:
            writer.writerow([
                item.get("name"),
                item.get("owner", {}).get("login"),
                item.get("stargazers_count"),
                item.get("forks_count"),
                item.get("language"),
                item.get("open_issues_count"),
                item.get("html_url"),
                (item.get("description") or "").replace("\n", " ")[:120],
            ])

    print(f"Converted {len(items)} JSON records -> {csv_path}")


if __name__ == "__main__":
    main()
