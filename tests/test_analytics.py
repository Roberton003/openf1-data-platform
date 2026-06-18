from src.web.routers.analytics import fetch_drivers_from_db, fetch_sessions_from_db

SESSION_KEY = 10014


def test_fetch_sessions_from_db_returns_list(mock_db):
    results = fetch_sessions_from_db(mock_db)
    assert isinstance(results, list)
    assert len(results) > 0


def test_fetch_sessions_from_db_has_required_fields(mock_db):
    results = fetch_sessions_from_db(mock_db)
    for row in results:
        assert "session_key" in row
        assert "year" in row
        assert "session_name" in row
        assert "circuit_short_name" in row
        assert "country_name" in row


def test_fetch_sessions_from_db_bahrain_present(mock_db):
    results = fetch_sessions_from_db(mock_db)
    bahrain = [r for r in results if r.get("circuit_short_name") == "Bahrain GP"]
    assert len(bahrain) > 0


def test_fetch_drivers_from_db_returns_list(mock_db):
    results = fetch_drivers_from_db(mock_db, SESSION_KEY)
    assert isinstance(results, list)
    assert len(results) > 0


def test_fetch_drivers_from_db_has_required_fields(mock_db):
    results = fetch_drivers_from_db(mock_db, SESSION_KEY)
    for row in results:
        assert "driver_number" in row
        assert "full_name" in row
        assert "team_name" in row
        assert "name_acronym" in row


def test_fetch_drivers_from_db_hamilton_present(mock_db):
    results = fetch_drivers_from_db(mock_db, SESSION_KEY)
    hamilton = [r for r in results if r.get("full_name") == "Lewis Hamilton"]
    assert len(hamilton) > 0


def test_fetch_drivers_from_db_returns_acronyms(mock_db):
    results = fetch_drivers_from_db(mock_db, SESSION_KEY)
    acronyms = {r["name_acronym"] for r in results}
    assert "HAM" in acronyms
    assert "VER" in acronyms
