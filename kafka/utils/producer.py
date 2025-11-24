"""Kafka Avro producer utility."""

import asyncio
import io
import logging
import struct
from typing import Generic, TypeVar

import httpx
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
from dataclasses_avroschema import AvroModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=AvroModel)

# Magic byte for Confluent Schema Registry wire format
MAGIC_BYTE = 0


class KafkaAvroProducer(Generic[T]):
    """
    Async Kafka producer for Avro-serialized messages with Schema Registry.

    This producer handles serialization of dataclass messages to Avro format,
    registers schemas with Schema Registry, and publishes messages to Kafka topics.

    Example:
        >>> from schemas.commands import TelescopeCommand
        >>> producer = KafkaAvroProducer[TelescopeCommand](
        ...     bootstrap_servers='localhost:9092',
        ...     schema_registry_url='http://localhost:8081',
        ...     topic='telescope.commands',
        ...     schema_class=TelescopeCommand
        ... )
        >>> await producer.start()
        >>> command = TelescopeCommand(
        ...     command_id="cmd-001",
        ...     command_type="start_observation",
        ...     timestamp=int(datetime.now().timestamp() * 1000),
        ...     issued_by="user-123"
        ... )
        >>> await producer.send(command, key="cmd-001")
        >>> await producer.stop()
    """

    def __init__(
        self,
        bootstrap_servers: str | list[str],
        schema_registry_url: str,
        topic: str,
        schema_class: type[T],
        client_id: str | None = None,
        compression_type: str = "snappy",
        max_batch_size: int = 16384,
        linger_ms: int = 10,
    ):
        """
        Initialize Kafka Avro producer.

        Args:
            bootstrap_servers: Kafka broker addresses
            schema_registry_url: URL of Schema Registry
            topic: Topic to produce messages to
            schema_class: Avro schema class for messages
            client_id: Client identifier for Kafka
            compression_type: Compression algorithm (snappy, gzip, lz4, zstd)
            max_batch_size: Maximum batch size in bytes
            linger_ms: Time to wait for additional messages before sending batch
        """
        self.bootstrap_servers = bootstrap_servers
        self.schema_registry_url = schema_registry_url.rstrip("/")
        self.topic = topic
        self.schema_class = schema_class
        self.client_id = client_id or f"avro-producer-{topic}"

        self._producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            client_id=self.client_id,
            compression_type=compression_type,
            max_batch_size=max_batch_size,
            linger_ms=linger_ms,
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            value_serializer=self._serialize_avro,
        )
        self._started = False
        self._schema_id: int | None = None
        self._http_client = httpx.AsyncClient()

    async def _register_schema(self) -> int:
        """Register schema with Schema Registry and return schema ID."""
        if self._schema_id is not None:
            return self._schema_id

        # Get Avro schema
        schema_dict = self.schema_class.avro_schema_to_python()
        import json

        schema_str = json.dumps(schema_dict)

        # Subject name for value schema (Confluent convention)
        subject = f"{self.topic}-value"

        # Register schema
        url = f"{self.schema_registry_url}/subjects/{subject}/versions"
        payload = {"schema": schema_str}

        try:
            response = await self._http_client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/vnd.schemaregistry.v1+json"},
            )
            response.raise_for_status()
            result = response.json()
            self._schema_id = result["id"]
            logger.info(
                f"Schema registered for topic '{self.topic}' with ID {self._schema_id}"
            )
            return self._schema_id
        except httpx.HTTPError as e:
            logger.error(f"Failed to register schema: {e}")
            raise

    def _serialize_avro(self, message: T) -> bytes:
        """Serialize message to Avro binary format with Schema Registry wire format."""
        try:
            if self._schema_id is None:
                raise RuntimeError(
                    "Schema not registered. Call start() before sending messages."
                )

            # Serialize message to Avro binary
            avro_bytes = message.serialize()

            # Create Schema Registry wire format:
            # [MAGIC_BYTE (1 byte)][SCHEMA_ID (4 bytes)][AVRO_PAYLOAD]
            output = io.BytesIO()
            output.write(struct.pack("b", MAGIC_BYTE))  # Magic byte
            output.write(struct.pack(">I", self._schema_id))  # Schema ID (big-endian)
            output.write(avro_bytes)  # Avro-encoded message

            return output.getvalue()
        except Exception as e:
            logger.error(f"Failed to serialize message: {e}")
            raise

    async def start(self) -> None:
        """Start the producer and register schema."""
        if not self._started:
            # Register schema with Schema Registry
            await self._register_schema()

            # Start producer
            await self._producer.start()
            self._started = True
            logger.info(f"Kafka producer started for topic '{self.topic}'")

    async def stop(self) -> None:
        """Stop the producer and flush pending messages."""
        if self._started:
            await self._producer.stop()
            await self._http_client.aclose()
            self._started = False
            logger.info(f"Kafka producer stopped for topic '{self.topic}'")

    async def send(
        self,
        message: T,
        key: str | None = None,
        partition: int | None = None,
        headers: dict[str, bytes] | None = None,
    ) -> None:
        """
        Send a message to Kafka.

        Args:
            message: Avro message to send
            key: Message key for partitioning
            partition: Specific partition to send to (overrides key-based partitioning)
            headers: Optional message headers

        Raises:
            KafkaError: If message cannot be sent
        """
        if not self._started:
            raise RuntimeError("Producer not started. Call start() first.")

        try:
            # Convert headers dict to list of tuples if provided
            header_list = None
            if headers:
                header_list = [(k, v) for k, v in headers.items()]

            future = await self._producer.send(
                topic=self.topic,
                value=message,
                key=key,
                partition=partition,
                headers=header_list,
            )

            # Wait for acknowledgment
            record_metadata = await future
            logger.debug(
                f"Message sent to {record_metadata.topic}[{record_metadata.partition}] "
                f"at offset {record_metadata.offset}"
            )

        except KafkaError as e:
            logger.error(f"Failed to send message: {e}")
            raise

    async def send_batch(
        self,
        messages: list[tuple[T, str | None]],
        headers: dict[str, bytes] | None = None,
    ) -> None:
        """
        Send multiple messages efficiently.

        Args:
            messages: List of (message, key) tuples
            headers: Optional headers to apply to all messages
        """
        tasks = [
            self.send(message, key=key, headers=headers) for message, key in messages
        ]
        await asyncio.gather(*tasks)

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()
