from crawler.normalize import (
    dedupe_hash,
    normalize_city,
    normalize_company,
    normalize_title,
)
from crawler.sources import parse_greenhouse, parse_lever


def test_company_suffixes_are_dropped():
    assert normalize_company("Stripe, Inc.") == "stripe"
    assert normalize_company("Acme Corporation") == "acme"
    assert normalize_company("  Palantir Technologies LLC ") == "palantir technologies"


def test_title_ignores_case_and_punctuation():
    assert normalize_title("Software Engineer, Backend (New Grad)") == \
        normalize_title("software engineer - backend new grad")


def test_city_keeps_only_the_city():
    assert normalize_city("San Francisco, CA, United States") == "san francisco"
    assert normalize_city("New York; Remote-friendly") == "remote"
    assert normalize_city("Remote - US") == "remote"
    assert normalize_city(None) == ""


def test_same_job_on_two_sites_gets_same_hash():
    a = dedupe_hash("Stripe, Inc.", "Software Engineer, Payments", "Seattle, WA")
    b = dedupe_hash("stripe", "Software Engineer - Payments", "Seattle")
    assert a == b


def test_different_city_gets_different_hash():
    a = dedupe_hash("Stripe", "Software Engineer", "Seattle, WA")
    b = dedupe_hash("Stripe", "Software Engineer", "Dublin")
    assert a != b


def test_hash_is_sha256_hex():
    h = dedupe_hash("x", "y", "z")
    assert len(h) == 64
    int(h, 16)


def test_parse_greenhouse_payload():
    payload = {"jobs": [{
        "id": 123,
        "title": "Data Analyst",
        "company_name": "Stripe",
        "location": {"name": "Chicago, IL"},
        "absolute_url": "https://example.com/123",
        "first_published": "2026-10-01T00:00:00Z",
    }]}
    [job] = parse_greenhouse("stripe", payload)
    assert job["source"] == "greenhouse"
    assert job["source_job_id"] == "123"
    assert job["company"] == "Stripe"
    assert job["dedupe_hash"] == dedupe_hash("Stripe", "Data Analyst", "Chicago")


def test_parse_lever_payload_uses_board_name_as_company():
    payload = [{
        "id": "abc",
        "text": "Backend Engineer",
        "categories": {"location": "Remote"},
        "hostedUrl": "https://example.com/abc",
        "createdAt": 1767225600000,
        "descriptionPlain": "x" * 10000,
    }]
    [job] = parse_lever("spotify", payload)
    assert job["company"] == "Spotify"
    assert job["posted_at"].startswith("2026-01-01")
    assert len(job["description"]) == 4000
