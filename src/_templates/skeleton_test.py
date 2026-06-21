"""pytest template — fixture, parametrize, edge cases."""

import pytest
from pydantic import ValidationError

from src._templates.skeleton_model import EntityModel


@pytest.fixture
def valid_entity_data() -> dict:
    """Default valid data for EntityModel."""
    return {"id": 1, "name": "Test Entity", "email": "test@example.com"}


class TestEntityModel:
    """Tests for EntityModel validation."""

    def test_valid_entity(self, valid_entity_data: dict):
        entity = EntityModel(**valid_entity_data)
        assert entity.id == 1
        assert entity.name == "Test Entity"

    def test_empty_name_raises(self, valid_entity_data: dict):
        data = {**valid_entity_data, "name": "   "}
        with pytest.raises(ValidationError, match="name must not be empty"):
            EntityModel(**data)

    def test_invalid_email_none_accepted(self, valid_entity_data: dict):
        data = {**valid_entity_data, "email": None}
        entity = EntityModel(**data)
        assert entity.email is None

    @pytest.mark.parametrize(
        "field,value,expected_error",
        [
            ("id", 0, "greater than or equal to 1"),
            ("id", -5, "greater than or equal to 1"),
            ("name", "", "must not be empty"),
            ("name", "a" * 201, "max_length"),
        ],
    )
    def test_field_constraints(self, valid_entity_data: dict, field: str, value, expected_error: str):
        data = {**valid_entity_data, field: value}
        with pytest.raises(ValidationError, match=expected_error):
            EntityModel(**data)
