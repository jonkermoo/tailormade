"""Write one crawled job into the database without creating duplicates.

The same real-world job can arrive many times: from another site (Stripe
posts on Greenhouse and it also shows up on Adzuna) or from the same site on
the next crawl. jobs.dedupe_hash is UNIQUE, so we look the hash up first:

- hash not seen yet          -> insert into jobs + job_sources   ("new")
- hash seen, new source row  -> add a job_sources row only       ("duplicate")
- hash and source both seen  -> just bump jobs.last_seen_at      ("seen")
"""
from dataclasses import dataclass
from datetime import datetime, timezone

NEW = "new"
DUPLICATE = "duplicate"
SEEN = "seen"


@dataclass
class UpsertResult:
    job_id: int
    status: str  # NEW, DUPLICATE or SEEN

    @property
    def is_new(self):
        return self.status == NEW


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _is_unique_violation(exc):
    # pyodbc and sqlite3 each have their own IntegrityError class
    return type(exc).__name__ == "IntegrityError"


def upsert_job(repo, job, now=None):
    """Insert or update one job. The caller commits."""
    now = now or _now()
    job_id = repo.find_job_id(job["dedupe_hash"])

    if job_id is None:
        try:
            job_id = repo.insert_job(job, now)
        except Exception as exc:
            # Two copies of the same job processed at the same moment: both
            # saw no row, the other insert won the UNIQUE index. Fall
            # through and record this one as a duplicate of that row.
            if not _is_unique_violation(exc):
                raise
            job_id = repo.find_job_id(job["dedupe_hash"])
            if job_id is None:
                raise
        else:
            repo.insert_source(job_id, job, now)
            return UpsertResult(job_id, NEW)

    repo.touch_job(job_id, now)
    if repo.source_exists(job["source"], job["source_job_id"]):
        return UpsertResult(job_id, SEEN)
    repo.insert_source(job_id, job, now)
    return UpsertResult(job_id, DUPLICATE)
