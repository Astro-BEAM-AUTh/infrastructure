"""Kafka Avro consumer utility."""

import io
import logging
import struct
from collections.abc import AsyncIterator
from typing import Awaitable, Callable, Generic, TypeVar

import httpx
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from aiokafka.structs import ConsumerRecord
from dataclasses_avroschema import AvroModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=AvroModel)

# Magic byte for Confluent Schema Registry wire format
MAGIC_BYTE = 0


class KafkaAvroConsumer(Generic[T]):
    """
    Async Kafka consumer for Avro-serialized messages with Schema Registry.

    This consumer handles deserialization of Avro messages from Kafka topics
    using Schema Registry and provides both polling and callback-based consumption patterns.

    Example:
        >>> from schemas.commands import TelescopeCommand
        >>>
        >>> async def handle_command(command: TelescopeCommand) -> None:
        ...     print(f"Received command: {command.command_id}")
        >>>
        >>> consumer = KafkaAvroConsumer[TelescopeCommand](
        ...     bootstrap_servers='localhost:9092',
        ...     schema_registry_url='http://localhost:8081',
        ...     topic='telescope.commands',
        ...     group_id='telescope-robotics',
        ...     message_class=TelescopeCommand
        ... )
        >>> await consumer.start()
        >>> await consumer.consume(handle_command)
    """

    def __init__(
        self,
        bootstrap_servers: str | list[str],
        schema_registry_url: str,
        topic: str | list[str],
        group_id: str,
        message_class: type[T],
        client_id: str | None = None,
        auto_offset_reset: str = "latest",
        enable_auto_commit: bool = True,
        max_poll_records: int = 100,
    ):
        """
        Initialize Kafka Avro consumer.

        Args:
            bootstrap_servers: Kafka broker addresses
            schema_registry_url: URL of Schema Registry
            topic: Topic or list of topics to consume from
            group_id: Consumer group identifier
            message_class: Dataclass type for message deserialization
            client_id: Client identifier for Kafka
            auto_offset_reset: Where to start reading ('earliest' or 'latest')
            enable_auto_commit: Whether to auto-commit offsets
            max_poll_records: Maximum number of records per poll
        """
        self.bootstrap_servers = bootstrap_servers
        self.schema_registry_url = schema_registry_url.rstrip("/")
        self.topics = [topic] if isinstance(topic, str) else topic
        self.group_id = group_id
        self.message_class = message_class
        self.client_id = client_id or f"avro-consumer-{group_id}"

        self._consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            client_id=self.client_id,
            auto_offset_reset=auto_offset_reset,
            enable_auto_commit=enable_auto_commit,
            max_poll_records=max_poll_records,
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
            value_deserializer=self._deserialize_avro,
        )
        self._started = False
        self._consuming = False
        self._http_client = httpx.AsyncClient()
        self._schema_cache: dict[int, dict] = {}  # Cache schemas by ID

    async def _get_schema_by_id(self, schema_id: int) -> dict:
        """Fetch schema from Schema Registry by ID."""
        if schema_id in self._schema_cache:
            return self._schema_cache[schema_id]

        url = f"{self.schema_registry_url}/schemas/ids/{schema_id}"

        try:
            response = await self._http_client.get(url)
            response.raise_for_status()
            result = response.json()

            import json

            schema_dict = json.loads(result["schema"])
            self._schema_cache[schema_id] = schema_dict
            return schema_dict
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch schema ID {schema_id}: {e}")
            raise

    def _deserialize_avro(self, data: bytes) -> T:
        """Deserialize Avro binary data with Schema Registry wire format."""
        try:
            if len(data) < 5:
                raise ValueError("Message too short to contain Schema Registry header")

            # Parse Schema Registry wire format:
            # [MAGIC_BYTE (1 byte)][SCHEMA_ID (4 bytes)][AVRO_PAYLOAD]
            reader = io.BytesIO(data)

            # Read and validate magic byte
            magic_byte = struct.unpack("b", reader.read(1))[0]
            if magic_byte != MAGIC_BYTE:
                raise ValueError(f"Invalid magic byte: {magic_byte}")

            # Read schema ID (big-endian)
            _ = struct.unpack(">I", reader.read(4))[0]

            # Read Avro payload
            avro_bytes = reader.read()

            # Deserialize using the message class
            # Note: Schema Registry schema validation happens at producer side
            # Here we trust the schema and deserialize directly
            return self.message_class.deserialize(avro_bytes)

        except Exception as e:
            logger.error(f"Failed to deserialize message: {e}")
            raise

    async def start(self) -> None:
        """Start the consumer."""
        if not self._started:
            await self._consumer.start()
            self._started = True
            logger.info(
                f"Kafka consumer started for topics {self.topics} "
                f"in group '{self.group_id}'"
            )

    async def stop(self) -> None:
        """Stop the consumer."""
        if self._started:
            self._consuming = False
            await self._consumer.stop()
            await self._http_client.aclose()
            self._started = False
            logger.info(f"Kafka consumer stopped for group '{self.group_id}'")

    async def consume(
        self,
        callback: Callable[[T], Awaitable[None]],
        error_handler: Callable[[Exception, ConsumerRecord], Awaitable[None]]
        | None = None,
    ) -> None:
        """
        Continuously consume messages and process them with callback.

        Args:
            callback: Async function to process each message
            error_handler: Optional async function to handle processing errors
        """
        if not self._started:
            raise RuntimeError("Consumer not started. Call start() first.")

        self._consuming = True
        logger.info("Starting message consumption...")

        try:
            async for record in self._consumer:
                if not self._consuming:
                    break

                try:
                    message: T = record.value
                    await callback(message)

                except Exception as e:
                    logger.error(
                        f"Error processing message from {record.topic}[{record.partition}] "
                        f"at offset {record.offset}: {e}"
                    )

                    if error_handler:
                        try:
                            await error_handler(e, record)
                        except Exception as handler_error:
                            logger.error(f"Error in error handler: {handler_error}")

        except KafkaError as e:
            logger.error(f"Kafka consumer error: {e}")
            raise
        finally:
            self._consuming = False

    async def poll(self, timeout_ms: int = 1000) -> list[T]:
        """
        Poll for messages and return them as a list.

        Args:
            timeout_ms: Maximum time to wait for messages

        Returns:
            List of deserialized messages
        """
        if not self._started:
            raise RuntimeError("Consumer not started. Call start() first.")

        messages: list[T] = []

        try:
            data = await self._consumer.getmany(timeout_ms=timeout_ms)

            for topic_partition, records in data.items():
                for record in records:
                    messages.append(record.value)

        except KafkaError as e:
            logger.error(f"Error polling messages: {e}")
            raise

        return messages

    async def stream(self) -> AsyncIterator[T]:
        """
        Stream messages as an async iterator.

        Yields:
            Deserialized messages one at a time

        Example:
            >>> async for message in consumer.stream():
            ...     print(f"Received: {message}")
        """
        if not self._started:
            raise RuntimeError("Consumer not started. Call start() first.")

        try:
            async for record in self._consumer:
                yield record.value
        except KafkaError as e:
            logger.error(f"Error streaming messages: {e}")
            raise

    async def commit(self) -> None:
        """Manually commit current offsets (when auto-commit is disabled)."""
        if not self._started:
            raise RuntimeError("Consumer not started. Call start() first.")

        await self._consumer.commit()
        logger.debug("Offsets committed")

    async def seek_to_beginning(self) -> None:
        """Seek to the beginning of all assigned partitions."""
        if not self._started:
            raise RuntimeError("Consumer not started. Call start() first.")

        self._consumer.seek_to_beginning()
        logger.info("Seeked to beginning of all partitions")

    async def seek_to_end(self) -> None:
        """Seek to the end of all assigned partitions."""
        if not self._started:
            raise RuntimeError("Consumer not started. Call start() first.")

        self._consumer.seek_to_end()
        logger.info("Seeked to end of all partitions")

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()
