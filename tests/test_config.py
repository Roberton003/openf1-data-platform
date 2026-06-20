import os
from unittest.mock import mock_open, patch

from src.ingestion.config import DEFAULT_DRIVERS, _load_dotenv_local, parse_focus_drivers


class TestParseFocusDrivers:
    def test_none_returns_default(self):
        result = parse_focus_drivers(None)
        assert result == DEFAULT_DRIVERS

    def test_empty_string_returns_default(self):
        result = parse_focus_drivers("")
        assert result == DEFAULT_DRIVERS

    def test_single_driver(self):
        result = parse_focus_drivers("1:Max Verstappen")
        assert result == {1: "Max Verstappen"}

    def test_multiple_drivers(self):
        result = parse_focus_drivers("1:Max Verstappen,4:Lando Norris")
        assert result == {1: "Max Verstappen", 4: "Lando Norris"}

    def test_driver_number_only(self):
        result = parse_focus_drivers("1")
        assert result == {1: "Driver 1"}

    def test_driver_with_extra_spaces(self):
        result = parse_focus_drivers("  44 : Lewis Hamilton , 63 : George Russell  ")
        assert result == {44: "Lewis Hamilton", 63: "George Russell"}

    def test_invalid_format_returns_default(self):
        result = parse_focus_drivers("not-a-driver")
        assert result == DEFAULT_DRIVERS

    def test_empty_item_skipped(self):
        result = parse_focus_drivers("1:Max Verstappen,,4:Lando Norris")
        assert result == {1: "Max Verstappen", 4: "Lando Norris"}

    def test_invalid_number_returns_default(self):
        result = parse_focus_drivers("abc:Invalid")
        assert result == DEFAULT_DRIVERS


class TestLoadDotenvLocal:
    def test_loads_env_file(self):
        env_content = 'FOCUS_DRIVERS="1:Max Verstappen,4:Lando Norris"\nSECRET_KEY=abc123\n'
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=env_content)),
        ):
            _load_dotenv_local()
        assert os.getenv("FOCUS_DRIVERS") == "1:Max Verstappen,4:Lando Norris"
        assert os.getenv("SECRET_KEY") == "abc123"
        os.environ.pop("FOCUS_DRIVERS", None)
        os.environ.pop("SECRET_KEY", None)

    def test_no_env_file_does_nothing(self):
        with patch("os.path.exists", return_value=False):
            _load_dotenv_local()

    def test_skips_comments_and_empty(self):
        env_content = "# comment\n\nKEY=value\n"
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=env_content)),
        ):
            _load_dotenv_local()
        assert os.getenv("KEY") == "value"
        assert os.getenv("comment") is None
        os.environ.pop("KEY", None)
