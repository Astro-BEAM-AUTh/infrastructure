# Schema Registry Integration Guide

This document explains how the Kafka infrastructure integrates with Confluent Schema Registry for Avro serialization/deserialization.

## Overview

The Kafka producers and consumers in this project use **Confluent Schema Registry** to:
1. Register Avro schemas automatically
2. Validate schema compatibility
3. Serialize messages with schema IDs
4. Deserialize messages using the correct schema version

## How It Works

### Producer Flow

1. **Schema Registration** (on startup):
   - Producer connects to Schema Registry
   - Extracts Avro schema from the dataclass (e.g., `TelescopeCommand`)
   - Registers schema under subject `{topic}-value` (e.g., `telescope.commands-value`)
   - Receives schema ID from Schema Registry
   - Caches schema ID for subsequent messages

2. **Message Serialization**:
   - Serialize message using `dataclasses-avroschema` to Avro binary
   - Prepend Confluent wire format header:
     ```
     [MAGIC_BYTE (1 byte)] [SCHEMA_ID (4 bytes, big-endian)] [AVRO_PAYLOAD]
     ```
   - Send to Kafka broker

### Consumer Flow

1. **Message Deserialization**:
   - Receive message from Kafka
   - Parse Confluent wire format header
   - Extract schema ID from header
   - Fetch schema from Schema Registry (with caching)
   - Deserialize Avro payload using the message class

## Wire Format

Messages use the Confluent Schema Registry wire format:

```
┌──────────────┬─────────────────┬──────────────────────┐
│  Magic Byte  │    Schema ID    │    Avro Payload      │
│   (1 byte)   │  (4 bytes BE)   │   (variable length)  │
│     0x00     │   0x00000001    │   {serialized data}  │
└──────────────┴─────────────────┴──────────────────────┘
```

- **Magic Byte**: Always `0x00` (indicates Confluent format)
- **Schema ID**: Big-endian 32-bit integer (schema version from registry)
- **Avro Payload**: Binary Avro-encoded message

## Usage Examples

### Producer with Schema Registry

```python
from schemas.commands import TelescopeCommand
from utils import KafkaAvroProducer

async with KafkaAvroProducer[TelescopeCommand](
    bootstrap_servers='localhost:9092',
    schema_registry_url='http://localhost:8081',  # Required!
    topic='telescope.commands',
    schema_class=TelescopeCommand,  # Required!
) as producer:
    command = TelescopeCommand(
        command_id="cmd-001",
        command_type="start_observation",
        timestamp=int(datetime.now().timestamp() * 1000),
        # ... other fields
    )
    await producer.send(command, key="cmd-001")
```

**Key changes from basic producer:**
- Added `schema_registry_url` parameter
- Added `schema_class` parameter (the dataclass type)

### Consumer with Schema Registry

```python
from schemas.commands import TelescopeCommand
from utils import KafkaAvroConsumer

async def handle_command(command: TelescopeCommand):
    print(f"Received: {command.command_id}")

async with KafkaAvroConsumer[TelescopeCommand](
    bootstrap_servers='localhost:9092',
    schema_registry_url='http://localhost:8081',  # Required!
    topic='telescope.commands',
    group_id='my-consumer-group',
    message_class=TelescopeCommand,
) as consumer:
    await consumer.consume(handle_command)
```

**Key changes from basic consumer:**
- Added `schema_registry_url` parameter

## Schema Evolution

Schema Registry enforces compatibility rules. By default, it uses **BACKWARD** compatibility.

### Compatible Changes (Safe)
- Adding optional fields with defaults
- Removing fields
- Changing field documentation

### Incompatible Changes (Breaking)
- Removing required fields
- Changing field types
- Renaming fields (without aliases)
- Adding required fields without defaults

### Example: Adding Optional Field

**Before:**
```python
@dataclass
class TelescopeCommand(AvroModel):
    command_id: str
    command_type: str
    timestamp: int
```

**After (Compatible):**
```python
@dataclass
class TelescopeCommand(AvroModel):
    command_id: str
    command_type: str
    timestamp: int
    priority: int = field(default=0)  # New optional field
```

This is safe! Old consumers can still read new messages (they ignore the `priority` field).

## Checking Registered Schemas

### List All Subjects
```bash
curl http://localhost:8081/subjects
```

Output:
```json
[
  "telescope.commands-value",
  "telescope.acknowledgments-value",
  "telescope.data-value",
  "telescope.status-value"
]
```

### Get Latest Schema Version
```bash
curl http://localhost:8081/subjects/telescope.commands-value/versions/latest
```

Output:
```json
{
  "subject": "telescope.commands-value",
  "version": 1,
  "id": 1,
  "schema": "{\"type\":\"record\",\"name\":\"TelescopeCommand\",...}"
}
```

### Get All Versions
```bash
curl http://localhost:8081/subjects/telescope.commands-value/versions
```

### Get Schema by ID
```bash
curl http://localhost:8081/schemas/ids/1
```

## Compatibility Modes

Change compatibility mode per subject:

```bash
# Set to FORWARD (new schema can read old data)
curl -X PUT http://localhost:8081/config/telescope.commands-value \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"compatibility": "FORWARD"}'

# Set to FULL (both backward and forward compatible)
curl -X PUT http://localhost:8081/config/telescope.commands-value \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"compatibility": "FULL"}'

# Set to NONE (no compatibility checks)
curl -X PUT http://localhost:8081/config/telescope.commands-value \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"compatibility": "NONE"}'
```

Available modes:
- `BACKWARD` (default): New schema can read old data
- `FORWARD`: Old schema can read new data
- `FULL`: Both backward and forward compatible
- `NONE`: No compatibility checks

## Testing Schema Compatibility

Before deploying a schema change, test it:

```bash
# Test if new schema is compatible
curl -X POST http://localhost:8081/compatibility/subjects/telescope.commands-value/versions/latest \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"TelescopeCommand\",..."}'
```

Response:
```json
{"is_compatible": true}
```

## Troubleshooting

### Schema Registration Fails

**Error**: `Schema already registered with different schema`

**Solution**: The schema has changed in a way that creates a new schema rather than a new version. Either:
1. Make the change backward compatible
2. Delete the subject and re-register (WARNING: breaks consumers)
3. Change compatibility mode to `NONE` temporarily

```bash
# Delete subject (careful!)
curl -X DELETE http://localhost:8081/subjects/telescope.commands-value
```

### Consumer Can't Deserialize

**Error**: `Invalid magic byte` or `Failed to deserialize message`

**Possible causes**:
1. Producer not using Schema Registry (old serialization method)
2. Message corrupted
3. Using wrong deserializer

**Solution**: Ensure both producer and consumer use Schema Registry URLs.

### Schema ID Not Found

**Error**: `Schema ID {X} not found in registry`

**Cause**: Consumer is trying to read a message with a schema that doesn't exist in the registry.

**Solution**:
1. Check Schema Registry is accessible
2. Ensure producer registered schema successfully
3. Verify schema wasn't deleted

## Performance Considerations

### Schema Caching

Both producer and consumer cache schemas to avoid repeated Registry calls:

- **Producer**: Caches schema ID after first registration
- **Consumer**: Caches schema definitions by ID

### Connection Pooling

The HTTP client (`httpx.AsyncClient`) uses connection pooling for efficiency.

### Best Practices

1. **Register schemas on startup**: Schema registration happens once per producer instance
2. **Reuse producer/consumer instances**: Don't create new instances per message
3. **Monitor Registry health**: Schema Registry is a critical dependency

## Integration with Backend

To use in your FastAPI backend:

```python
# backend/src/backend/kafka_utils.py

from schemas.commands import TelescopeCommand
from utils import KafkaAvroProducer

class KafkaService:
    def __init__(self):
        self.command_producer: KafkaAvroProducer[TelescopeCommand] | None = None
    
    async def start(self):
        self.command_producer = KafkaAvroProducer[TelescopeCommand](
            bootstrap_servers='localhost:9092',
            schema_registry_url='http://localhost:8081',
            topic='telescope.commands',
            schema_class=TelescopeCommand,
        )
        await self.command_producer.start()
    
    async def stop(self):
        if self.command_producer:
            await self.command_producer.stop()
    
    async def send_command(self, command: TelescopeCommand):
        await self.command_producer.send(command, key=command.command_id)

# In your FastAPI app
kafka_service = KafkaService()

@app.on_event("startup")
async def startup():
    await kafka_service.start()

@app.on_event("shutdown")
async def shutdown():
    await kafka_service.stop()
```

## References

- [Confluent Schema Registry Documentation](https://docs.confluent.io/platform/current/schema-registry/index.html)
- [Avro Specification](https://avro.apache.org/docs/current/spec.html)
- [dataclasses-avroschema Documentation](https://marcosschroh.github.io/dataclasses-avroschema/)
