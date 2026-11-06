"""User-facing HTTP API, deployed as the Static Web Apps managed API.

Endpoints for jobs, saved filters, the application tracker and resume
tailoring will live here.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Sample data until the jobs table in Azure SQL is ready.
# Field names follow the jobs table in db/schema.sql; url comes from job_sources.
SAMPLE_JOBS_PATH = Path(__file__).parent / "sample_jobs.json"


def _json_response(body, status_code=200):
    return func.HttpResponse(
        json.dumps(body), status_code=status_code, mimetype="application/json"
    )


@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    body = {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}
    return _json_response(body)


@app.route(route="jobs", methods=["GET"])
def jobs(req: func.HttpRequest) -> func.HttpResponse:
    """Return the job feed. Optional ?q=engineer filters by title."""
    with open(SAMPLE_JOBS_PATH, encoding="utf-8") as f:
        all_jobs = json.load(f)

    q = (req.params.get("q") or "").strip().lower()
    if q:
        results = [job for job in all_jobs if q in job["title"].lower()]
    else:
        results = all_jobs

    # Newest first, same order the feed will use once it reads from SQL
    results.sort(key=lambda job: job["posted_at"], reverse=True)

    return _json_response({"count": len(results), "jobs": results})