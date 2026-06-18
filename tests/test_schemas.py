import pytest
from pydantic import ValidationError

from src.ingestion.schemas import (
    DriverContract,
    OvertakeContract,
    RaceControlContract,
    SessionContract,
    SessionResultContract,
)


class TestSessionContract:
    def test_valid_session(self):
        s = SessionContract(
            session_key=10014,
            year=2025,
            session_name="Race",
            session_type="Race",
            circuit_key=12,
            circuit_short_name="Bahrain GP",
            country_name="Bahrain",
        )
        assert s.session_key == 10014

    def test_invalid_year_raises(self):
        with pytest.raises(ValidationError):
            SessionContract(
                session_key=1,
                year=1999,
                session_name="Race",
                session_type="Race",
                circuit_key=1,
                circuit_short_name="Test",
                country_name="Test",
            )


class TestDriverContract:
    def test_valid_driver(self):
        d = DriverContract(
            driver_number=44,
            full_name="Lewis Hamilton",
            name_acronym="HAM",
            team_name="Ferrari",
        )
        assert d.name_acronym == "HAM"

    def test_country_code_optional(self):
        d = DriverContract(
            driver_number=1,
            full_name="Max Verstappen",
            name_acronym="VER",
            team_name="Red Bull Racing",
        )
        assert d.country_code is None


class TestRaceControlContract:
    def test_valid_race_control(self):
        from datetime import datetime

        r = RaceControlContract(
            session_key=10014,
            category="Flag",
            message="Green flag",
            date=datetime(2025, 3, 16, 12, 0, 0),
        )
        assert r.category == "Flag"

    def test_driver_number_optional(self):
        from datetime import datetime

        r = RaceControlContract(
            session_key=10014,
            category="Flag",
            message="Test",
            date=datetime(2025, 3, 16, 12, 0, 0),
        )
        assert r.driver_number is None


class TestSessionResultContract:
    def test_valid_session_result(self):
        r = SessionResultContract(
            session_key=10014,
            driver_number=44,
            position=1,
            points=25.0,
        )
        assert r.points == 25.0

    def test_dnf_defaults_to_none(self):
        r = SessionResultContract(session_key=10014, driver_number=44)
        assert r.dnf is None


class TestOvertakeContract:
    def test_valid_overtake(self):
        from datetime import datetime

        o = OvertakeContract(
            session_key=10014,
            overtaking_driver_number=1,
            overtaken_driver_number=44,
            position=1,
            date=datetime(2025, 3, 16, 12, 10, 0),
        )
        assert o.overtaking_driver_number == 1

    def test_invalid_missing_date_raises(self):
        with pytest.raises(ValidationError):
            OvertakeContract(
                session_key=10014,
                overtaking_driver_number=1,
                overtaken_driver_number=44,
                position=1,
            )
