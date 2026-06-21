"""Pydantic model template — Field, field_validator, model_config."""

from pydantic import BaseModel, Field, field_validator, model_validator


class EntityModel(BaseModel):
    """Business entity with validated fields."""

    id: int = Field(..., ge=1, description="Unique identifier")
    name: str = Field(..., min_length=1, max_length=200, description="Display name")
    email: str | None = Field(None, pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be empty or whitespace")
        return v.strip()

    @model_validator(mode="after")
    def validate_consistency(self) -> "EntityModel":
        """Cross-field validation."""
        return self
