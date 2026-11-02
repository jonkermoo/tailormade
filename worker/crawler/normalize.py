"""Turn raw postings from any source into one common job shape.

The dedupe hash is what lets us recognize the same job when it shows up
on more than one site: normalized company + title + city, run through
SHA-256. The database keeps a UNIQUE index on it.
"""
import hashlib
import re

# Suffixes that differ between sources for the same company
_COMPANY_SUFFIXES = re.compile(
    r"\b(inc|incorporated|llc|ltd|limited|corp|corporation|co|company|plc|gmbh)\b"
)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_REMOTE = re.compile(r"\b(remote|anywhere|work from home|wfh)\b")

MAX_DESCRIPTION_CHARS = 4000


def _squash(text):
    """Lowercase, drop punctuation, collapse whitespace."""
    return _NON_ALNUM.sub(" ", (text or "").lower()).strip()


def normalize_company(name):
    return " ".join(_COMPANY_SUFFIXES.sub(" ", _squash(name)).split())


def normalize_title(title):
    return _squash(title)


def normalize_city(location):
    """Reduce a location string to just the city, or 'remote'.

    "San Francisco, CA, United States" -> "san francisco"
    "Remote - US" -> "remote"
    """
    lowered = (location or "").lower()
    if _REMOTE.search(lowered):
        return "remote"
    first_part = lowered.split(",")[0].split(";")[0]
    return _squash(first_part)


def dedupe_hash(company, title, location):
    key = "|".join(
        [normalize_company(company), normalize_title(title), normalize_city(location)]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def make_job(source, source_job_id, company, title, location, url,
             posted_at=None, description=""):
    """Build the normalized job message that goes on the queue."""
    return {
        "source": source,
        "source_job_id": str(source_job_id),
        "company": (company or "").strip(),
        "title": (title or "").strip(),
        "location": (location or "").strip(),
        "url": url,
        "posted_at": posted_at,
        "description": (description or "")[:MAX_DESCRIPTION_CHARS],
        "dedupe_hash": dedupe_hash(company, title, location),
    }
