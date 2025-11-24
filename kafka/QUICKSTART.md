# Kafka Infrastructure Quick Reference

## Quick Start (Windows)

```cmd
cd c:\Users\Herck\GitHub Repos\Astro\infrastructure\kafka

REM Setup everything
setup.bat

REM Or manual steps:
copy .env.example .env
pip install -e .
python generate_schemas.py
docker compose up -d

REM Deploy sink connector (after services are healthy)
cd connectors
deploy-connector.bat
```

## Quick Start (Linux/Mac)

```bash
cd infrastructure/kafka

# Setup everything
chmod +x setup.sh
./setup.sh

# Or manual steps:
cp .env.example .env
pip install -e .
python generate_schemas.py
docker compose up -d

# Deploy sink connector
cd connectors
chmod +x deploy-connector.sh
./deploy-connector.sh
```

## Service URLs

- **Kafka Broker**: `localhost:9092`
- **Schema Registry**: `http://localhost:8081` ⭐
- **Kafka Connect**: `http://localhost:8083`
- **Kafka UI**: `http://localhost:8080` (with `--profile tools`)

⭐ **Schema Registry is required** for all producers and consumers!

## Python Usage

### Send a Command (Producer)

```python
from datetime import datetime
from schemas.commands import TelescopeCommand, CommandType
from utils import KafkaAvroProducer

async with KafkaAvroProducer[TelescopeCommand](
    bootstrap_servers='localhost:9092',
    schema_registry_url='http://localhost:8081',  # Required!
    topic='telescope.commands',
    schema_class=TelescopeCommand,  # Required!
) as producer:
    cmd = TelescopeCommand(
        command_id="cmd-001",
        command_type=CommandType.START_OBSERVATION.value,
        timestamp=int(datetime.now().timestamp() * 1000),
        # ... other fields
    )
    await producer.send(cmd, key="cmd-001")
```

**Important**: Always provide `schema_registry_url` and `schema_class`!

### Consume Commands (Consumer)

```python
from schemas.commands import TelescopeCommand
from utils import KafkaAvroConsumer

async def handle(cmd: TelescopeCommand):
    print(f"Got command: {cmd.command_id}")

async with KafkaAvroConsumer[TelescopeCommand](
    bootstrap_servers='localhost:9092',
    schema_registry_url='http://localhost:8081',  # Required!
    topic='telescope.commands',
    group_id='my-app',
    message_class=TelescopeCommand,
) as consumer:
    await consumer.consume(handle)
```

## Common Commands

### Docker Management

```bash
# Start all services
docker compose up -d

# Start with Kafka UI
docker compose --profile tools up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f kafka
docker compose logs -f kafka-connect

# Restart a service
docker compose restart kafka
```

### Topic Management

```bash
# List topics
docker exec astro-kafka kafka-topics --bootstrap-server localhost:9092 --list

# Describe topic
docker exec astro-kafka kafka-topics --bootstrap-server localhost:9092 --describe --topic telescope.commands

# Delete topic (if needed)
docker exec astro-kafka kafka-topics --bootstrap-server localhost:9092 --delete --topic topic-name

# Consume messages from topic
docker exec astro-kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic telescope.commands --from-beginning
```

### Schema Registry Management

```bash
# List all registered schemas
curl http://localhost:8081/subjects

# Get latest version of a schema
curl http://localhost:8081/subjects/telescope.commands-value/versions/latest

# Get all versions
curl http://localhost:8081/subjects/telescope.commands-value/versions

# Get schema by ID
curl http://localhost:8081/schemas/ids/1

# Delete a subject (careful!)
curl -X DELETE http://localhost:8081/subjects/telescope.commands-value

# Check compatibility
curl -X POST http://localhost:8081/compatibility/subjects/telescope.commands-value/versions/latest \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{...}"}'
```

### Connector Management

```bash
# List connectors
curl http://localhost:8083/connectors

# Check connector status
curl http://localhost:8083/connectors/postgres-telescope-data-sink/status

# Delete connector
curl -X DELETE http://localhost:8083/connectors/postgres-telescope-data-sink

# Restart connector
curl -X POST http://localhost:8083/connectors/postgres-telescope-data-sink/restart
```

### Consumer Group Management

```bash
# List consumer groups
docker exec astro-kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list

# Describe consumer group
docker exec astro-kafka kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group telescope-robotics

# Reset consumer group offset
docker exec astro-kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group telescope-robotics --reset-offsets --to-earliest --topic telescope.commands --execute
```

## Troubleshooting

### Services not starting

```bash
# Check logs
docker compose logs

# Check specific service
docker compose logs kafka

# Restart services
docker compose restart
```

### Cannot connect from code

- Ensure you're using `localhost:9092` (not `kafka:29092` which is internal)
- Verify Schema Registry URL is correct: `http://localhost:8081`
- Check firewall settings
- Verify services are running: `docker compose ps`

### Schema Registration Fails

```bash
# Check if Schema Registry is healthy
curl http://localhost:8081/subjects

# Common issues:
# - Schema Registry not running
# - Network connectivity issues
# - Schema already exists with different definition
```

### Connector failing

```bash
# Check connector status
curl http://localhost:8083/connectors/postgres-telescope-data-sink/status

# Check logs
docker logs astro-kafka-connect

# Common issues:
# - Database not accessible from container
# - Table doesn't exist (run SQL migration)
# - Invalid credentials in .env
```

### Deserialization Errors

**Error**: `Invalid magic byte` or `Failed to deserialize message`

**Solution**: Ensure both producer and consumer use Schema Registry:
- Producer: Include `schema_registry_url` and `schema_class`
- Consumer: Include `schema_registry_url`

## Database Migration

Don't forget to create the `telescope_data_raw` table in PostgreSQL:

```bash
# Copy the migration
cp sql/create_telescope_data_table.sql ../database/migrations/v0.2.0_kafka_telescope_data.sql

# Run migration using your database migration tool
cd ../database
python migrate.py
```

## Integration with Backend

Add to `backend/pyproject.toml`:

```toml
dependencies = [
    # ... existing
    "aiokafka[snappy]>=0.12.0",
    "dataclasses-avroschema>=0.66.1",
    "httpx>=0.27.0",
]
```

Import schemas in your FastAPI app:

```python
# Add kafka folder to Python path or install as package
import sys
sys.path.append('../infrastructure/kafka')

from schemas.commands import TelescopeCommand
from utils import KafkaAvroProducer

# Create producer
producer = KafkaAvroProducer[TelescopeCommand](
    bootstrap_servers='localhost:9092',
    schema_registry_url='http://localhost:8081',
    topic='telescope.commands',
    schema_class=TelescopeCommand,
)

# Start on app startup
await producer.start()

# Use in endpoints
await producer.send(command, key=command.command_id)
```

## Schema Evolution

See [SCHEMA_REGISTRY.md](SCHEMA_REGISTRY.md) for detailed guide on:
- Schema compatibility rules
- Safe vs. breaking changes
- Testing schema updates
- Wire format details

## Key Differences from Basic Kafka

This implementation uses **Confluent Schema Registry**, which means:

✅ **Schema validation** - Invalid messages are rejected
✅ **Schema evolution** - Controlled schema changes
✅ **Type safety** - Strongly typed messages
✅ **Efficiency** - Schema sent once, referenced by ID
✅ **Documentation** - Self-documenting schemas

But requires:
⚠️ Schema Registry URL in all producers/consumers
⚠️ Schema class parameter in producers
⚠️ Schema Registry service must be running
