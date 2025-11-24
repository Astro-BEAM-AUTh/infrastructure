"""Telescope command acknowledgment schema."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional

from dataclasses_avroschema import AvroModel


class AckStatus(StrEnum):
    """Acknowledgment status types."""

    RECEIVED = "received"  # Command received and queued
    STARTED = "started"  # Command execution started
    COMPLETED = "completed"  # Command completed successfully
    FAILED = "failed"  # Command execution failed
    REJECTED = "rejected"  # Command rejected (invalid parameters, etc.)
    TIMEOUT = "timeout"  # Command timed out


@dataclass
class CommandAcknowledgment(AvroModel):
    """
    Acknowledgment message sent from telescope applications to control center.

    This message is published to the 'telescope.acknowledgments' topic.
    """

    # Acknowledgment identification
    ack_id: str = field(metadata={"doc": "Unique identifier for this acknowledgment"})
    command_id: str = field(metadata={"doc": "ID of the command being acknowledged"})
    timestamp: int = field(
        metadata={"doc": "Unix timestamp in milliseconds when ack was sent"}
    )

    # Status information
    status: AckStatus = field(
        metadata={"doc": "Acknowledgment status (see AckStatus enum)"}
    )
    message: Optional[str] = field(
        default=None,
        metadata={"doc": "Human-readable status message or error description"},
    )

    # Source information
    source_application: str = field(
        default="",
        metadata={
            "doc": "Name of the application sending the acknowledgment (e.g., 'telescope-robotics', 'telescope-data-handler')"
        },
    )
    source_hostname: Optional[str] = field(
        default=None,
        metadata={"doc": "Hostname of the machine running the application"},
    )

    # Progress tracking (for long-running commands)
    progress_percent: Optional[float] = field(
        default=None,
        metadata={"doc": "Completion percentage (0-100) for in-progress commands"},
    )
    estimated_completion_time: Optional[int] = field(
        default=None, metadata={"doc": "Estimated completion timestamp in milliseconds"}
    )

    # Error details (for FAILED status)
    error_code: Optional[str] = field(
        default=None, metadata={"doc": "Error code if status is FAILED"}
    )
    error_details: Optional[str] = field(
        default=None, metadata={"doc": "Detailed error information if status is FAILED"}
    )
