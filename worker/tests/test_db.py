import pytest

from processor.db import connect_with_retry, is_waking_up

PAUSED = Exception("('HY000', \"[SQL Server]Database 'tailormade-db' is not currently "
                   "available. Please retry the connection later. (40613)\")")
TIMEOUT = Exception("('HYT00', '[ODBC Driver 18 for SQL Server]Login timeout expired')")
BAD_LOGIN = Exception("('28000', \"Login failed for user 'tailormadeadmin'. (18456)\")")


def flaky(failures):
    calls = {"n": 0}

    def open_conn():
        calls["n"] += 1
        if calls["n"] <= len(failures):
            raise failures[calls["n"] - 1]
        return "conn"
    return open_conn, calls


def test_waking_database_errors_are_recognised():
    assert is_waking_up(PAUSED)
    assert is_waking_up(TIMEOUT)
    assert not is_waking_up(BAD_LOGIN)


def test_retries_until_the_database_is_awake():
    open_conn, calls = flaky([PAUSED, TIMEOUT])
    waits = []
    assert connect_with_retry(open_conn, sleep=waits.append) == "conn"
    assert calls["n"] == 3
    assert waits == [10, 10]


def test_does_not_retry_a_wrong_password():
    open_conn, calls = flaky([BAD_LOGIN])
    with pytest.raises(Exception, match="Login failed"):
        connect_with_retry(open_conn, sleep=lambda s: None)
    assert calls["n"] == 1


def test_gives_up_after_the_last_attempt():
    open_conn, calls = flaky([PAUSED] * 10)
    with pytest.raises(Exception, match="40613"):
        connect_with_retry(open_conn, attempts=3, sleep=lambda s: None)
    assert calls["n"] == 3
