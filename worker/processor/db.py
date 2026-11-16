"""Data access for the queue processor.

Talks to the jobs, job_sources and saved_filters tables from db/schema.sql.

Where the connection comes from:
- SQL_CONNECTION_STRING set  -> Azure SQL through pyodbc (production).
- otherwise                  -> a local SQLite file (LOCAL_SQLITE_PATH,
                                default worker/.local/tailormade.db), so the
                                processor and the demo run before Azure SQL
                                is provisioned.

pyodbc and sqlite3 both use "?" placeholders, so the queries below are
shared. The only dialect difference is how an INSERT returns the new id.
"""
import logging
import os
import sqlite3
import time
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_SQLITE_PATH = Path(__file__).resolve().parent.parent / ".local" / "tailormade.db"

# SQLite version of the three tables the processor needs. Column names and
# constraints match db/schema.sql so the code works unchanged on Azure SQL.
SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    dedupe_hash     TEXT NOT NULL UNIQUE,
    company         TEXT NOT NULL,
    title           TEXT NOT NULL,
    location        TEXT,
    is_remote       INTEGER NOT NULL DEFAULT 0,
    description     TEXT,
    posted_at       TEXT,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS job_sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    source          TEXT NOT NULL,
    source_job_id   TEXT NOT NULL,
    url             TEXT NOT NULL,
    fetched_at      TEXT NOT NULL,
    UNIQUE (source, source_job_id)
);
CREATE TABLE IF NOT EXISTS saved_filters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    name            TEXT NOT NULL,
    keywords        TEXT,
    locations       TEXT,
    remote_only     INTEGER NOT NULL DEFAULT 0,
    min_score       INTEGER NOT NULL DEFAULT 70,
    alerts_enabled  INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class JobRepository:
    """Thin wrapper around a DB-API connection (pyodbc or sqlite3)."""

    def __init__(self, conn, dialect):
        if dialect not in ("mssql", "sqlite"):
            raise ValueError(f"unknown dialect {dialect!r}")
        self.conn = conn
        self.dialect = dialect

    def _one(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        return cur.fetchone()

    # jobs

    def find_job_id(self, dedupe_hash):
        row = self._one("SELECT id FROM jobs WHERE dedupe_hash = ?", (dedupe_hash,))
        return row[0] if row else None

    def insert_job(self, job, now):
        columns = ("dedupe_hash, company, title, location, is_remote, description, "
                   "posted_at, first_seen_at, last_seen_at")
        values = (job["dedupe_hash"], job["company"], job["title"], job.get("location"),
                  1 if job.get("is_remote") else 0, job.get("description"),
                  job.get("posted_at"), now, now)
        if self.dialect == "mssql":
            sql = f"INSERT INTO jobs ({columns}) OUTPUT INSERTED.id VALUES (?,?,?,?,?,?,?,?,?)"
        else:
            sql = f"INSERT INTO jobs ({columns}) VALUES (?,?,?,?,?,?,?,?,?) RETURNING id"
        return int(self._one(sql, values)[0])

    def touch_job(self, job_id, now):
        self.conn.cursor().execute(
            "UPDATE jobs SET last_seen_at = ? WHERE id = ?", (now, job_id))

    # job_sources

    def source_exists(self, source, source_job_id):
        row = self._one(
            "SELECT 1 FROM job_sources WHERE source = ? AND source_job_id = ?",
            (source, source_job_id))
        return row is not None

    def insert_source(self, job_id, job, now):
        self.conn.cursor().execute(
            "INSERT INTO job_sources (job_id, source, source_job_id, url, fetched_at) "
            "VALUES (?,?,?,?,?)",
            (job_id, job["source"], job["source_job_id"], job.get("url") or "", now))

    # saved_filters

    def list_alert_filters(self):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, user_id, name, keywords, locations, remote_only, min_score "
            "FROM saved_filters WHERE alerts_enabled = 1")
        names = [c[0] for c in cur.description]
        return [dict(zip(names, row)) for row in cur.fetchall()]

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def connect_sqlite(path=None):
    path = Path(path or os.environ.get("LOCAL_SQLITE_PATH") or DEFAULT_SQLITE_PATH)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SQLITE_SCHEMA)
    return JobRepository(conn, "sqlite")


def is_waking_up(exc):
    """True for the errors a paused serverless database gives while it resumes.

    40613 = database not currently available, HYT00 = login timeout,
    08001 / 08S01 = connection refused or reset.
    """
    text = str(exc)
    return any(code in text for code in ("40613", "HYT00", "08001", "08S01"))


def connect_with_retry(open_conn, attempts=6, delay_seconds=10, sleep=time.sleep):
    """Call open_conn(), retrying while the database wakes from auto-pause.

    The free Azure SQL offer pauses after an hour idle and takes up to a
    minute to resume. Waiting here is cheaper than burning the queue
    message's retries, which sends it to the poison queue.
    """
    for attempt in range(1, attempts + 1):
        try:
            return open_conn()
        except Exception as exc:
            if attempt == attempts or not is_waking_up(exc):
                raise
            log.info("Database not ready (attempt %d/%d), retrying in %ds",
                     attempt, attempts, delay_seconds)
            sleep(delay_seconds)


def connect():
    """Open the repository for whatever database this environment has."""
    conn_str = os.environ.get("SQL_CONNECTION_STRING")
    if conn_str:
        import pyodbc  # only needed when talking to Azure SQL
        return JobRepository(connect_with_retry(lambda: pyodbc.connect(conn_str)), "mssql")
    log.warning("SQL_CONNECTION_STRING not set, using local SQLite fallback")
    return connect_sqlite()
