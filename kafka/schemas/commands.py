"""Telescope command message schema."""

from dataclasses import dataclass, field
from enum import StrEnum

from dataclasses_avroschema import AvroModel

from models.observation import ObservationBase


class CommandType(StrEnum):
    """Types of commands that can be sent to telescope."""

    START_OBSERVATION = "start_observation"
    CANCEL_OBSERVATION = "cancel_observation"


@dataclass
class TelescopeCommand(AvroModel):
    """
    Command message sent from control center to telescope applications.

    This message is published to the 'telescope.commands' topic.
    """

    # Command identification
    command_id: str = field(
        default="",
        metadata={"doc": "Unique identifier for this command"},
    )
    command_type: str = field(
        default=CommandType.START_OBSERVATION.value,
        metadata={"doc": "Type of command to execute (see CommandType enum)"},
    )
    timestamp: int = field(
        default=0,
        metadata={"doc": "Unix timestamp in milliseconds when command was issued"},
    )

    # Observation parameters (for START_OBSERVATION commands)
    observation_request: ObservationBase = field(
        default=None,
        metadata={"doc": "Observation parameters (required for START_OBSERVATION)"},
    )
