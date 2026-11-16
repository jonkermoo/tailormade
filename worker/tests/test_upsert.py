from crawler.normalize import make_job
from processor import db
from processor.pipeline import process_job
from processor.scoring import SavedFilter
from processor.upsert import DUPLICATE, NEW, SEEN, upsert_job


class FakeRepo:
    """In-memory stand-in for JobRepository."""

    def __init__(self):
        self.jobs = {}       # id -> job
        self.sources = []    # (job_id, source, source_job_id)
        self.touched = []

    def find_job_id(self, dedupe_hash):
        for job_id, job in self.jobs.items():
            if job["dedupe_hash"] == dedupe_hash:
                return job_id
        return None

    def insert_job(self, job, now):
        job_id = len(self.jobs) + 1
        self.jobs[job_id] = job
        return job_id

    def touch_job(self, job_id, now):
        self.touched.append(job_id)

    def source_exists(self, source, source_job_id):
        return any(s[1:] == (source, source_job_id) for s in self.sources)

    def insert_source(self, job_id, job, now):
        self.sources.append((job_id, job["source"], job["source_job_id"]))


STRIPE_GH = make_job("greenhouse", 101, "Stripe, Inc.", "Software Engineer, Payments",
                     "Seattle, WA", "https://example.com/gh/101")
STRIPE_ADZUNA = make_job("adzuna", "A9", "Stripe", "Software Engineer - Payments",
                         "Seattle", "https://example.com/adz/A9")
STRIPE_DUBLIN = make_job("greenhouse", 102, "Stripe", "Software Engineer, Payments",
                         "Dublin, Ireland", "https://example.com/gh/102")


def test_first_sighting_inserts_job_and_source():
    repo = FakeRepo()
    result = upsert_job(repo, STRIPE_GH)
    assert result.status == NEW and result.is_new
    assert len(repo.jobs) == 1
    assert repo.sources == [(result.job_id, "greenhouse", "101")]


def test_same_job_on_another_site_adds_only_a_source():
    repo = FakeRepo()
    first = upsert_job(repo, STRIPE_GH)
    second = upsert_job(repo, STRIPE_ADZUNA)
    assert second.status == DUPLICATE
    assert second.job_id == first.job_id
    assert len(repo.jobs) == 1
    assert len(repo.sources) == 2


def test_recrawl_of_same_posting_only_bumps_last_seen():
    repo = FakeRepo()
    first = upsert_job(repo, STRIPE_GH)
    again = upsert_job(repo, STRIPE_GH)
    assert again.status == SEEN
    assert len(repo.sources) == 1
    assert repo.touched == [first.job_id]


def test_same_title_in_another_city_is_a_different_job():
    repo = FakeRepo()
    upsert_job(repo, STRIPE_GH)
    other = upsert_job(repo, STRIPE_DUBLIN)
    assert other.status == NEW
    assert len(repo.jobs) == 2


def test_process_job_scores_against_each_filter():
    repo = FakeRepo()
    filters = [SavedFilter(id=1, keywords=["payments"], locations=["Seattle"]),
               SavedFilter(id=2, keywords=["ios"], remote_only=True)]
    result = process_job(repo, STRIPE_GH, filters, now="2026-11-15T00:00:00Z")
    assert result.status == NEW
    assert result.scores[1] > result.scores[2]
    assert result.best_score == result.scores[1]
    assert result.job["is_remote"] is False


def test_sqlite_repository_runs_the_same_flow():
    repo = db.connect_sqlite(":memory:")
    assert upsert_job(repo, STRIPE_GH).status == NEW
    assert upsert_job(repo, STRIPE_ADZUNA).status == DUPLICATE
    assert upsert_job(repo, STRIPE_ADZUNA).status == SEEN
    repo.commit()
    cur = repo.conn.cursor()
    assert cur.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    assert cur.execute("SELECT COUNT(*) FROM job_sources").fetchone()[0] == 2
