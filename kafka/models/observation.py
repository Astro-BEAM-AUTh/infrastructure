"""Telescope observation database model."""

from dataclasses import field
from datetime import UTC, datetime

from dataclasses_avroschema import AvroModel

from models.user import UserBase as User


def utc_now() -> datetime:
    """Get current UTC time as naive datetime."""
    return datetime.now(UTC).replace(tzinfo=None)


class ObservationBase(AvroModel):
    """Base model for telescope observations shared between API and database."""

    # Observation target information
    target_name: str = field(metadata={"doc": "Name of the observation target"})
    observation_object: str = field(metadata={"doc": "Object being observed"})
    ra: float = field(metadata={"doc": "Right Ascension in degrees"})
    dec: float = field(metadata={"doc": "Declination in degrees"})

    # Telescope configuration
    center_frequency: float = field(metadata={"doc": "Center frequency in MHz"})
    rf_gain: float = field(metadata={"doc": "RF gain in dB"})
    if_gain: float = field(metadata={"doc": "IF gain in dB"})
    bb_gain: float = field(metadata={"doc": "Baseband gain in dB"})
    observation_type: str = field(metadata={"doc": "Type of observation"})
    integration_time: float = field(metadata={"doc": "Integration time in seconds"})

    # Output information
    output_filename: str = field(metadata={"doc": "Filename for the observation data"})

    id: int | None = field(
        default=None,
        metadata={"doc": "Database primary key"},
    )
    observation_id: str = field(
        default="",
        metadata={"doc": "Unique observation identifier"},
    )

    # User relationship
    user_id: int = field(
        default=0,
        metadata={"doc": "ID of the user who submitted the observation"},
    )
    user: User = field(
        default=None,
        metadata={"doc": "User who submitted the observation"},
    )

    # Status tracking
    status: str = field(
        default="pending",
        metadata={"doc": "Current observation status"},
    )
    submitted_at: datetime = field(
        default_factory=utc_now, metadata={"doc": "Timestamp of submission"}
    )
    completed_at: datetime | None = field(
        default=None, metadata={"doc": "Timestamp of completion"}
    )

    # Additional metadata
    created_at: datetime = field(
        default_factory=utc_now, metadata={"doc": "Record creation timestamp"}
    )
    updated_at: datetime = field(
        default_factory=utc_now, metadata={"doc": "Record update timestamp"}
    )
