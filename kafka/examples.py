"""Example usage of Kafka producers and consumers for Astro BEAM."""

import asyncio
from datetime import datetime

from models.observation import ObservationBase
from schemas.acknowledgments import AckStatus, CommandAcknowledgment
from schemas.commands import CommandType, TelescopeCommand
from schemas.data import TelescopeData
from schemas.status import StatusLevel, TelescopeStatus
from utils import KafkaAvroConsumer, KafkaAvroProducer


async def example_send_command():
    """Example: Send a telescope command."""
    print("=== Sending Telescope Command ===")

    async with KafkaAvroProducer[TelescopeCommand](
        bootstrap_servers="localhost:9092",
        schema_registry_url="http://localhost:8081",
        topic="telescope.commands",
        schema_class=TelescopeCommand,
    ) as producer:
        observation_request = ObservationBase(
            target_name="M31",
            observation_object="Andromeda Galaxy",
            ra=10.68470833,
            dec=41.26875,
            center_frequency=1420.0,
            rf_gain=30.0,
            if_gain=20.0,
            bb_gain=15.0,
            observation_type="imaging",
            integration_time=600.0,
            output_filename="m31_observation.fits",
            observation_id="obs-20251124-001",
            user_id=1,  # Assuming user with ID 1 exists
            user=None,
            status="pending",
            submitted_at=datetime.now(),
            completed_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        command = TelescopeCommand(
            command_id="cmd-001",
            command_type=CommandType.START_OBSERVATION.value,
            timestamp=int(datetime.now().timestamp() * 1000),
            observation_request=observation_request,
        )

        await producer.send(command, key=command.command_id)
        print(f"✓ Command {command.command_id} sent successfully!")


async def example_send_acknowledgment():
    """Example: Send a command acknowledgment."""
    print("\n=== Sending Command Acknowledgment ===")

    async with KafkaAvroProducer[CommandAcknowledgment](
        bootstrap_servers="localhost:9092",
        schema_registry_url="http://localhost:8081",
        topic="telescope.acknowledgments",
        schema_class=CommandAcknowledgment,
    ) as producer:
        ack = CommandAcknowledgment(
            ack_id="ack-001",
            command_id="cmd-001",
            timestamp=int(datetime.now().timestamp() * 1000),
            status=AckStatus.STARTED.value,
            message="Observation started successfully",
            source_application="telescope-robotics",
            source_hostname="telescope-server-01",
            progress_percent=0.0,
        )

        await producer.send(ack, key=ack.command_id)
        print(f"✓ Acknowledgment {ack.ack_id} sent successfully!")


async def example_send_telescope_data():
    """Example: Send telescope observation data."""
    print("\n=== Sending Telescope Data ===")

    async with KafkaAvroProducer[TelescopeData](
        bootstrap_servers="localhost:9092",
        schema_registry_url="http://localhost:8081",
        topic="telescope.data",
        schema_class=TelescopeData,
    ) as producer:
        data = TelescopeData(
            data_id="data-001",
            observation_id="obs-20251124-001",
            sequence_number=1,
            timestamp=int(datetime.now().timestamp() * 1000),
            data_payload=b"binarydatahere",
        )

        await producer.send(data, key=data.data_id)
        print(f"✓ Data {data.data_id} sent successfully!")


async def example_send_status():
    """Example: Send telescope status update."""
    print("\n=== Sending Status Update ===")

    async with KafkaAvroProducer[TelescopeStatus](
        bootstrap_servers="localhost:9092",
        schema_registry_url="http://localhost:8081",
        topic="telescope.status",
        schema_class=TelescopeStatus,
    ) as producer:
        status = TelescopeStatus(
            status_id="status-001",
            timestamp=int(datetime.now().timestamp() * 1000),
            source_application="telescope-robotics",
            source_hostname="telescope-server-01",
            level=StatusLevel.INFO.value,
            component="mount",
            message="Telescope positioned successfully",
            is_operational=True,
            current_observation_id="obs-20251124-001",
            cpu_usage_percent=45.2,
            memory_usage_percent=62.8,
        )

        await producer.send(status, key=status.source_application)
        print(f"✓ Status {status.status_id} sent successfully!")


async def example_consume_commands():
    """Example: Consume telescope commands."""
    print("\n=== Consuming Telescope Commands ===")
    print("Listening for commands (press Ctrl+C to stop)...\n")

    async def handle_command(command: TelescopeCommand):
        print("📡 Received command:")
        print(f"   ID: {command.command_id}")
        print(f"   Type: {command.command_type}")
        print()

    async with KafkaAvroConsumer[TelescopeCommand](
        bootstrap_servers="localhost:9092",
        schema_registry_url="http://localhost:8081",
        topic="telescope.commands",
        group_id="example-consumer",
        message_class=TelescopeCommand,
        auto_offset_reset="earliest",
    ) as consumer:
        try:
            await consumer.consume(handle_command)
        except KeyboardInterrupt:
            print("\n✓ Consumer stopped")


async def example_consume_acknowledgments():
    """Example: Consume command acknowledgments."""
    print("\n=== Consuming Acknowledgments ===")
    print("Listening for acknowledgments (press Ctrl+C to stop)...\n")

    async with KafkaAvroConsumer[CommandAcknowledgment](
        bootstrap_servers="localhost:9092",
        schema_registry_url="http://localhost:8081",
        topic="telescope.acknowledgments",
        group_id="example-ack-consumer",
        message_class=CommandAcknowledgment,
        auto_offset_reset="earliest",
    ) as consumer:
        try:
            async for ack in consumer.stream():
                status_emoji = (
                    "✓" if ack.status in ["received", "started", "completed"] else "✗"
                )
                print(f"{status_emoji} Ack for {ack.command_id}:")
                print(f"   Status: {ack.status}")
                print(f"   From: {ack.source_application}")
                print(f"   Message: {ack.message}")
                if ack.progress_percent is not None:
                    print(f"   Progress: {ack.progress_percent:.1f}%")
                print()
        except KeyboardInterrupt:
            print("\n✓ Consumer stopped")


async def example_batch_send():
    """Example: Send multiple messages in batch."""
    print("\n=== Batch Sending Commands ===")

    async with KafkaAvroProducer[TelescopeCommand](
        bootstrap_servers="localhost:9092",
        schema_registry_url="http://localhost:8081",
        topic="telescope.commands",
        schema_class=TelescopeCommand,
    ) as producer:
        observation_request = ObservationBase(
            target_name="",
            observation_object="",
            ra=0.0,
            dec=0.0,
            center_frequency=0.0,
            rf_gain=0.0,
            if_gain=0.0,
            bb_gain=0.0,
            observation_type="",
            integration_time=0.0,
            output_filename="",
            observation_id="",
            user_id=0,
            user=None,
            status="",
            submitted_at=datetime.now(),
            completed_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        observation_request.target_name = "M42"
        observation_request.observation_object = "Orion Nebula"
        observation_request.ra = 83.82208333
        observation_request.dec = -5.39111111
        observation_request.center_frequency = 1420.0
        observation_request.rf_gain = 28.0
        observation_request.if_gain = 18.0
        observation_request.bb_gain = 12.0
        observation_request.observation_type = "spectroscopy"
        observation_request.integration_time = 900.0
        observation_request.output_filename = "m42_observation.fits"
        observation_request.observation_id = "obs-20251124-002"
        observation_request.user_id = 2  # Assuming user with ID 2 exists
        observation_request.submitted_at = datetime.now()
        observation_request.created_at = datetime.now()
        observation_request.updated_at = datetime.now()

        commands = [
            (
                TelescopeCommand(
                    command_id=f"cmd-{i:03d}",
                    command_type=CommandType.START_OBSERVATION.value,
                    timestamp=int(datetime.now().timestamp() * 1000),
                    observation_request=observation_request,
                ),
                f"cmd-{i:03d}",
            )
            for i in range(1, 6)
        ]

        await producer.send_batch(commands)
        print(f"✓ Sent {len(commands)} commands in batch!")


async def main():
    """Run all examples."""
    # Uncomment the examples you want to run

    # Producer examples
    await example_send_command()
    await example_send_acknowledgment()
    await example_send_telescope_data()
    await example_send_status()
    await example_batch_send()

    # Consumer examples (these will run indefinitely)
    # await example_consume_commands()
    # await example_consume_acknowledgments()


if __name__ == "__main__":
    asyncio.run(main())
