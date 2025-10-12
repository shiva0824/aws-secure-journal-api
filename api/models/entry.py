from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime
from uuid import uuid4
import re


class EntryCreate(BaseModel):
    """Model for creating a new journal entry (user input)."""
    work: str = Field(
        max_length=256,
        description="What did you work on today?",
        json_schema_extra={
            "example": "Studied FastAPI and built my first API endpoints"}
    )
    struggle: str = Field(
        max_length=256,
        description="What's one thing you struggled with today?",
        json_schema_extra={
            "example": "Understanding async/await syntax and when to use it"}
    )
    intention: str = Field(
        max_length=256,
        description="What will you study/work on tomorrow?",
        json_schema_extra={
            "example": "Practice PostgreSQL queries and database design"}
    )


class Entry(BaseModel):
    # TODO: Add field validation rules
    # TODO: Add custom validators
    # TODO: Add schema versioning
    # TODO: Add data sanitization methods

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the entry (UUID)."
    )
    work: str = Field(
        min_length=1,
        max_length=256,
        description="What did you work on today?"
    )
    struggle: str = Field(
        min_length=1,
        max_length=256,
        description="What’s one thing you struggled with today?"
    )
    intention: str = Field(
        min_length=1,
        max_length=256,
        description="What will you study/work on tomorrow?"
    )
    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the entry was created."
    )
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the entry was last updated."
    )

    # Intial version for the entry model
    schema_version: int = Field(default=1)

    # Data sanitization methods and custom validators
    # 1. Prevent harmful html injection (sanitize before validation)
    @model_validator(mode="before")
    @classmethod
    def sanitize_before_validation(cls, data: dict):
        if isinstance(data, dict):
            for key in ["work", "struggle", "intention"]:
                if key in data and isinstance(data[key], str):
                    # Escape < and > to prevent script/HTML injection
                    text = data[key].replace("<", "&lt;").replace(">", "&gt;")
                    data[key] = text
        return data

    # 2. Disallow empty or only whitespace as input (validate before)
    @field_validator("work", "struggle", "intention", mode="before")
    def strip_and_validate_text(cls, val):
        if not val or not val.strip():
            raise ValueError(
                "Whitespaces are not supported or the value cannot be empty")
        return val.strip()

    # 3. Normalize whitespace (sanitize after validation)
    @field_validator("work", "struggle", "intention", mode="after")
    def normalize_whitespace(cls, val: str) -> str:
        # Collapse multiple spaces into one and strip edges
        return re.sub(r"\s+", " ", val).strip()

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }
