import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# -------------------------
# Config
# -------------------------

BASE_URL = "https://www.sports-reference.com"

# 2024-25 college season is labeled 2025 on Sports-Reference
SPORTSREF_YEAR = 2025
CONF_SLUG = "sun-belt"

CONF_URL = f"{BASE_URL}/cbb/conferences/{CONF_SLUG}/men/{SPORTSREF_YEAR}.html"

# Resolve project root based on this file's location
# scripts/ -> project root is the parent of this directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUT_DIR = (
    PROJECT_ROOT
    / "ncaa-analytics"
    / "data_raw"
    / "sun_belt"
    / "2024-25"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; itpr-ncaa-database-v0/0.1; "
        "+https://itprodirect.com)"
    )
}


# -------------------------
# Helpers
# -------------------------

def ensure_out_dir() -> None:
    """Create the output directory if it doesn't exist."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_html(url: str) -> str:
    """Fetch a URL and return response text, raising on HTTP errors."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def get_sunbelt_teams():
    """
    Return list of (team_name, team_slug, team_url) for Sun Belt 2024-25.

    Scrapes the Sun Belt conference page for the 2025 Sports-Reference season.
    """
    html = fetch_html(CONF_URL)
    soup = BeautifulSoup(html, "html.parser")

    teams = []

    # Sports-Ref conference page has tables with links to /cbb/schools/{slug}/{year}.html
    for a in soup.select("table a[href*='/cbb/schools/']"):
        team_url = a["href"]
        team_name = a.get_text(strip=True)

        parts = team_url.strip("/").split("/")
        # Expect: ['cbb', 'schools', '{slug}', '2025.html']
        if len(parts) >= 4 and parts[1] == "schools":
            team_slug = parts[2]
            full_url = BASE_URL + team_url
            teams.append((team_name, team_slug, full_url))

    # Deduplicate by slug
    seen = set()
    unique = []
    for name, slug, url in teams:
        if slug not in seen:
            seen.add(slug)
            unique.append((name, slug, url))

    if not unique:
        print("WARNING: No teams found. The page structure may have changed.")
    return unique


def save_team_page(team_name: str, team_slug: str, url: str) -> None:
    """Download team-season page and save to disk."""
    print(f"Fetching {team_name} ({team_slug}) from {url}")
    html = fetch_html(url)
    out_path = OUT_DIR / f"{team_slug}_{SPORTSREF_YEAR}.html"
    out_path.write_text(html, encoding="utf-8")


# -------------------------
# Main
# -------------------------

def main():
    ensure_out_dir()

    teams = get_sunbelt_teams()
    print(f"Found {len(teams)} Sun Belt teams for 2024-25:")
    for name, slug, url in teams:
        print(f" - {name} ({slug})")

    for name, slug, url in teams:
        save_team_page(name, slug, url)
        time.sleep(1.0)  # politeness delay


if __name__ == "__main__":
    main()
