"""Score how well a job matches a saved filter, from 0 to 100.

Weights (they add up to 100):

    keywords   40  Share of the filter's keywords found in the job. A hit in
                   the title counts fully, a hit only in the description
                   counts half, because titles are what people search by.
    location   25  Full points if the job is in one of the filter's cities.
                   A remote job gets 20 of 25 when the filter lists cities
                   (still workable, just not what was asked for). If the
                   filter is remote-only, only remote jobs get points.
    recency    20  Fresh postings get more responses: <=1 day 20, <=3 days 15,
                   <=7 days 10, <=14 days 5, older 0. Unknown date gets 5.
    seniority  15  Level guessed from the title (intern / entry / mid /
                   senior). Exact match 15, one level off 7, otherwise 0.

A criterion the filter leaves empty gets full points, so a filter with only
keywords is judged on keywords. The function is pure (no I/O, "now" can be
passed in) so it is easy to test.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from crawler.normalize import normalize_city

W_KEYWORDS = 40
W_LOCATION = 25
W_RECENCY = 20
W_SENIORITY = 15
REMOTE_PARTIAL = 20

DEFAULT_MIN_SCORE = 70  # saved_filters.min_score default

SENIORITY_LEVELS = ["intern", "entry", "mid", "senior"]
_SENIORITY_PATTERNS = [
    ("intern", re.compile(r"\b(intern|internship|co-?op)\b")),
    ("entry", re.compile(r"\b(new grad|graduate|junior|jr|entry|associate|early career)\b|\bi\b")),
    ("senior", re.compile(r"\b(senior|sr|staff|principal|lead|manager|director|head)\b")),
]
_RECENCY_STEPS = [(1, 20), (3, 15), (7, 10), (14, 5)]
UNKNOWN_DATE_POINTS = 5


def _split_csv(value):
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [v.strip() for v in value if v and v.strip()]
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass
class SavedFilter:
    keywords: list = field(default_factory=list)
    locations: list = field(default_factory=list)
    remote_only: bool = False
    seniority: str = ""          # one of SENIORITY_LEVELS, or "" for any
    min_score: int = DEFAULT_MIN_SCORE
    id: int = None
    user_id: int = None
    name: str = ""

    @classmethod
    def from_row(cls, row):
        """Build from a saved_filters row (dict of column -> value)."""
        return cls(
            keywords=_split_csv(row.get("keywords")),
            locations=_split_csv(row.get("locations")),
            remote_only=bool(row.get("remote_only")),
            seniority=(row.get("seniority") or "").lower(),
            min_score=int(row.get("min_score") or DEFAULT_MIN_SCORE),
            id=row.get("id"),
            user_id=row.get("user_id"),
            name=row.get("name") or "",
        )


def guess_seniority(title):
    lowered = (title or "").lower()
    for level, pattern in _SENIORITY_PATTERNS:
        if pattern.search(lowered):
            return level
    return "mid"


def _parse_time(value):
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def keyword_points(job, keywords):
    if not keywords:
        return W_KEYWORDS
    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    credit = 0.0
    for kw in keywords:
        kw = kw.lower()
        if kw in title:
            credit += 1.0
        elif kw in description:
            credit += 0.5
    return W_KEYWORDS * credit / len(keywords)


def location_points(job, locations, remote_only):
    city = normalize_city(job.get("location"))
    is_remote = city == "remote"
    if remote_only:
        return W_LOCATION if is_remote else 0
    if not locations:
        return W_LOCATION
    if any(normalize_city(loc) == city for loc in locations):
        return W_LOCATION
    return REMOTE_PARTIAL if is_remote else 0


def recency_points(posted_at, now):
    posted = _parse_time(posted_at)
    if posted is None:
        return UNKNOWN_DATE_POINTS
    age_days = (now - posted).total_seconds() / 86400
    for max_days, points in _RECENCY_STEPS:
        if age_days <= max_days:
            return points
    return 0


def seniority_points(title, wanted):
    if not wanted:
        return W_SENIORITY
    if wanted not in SENIORITY_LEVELS:
        return W_SENIORITY
    distance = abs(SENIORITY_LEVELS.index(guess_seniority(title)) -
                   SENIORITY_LEVELS.index(wanted))
    if distance == 0:
        return W_SENIORITY
    return 7 if distance == 1 else 0


def score_job(job, saved_filter, now=None):
    """Return an int score 0-100 for one job against one SavedFilter."""
    now = _parse_time(now) or datetime.now(timezone.utc)
    total = (
        keyword_points(job, saved_filter.keywords)
        + location_points(job, saved_filter.locations, saved_filter.remote_only)
        + recency_points(job.get("posted_at"), now)
        + seniority_points(job.get("title"), saved_filter.seniority)
    )
    return max(0, min(100, round(total)))
