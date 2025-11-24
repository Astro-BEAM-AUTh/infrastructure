"""Telescope observation data schema."""

from dataclasses import dataclass, field
from typing import Optional

from dataclasses_avroschema import AvroModel


@dataclass
class TelescopeData(AvroModel):
    """
    Telescope observation data message.

    This message is published to the 'telescope.data' topic and
    is consumed by Kafka Connect to insert into PostgreSQL.
    """

    # Data identification
    data_id: str = field(metadata={"doc": "Unique identifier for this data record"})
    observation_id: str = field(
        metadata={"doc": "ID of the observation this data belongs to"}
    )
    sequence_number: int = field(
        metadata={"doc": "Sequence number within the observation (for chunked data)"}
    )
    timestamp: int = field(
        metadata={"doc": "Unix timestamp in milliseconds when data was captured"}
    )

    # Observation data payload
    data_payload: Optional[bytes] = field(
        default=None,
        metadata={"doc": "Binary payload of the observation data (e.g., image bytes)"},
    )
