"""What happens to one job taken off the queue.

1. Clean it up: recompute the dedupe hash, set is_remote, store posted_at
   in UTC.
2. Upsert it into jobs / job_sources (see upsert.py).
3. Score it against every saved filter that has alerts on.

Used by the queue trigger in function_app.py and by `python -m processor.demo`.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone

from crawler.normalize import dedupe_hash, normalize_city

from .scoring import SavedFilter, score_job
from .upsert import upsert_job


@dataclass
class ProcessResult:
    job: dict
    job_id: int
    status: str                                  # new / duplicate / seen
    scores: dict = field(default_factory=dict)   # filter id -> score

    @property
    def best_score(self):
        return max(self.scores.values(), default=None)


def _to_utc_string(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def prepare_job(job):
    job = dict(job)
    # Recompute rather than trust the message, so the rule lives in one place
    job["dedupe_hash"] = dedupe_hash(job["company"], job["title"], job.get("location"))
    job["is_remote"] = normalize_city(job.get("location")) == "remote"
    job["posted_at"] = _to_utc_string(job.get("posted_at"))
    return job


def load_filters(repo):
    return [SavedFilter.from_row(row) for row in repo.list_alert_filters()]


def process_job(repo, job, filters, now=None):
    """Store and score one job. The caller commits."""
    job = prepare_job(job)
    result = upsert_job(repo, job)
    scores = {f.id: score_job(job, f, now=now) for f in filters}
    return ProcessResult(job=job, job_id=result.job_id, status=result.status, scores=scores)
