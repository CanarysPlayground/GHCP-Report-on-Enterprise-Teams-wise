#!/usr/bin/env python3
"""
GitHub Copilot Enterprise-Team Activity Report
------------------------------------------------
Reports Copilot seats that were granted via an Enterprise Team (i.e. teams
linked to Copilot licensing), along with each user's last Copilot activity.

Output columns: Enterprise Team Name, User Name, Last Activity At

Uses: GET /enterprises/{enterprise}/copilot/billing/seats
Auth: classic PAT with 'manage_billing:copilot' or 'read:enterprise' scope.

Usage:
    export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
    python copilot_team_activity_report.py <enterprise-slug> [output.csv]
"""

import csv
import os
import sys
import requests

API_VERSION = "2022-11-28"
BASE_URL = "https://api.github.com"


def get_headers(token: str) -> dict:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": API_VERSION,
    }


def paginated_seats(enterprise: str, headers: dict) -> list:
    """
    GET /enterprises/{enterprise}/copilot/billing/seats returns
    { total_seats, seats: [...] } and paginates via ?page=.
    """
    url = f"{BASE_URL}/enterprises/{enterprise}/copilot/billing/seats"
    all_seats = []
    page = 1
    while True:
        resp = requests.get(
            url, headers=headers, params={"per_page": 100, "page": page}
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Request failed: {resp.status_code} {resp.text}")
        data = resp.json()
        seats = data.get("seats", [])
        if not seats:
            break
        all_seats.extend(seats)
        if len(seats) < 100:
            break
        page += 1
    return all_seats


def main():
    if len(sys.argv) < 2:
        print("Usage: python copilot_team_activity_report.py <enterprise-slug> [output.csv]")
        sys.exit(1)

    enterprise = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "copilot_team_activity_report.csv"

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: set the GITHUB_TOKEN environment variable with a classic PAT.")
        sys.exit(1)

    headers = get_headers(token)

    print(f"Fetching Copilot seats for enterprise '{enterprise}'...")
    seats = paginated_seats(enterprise, headers)
    print(f"Retrieved {len(seats)} total seat(s).")

    rows = []
    for seat in seats:
        assigning_team = seat.get("assigning_team")
        # Only keep seats granted via an Enterprise Team (skip org- or
        # individually-assigned seats, which have assigning_team = null).
        if not assigning_team:
            continue

        team_name = assigning_team.get("name") or assigning_team.get("slug", "")
        assignee = seat.get("assignee") or {}
        user_name = assignee.get("login", "")
        last_activity = seat.get("last_activity_at") or "Never"

        rows.append({
            "Enterprise Team Name": team_name,
            "User Name": user_name,
            "Last Activity At": last_activity,
        })

    rows.sort(key=lambda r: (r["Enterprise Team Name"], r["User Name"]))

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Enterprise Team Name", "User Name", "Last Activity At"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nReport written to {output_path} ({len(rows)} rows across enterprise-team-linked seats).")


if __name__ == "__main__":
    main()
