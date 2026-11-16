from datetime import datetime, timezone

from processor.scoring import SavedFilter, guess_seniority, score_job

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)


def make_job(**overrides):
    job = {
        "title": "Software Engineer, Backend (New Grad)",
        "description": "Python services on Azure",
        "location": "Seattle, WA",
        "posted_at": "2026-11-15T08:00:00Z",
    }
    job.update(overrides)
    return job


def test_perfect_match_scores_100():
    f = SavedFilter(keywords=["backend"], locations=["Seattle"], seniority="entry")
    assert score_job(make_job(), f, now=NOW) == 100


def test_empty_filter_gives_full_points():
    assert score_job(make_job(), SavedFilter(), now=NOW) == 100


def test_score_is_always_between_0_and_100():
    f = SavedFilter(keywords=["rust", "golang"], locations=["Dublin"],
                    remote_only=True, seniority="senior")
    score = score_job(make_job(posted_at="2020-01-01T00:00:00Z"), f, now=NOW)
    assert 0 <= score <= 100
    assert score == 0


def test_title_keyword_beats_description_keyword():
    f = SavedFilter(keywords=["python"])
    in_title = score_job(make_job(title="Python Developer"), f, now=NOW)
    in_description = score_job(make_job(title="Developer"), f, now=NOW)
    assert in_title == 100
    assert in_description == 80   # keyword part drops from 40 to 20


def test_keyword_credit_is_shared_across_keywords():
    f = SavedFilter(keywords=["backend", "kotlin"])
    assert score_job(make_job(), f, now=NOW) == 80   # 1 of 2 keywords


def test_remote_only_filter_rejects_onsite_jobs():
    f = SavedFilter(remote_only=True)
    assert score_job(make_job(location="Remote - US"), f, now=NOW) == 100
    assert score_job(make_job(location="Seattle, WA"), f, now=NOW) == 75


def test_remote_job_gets_partial_credit_for_city_filter():
    f = SavedFilter(locations=["New York"])
    assert score_job(make_job(location="Remote"), f, now=NOW) == 95
    assert score_job(make_job(location="Austin, TX"), f, now=NOW) == 75


def test_older_postings_score_lower():
    f = SavedFilter()
    scores = [score_job(make_job(posted_at=d), f, now=NOW) for d in
              ("2026-11-15T00:00:00Z", "2026-11-13T00:00:00Z",
               "2026-11-09T00:00:00Z", "2026-11-02T00:00:00Z",
               "2026-10-01T00:00:00Z")]
    assert scores == [100, 95, 90, 85, 80]


def test_unknown_posting_date_gets_some_credit():
    assert score_job(make_job(posted_at=None), SavedFilter(), now=NOW) == 85


def test_seniority_one_level_off_gets_half():
    f = SavedFilter(seniority="intern")
    assert score_job(make_job(), f, now=NOW) == 92            # entry vs intern
    assert score_job(make_job(title="Staff Engineer"), f, now=NOW) == 85


def test_guess_seniority_from_title():
    assert guess_seniority("Software Engineering Intern") == "intern"
    assert guess_seniority("Junior Data Engineer") == "entry"
    assert guess_seniority("Sr. Backend Engineer") == "senior"
    assert guess_seniority("Software Engineer") == "mid"


def test_filter_from_saved_filters_row():
    row = {"id": 3, "user_id": 1, "name": "Seattle backend",
           "keywords": "backend, python", "locations": "Seattle,Remote",
           "remote_only": 0, "min_score": 80}
    f = SavedFilter.from_row(row)
    assert f.keywords == ["backend", "python"]
    assert f.locations == ["Seattle", "Remote"]
    assert f.remote_only is False
    assert f.min_score == 80
    assert f.seniority == ""
