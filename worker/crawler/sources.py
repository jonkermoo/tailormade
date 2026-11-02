"""Fetchers for each job source.

We only use official, public APIs (no scraping):
- Greenhouse job boards: https://boards-api.greenhouse.io/v1/boards/{board}/jobs
- Lever postings:        https://api.lever.co/v0/postings/{company}?mode=json
- Adzuna search API:     https://developer.adzuna.com (needs a free app id + key)

Each source has a parse_* function (pure, easy to unit test) and a
fetch_* function that does the HTTP call and hands the payload to parse_*.
"""
from datetime import datetime, timezone

import requests

from .normalize import make_job

TIMEOUT_SECONDS = 20


def _get_json(url, params=None):
    resp = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.json()


# Greenhouse

def parse_greenhouse(board, payload):
    jobs = []
    for item in payload.get("jobs", []):
        jobs.append(make_job(
            source="greenhouse",
            source_job_id=item["id"],
            company=item.get("company_name") or board.title(),
            title=item.get("title"),
            location=(item.get("location") or {}).get("name"),
            url=item.get("absolute_url"),
            posted_at=item.get("first_published") or item.get("updated_at"),
        ))
    return jobs


def fetch_greenhouse(board):
    payload = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs")
    return payload, parse_greenhouse(board, payload)


# Lever

def parse_lever(company, payload):
    jobs = []
    for item in payload:
        created_ms = item.get("createdAt")
        posted_at = (
            datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc).isoformat()
            if created_ms else None
        )
        jobs.append(make_job(
            source="lever",
            source_job_id=item["id"],
            # Lever does not return a company name, so use the board name
            company=company.title(),
            title=item.get("text"),
            location=(item.get("categories") or {}).get("location"),
            url=item.get("hostedUrl"),
            posted_at=posted_at,
            description=item.get("descriptionPlain", ""),
        ))
    return jobs


def fetch_lever(company):
    payload = _get_json(f"https://api.lever.co/v0/postings/{company}", {"mode": "json"})
    return payload, parse_lever(company, payload)


# Adzuna

def parse_adzuna(payload):
    jobs = []
    for item in payload.get("results", []):
        jobs.append(make_job(
            source="adzuna",
            source_job_id=item["id"],
            company=(item.get("company") or {}).get("display_name"),
            title=item.get("title"),
            location=(item.get("location") or {}).get("display_name"),
            url=item.get("redirect_url"),
            posted_at=item.get("created"),
            description=item.get("description", ""),
        ))
    return jobs


def fetch_adzuna(app_id, app_key, what, country="us", results=50):
    payload = _get_json(
        f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",
        {
            "app_id": app_id,
            "app_key": app_key,
            "what": what,
            "results_per_page": results,
            "max_days_old": 1,
            "content-type": "application/json",
        },
    )
    return payload, parse_adzuna(payload)
