"""Run a crawl sample through dedupe, the database and scoring, and print a table.

    python -m processor.demo                  # bundled sample, fresh SQLite db
    python -m processor.demo --live           # crawl the real APIs instead
    python -m processor.demo --snapshot f.json  # replay a raw-crawls snapshot

Writes to the local SQLite file (worker/.local/demo.db, recreated each run)
unless SQL_CONNECTION_STRING is set, in which case it writes to Azure SQL.
"""
import argparse
import json
import logging
import os
from pathlib import Path

from crawler import sources
from crawler.run import crawl

from . import db
from .pipeline import process_job
from .scoring import SavedFilter
from .upsert import DUPLICATE

SAMPLE_PATH = Path(__file__).parent / "sample_crawl.json"
DEMO_DB_PATH = db.DEFAULT_SQLITE_PATH.parent / "demo.db"

DEMO_FILTER = SavedFilter(
    id=1, name="New grad backend",
    keywords=["backend", "python"], locations=["Seattle", "New York"],
    seniority="entry",
)


def jobs_from_snapshot(snapshot):
    jobs = []
    for entry in snapshot["sources"]:
        source, target, payload = entry["source"], entry["target"], entry["payload"]
        if source == "greenhouse":
            jobs += sources.parse_greenhouse(target, payload)
        elif source == "lever":
            jobs += sources.parse_lever(target, payload)
        elif source == "adzuna":
            jobs += sources.parse_adzuna(payload)
    return jobs


def _cut(text, width):
    text = text or ""
    return text if len(text) <= width else text[: width - 3] + "..."


def print_table(results):
    header = f"{'Job':<40} {'Company':<12} {'Source':<11} {'Score':>5}  Duplicate"
    print(header)
    print("-" * len(header))
    # Group each duplicate under the job it was merged into, best jobs first
    group_best = {}
    for r in results:
        group_best[r.job_id] = max(group_best.get(r.job_id, 0), r.best_score)
    for r in sorted(results, key=lambda r: (-group_best[r.job_id], r.job_id,
                                            r.status == DUPLICATE)):
        dup = f"yes (job {r.job_id})" if r.status == DUPLICATE else "no"
        print(f"{_cut(r.job['title'], 40):<40} {_cut(r.job['company'], 12):<12} "
              f"{r.job['source']:<11} {r.best_score:>5}  {dup}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--live", action="store_true", help="crawl the real APIs")
    parser.add_argument("--snapshot", type=Path, help="replay a raw-crawls JSON file")
    args = parser.parse_args()

    if args.live:
        snapshot, jobs = crawl()
    else:
        snapshot = json.loads((args.snapshot or SAMPLE_PATH).read_text(encoding="utf-8"))
        jobs = jobs_from_snapshot(snapshot)
    now = None if args.live else snapshot.get("started_at")

    if os.environ.get("SQL_CONNECTION_STRING"):
        repo, where = db.connect(), "Azure SQL"
    else:
        DEMO_DB_PATH.unlink(missing_ok=True)
        repo, where = db.connect_sqlite(DEMO_DB_PATH), f"SQLite ({DEMO_DB_PATH.name})"

    results = [process_job(repo, job, [DEMO_FILTER], now=now) for job in jobs]
    repo.commit()

    cur = repo.conn.cursor()
    cur.execute("SELECT COUNT(*) FROM jobs")
    job_rows = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM job_sources")
    source_rows = cur.fetchone()[0]
    repo.close()

    f = DEMO_FILTER
    print(f"\nFilter \"{f.name}\": keywords={','.join(f.keywords)}  "
          f"locations={','.join(f.locations)}  seniority={f.seniority}  "
          f"min_score={f.min_score}\n")
    print_table(results)
    dupes = sum(r.status == DUPLICATE for r in results)
    strong = sum(r.best_score >= f.min_score for r in results if r.status != DUPLICATE)
    print(f"\n{len(results)} postings -> {job_rows} jobs + {source_rows} sources in {where}. "
          f"{dupes} duplicates merged, {strong} jobs at or above {f.min_score}.\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    main()
