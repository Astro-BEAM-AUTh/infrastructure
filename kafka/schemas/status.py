"""Telescope status update schema."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional

from dataclasses_avroschema import AvroModel


class StatusLevel(StrEnum):
    """Status severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TelescopeStatus(AvroModel):
    """
    Status update message from telescope applications.

    This message is published to the 'telescope.status' topic for monitoring.
    """

    # Status identification
    status_id: str = field(metadata={"doc": "Unique identifier for this status update"})
    timestamp: int = field(
        metadata={"doc": "Unix timestamp in milliseconds when status was generated"}
    )

    # Source information
    source_application: str = field(
        default="",
        metadata={
            "doc": "Name of the application (e.g., 'telescope-robotics', 'telescope-data-handler')"
        },
    )
    source_hostname: Optional[str] = field(
        default=None,
        metadata={"doc": "Hostname of the machine"},
    )

    # Status details
    level: StatusLevel = field(
        default=StatusLevel.INFO,
        metadata={"doc": "Status severity level (see StatusLevel enum)"},
    )
    component: str = field(
        default="",
        metadata={"doc": "Component or subsystem this status relates to"},
    )
    message: str = field(
        default="",
        metadata={"doc": "Human-readable status message"},
    )

    # Current state
    is_operational: bool = field(
        default=True,
        metadata={"doc": "Whether the component is operational"},
    )
    current_observation_id: Optional[str] = field(
        default=None, metadata={"doc": "ID of currently running observation if any"}
    )

    # System metrics
    cpu_usage_percent: Optional[float] = field(
        default=None, metadata={"doc": "CPU usage percentage"}
    )
    memory_usage_percent: Optional[float] = field(
        default=None, metadata={"doc": "Memory usage percentage"}
    )
    disk_usage_percent: Optional[float] = field(
        default=None, metadata={"doc": "Disk usage percentage"}
    )

    # Additional context
    error_code: Optional[str] = field(
        default=None, metadata={"doc": "Error code if level is ERROR or CRITICAL"}
    )
    additional_info: Optional[str] = field(
        default=None,
        metadata={"doc": "String with additional contextual information"},
    )
