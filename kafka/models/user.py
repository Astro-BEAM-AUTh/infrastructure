"""User database model."""

from dataclasses import field
from datetime import UTC, datetime

from dataclasses_avroschema import AvroModel


def utc_now() -> datetime:
    """Get current UTC time as naive datetime."""
    return datetime.now(UTC).replace(tzinfo=None)


class UserBase(AvroModel):
    """Base model for users shared between API and database."""

    user_id: str = field(metadata={"doc": "Unique user identifier"})
    username: str = field(metadata={"doc": "Username"})
    email: str = field(metadata={"doc": "Email address"})

    id: int = field(metadata={"doc": "Database primary key"})
    is_active: bool = field(metadata={"doc": "Whether the user is active"})
    created_at: datetime = field(metadata={"doc": "Record creation timestamp"})
