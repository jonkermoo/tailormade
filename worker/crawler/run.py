"""One crawl run: hit every configured source and collect the results.

Kept separate from function_app.py so it can be run and tested without
the Functions host (see `python -m crawler.run`).
"""
import logging
import os
from datetime import datetime, timezone

from . import sources

log = logging.getLogger(__name__)


def _csv_setting(name, default=""):
    return [v.strip() for v in os.environ.get(name, default).split(",") if v.strip()]


def _matches_keywords(job, keywords):
    if not keywords:
        return True
    title = job["title"].lower()
    return any(k.lower() in title for k in keywords)


def crawl():
    """Returns (snapshot, jobs).

    snapshot is the raw payload from every source, saved to Blob Storage
    as-is so a run can be inspected or replayed later. jobs is the list of
    normalized jobs to put on the queue.
    """
    started = datetime.now(timezone.utc)
    keywords = _csv_setting("CRAWL_KEYWORDS")
    snapshot = {"started_at": started.isoformat(), "sources": [], "errors": []}
    jobs = []

    calls = []
    for board in _csv_setting("GREENHOUSE_BOARDS", "stripe,discord"):
        calls.append(("greenhouse", board, lambda b=board: sources.fetch_greenhouse(b)))
    for company in _csv_setting("LEVER_COMPANIES", "spotify,palantir"):
        calls.append(("lever", company, lambda c=company: sources.fetch_lever(c)))

    adzuna_id = os.environ.get("ADZUNA_APP_ID")
    adzuna_key = os.environ.get("ADZUNA_APP_KEY")
    if adzuna_id and adzuna_key:
        what = os.environ.get("ADZUNA_QUERY", "software engineer")
        calls.append(("adzuna", what, lambda: sources.fetch_adzuna(adzuna_id, adzuna_key, what)))
    else:
        log.info("Adzuna skipped: ADZUNA_APP_ID / ADZUNA_APP_KEY not set")

    for source, target, fetch in calls:
        try:
            payload, found = fetch()
        except Exception as exc:  # one bad source should not stop the run
            log.warning("%s/%s failed: %s", source, target, exc)
            snapshot["errors"].append({"source": source, "target": target, "error": str(exc)})
            continue
        kept = [j for j in found if _matches_keywords(j, keywords)]
        log.info("%s/%s: %d jobs (%d after keyword filter)", source, target, len(found), len(kept))
        snapshot["sources"].append({"source": source, "target": target, "payload": payload})
        jobs.extend(kept)

    snapshot["finished_at"] = datetime.now(timezone.utc).isoformat()
    snapshot["job_count"] = len(jobs)
    return snapshot, jobs


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    _, found_jobs = crawl()
    print(f"\n{len(found_jobs)} jobs found. First few:")
    for job in found_jobs[:5]:
        print(f"  [{job['source']}] {job['company']} - {job['title']} ({job['location']})")
