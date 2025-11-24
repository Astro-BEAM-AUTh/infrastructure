# Astro BEAM Kafka Infrastructure

This directory contains the Kafka infrastructure configuration for the Astro BEAM telescope control system, including message schemas, Docker Compose setup, and Python utilities for message production and consumption.

## Architecture Overview

The Kafka infrastructure supports communication between the control center (backend) and telescope applications (telescope-robotics and telescope-data-handler).

### Topics

| Topic | Purpose | Retention | Partitions |
|-------|---------|-----------|------------|
| `telescope.commands` | Commands from control center to telescope apps | 7 days | 1 |
| `telescope.acknowledgments` | Acknowledgments from telescope apps to control center | 7 days | 1 |
| `telescope.data` | Observation data from telescope-data-handler to PostgreSQL | 30 days | 1 |
| `telescope.status` | Status updates from telescope systems | 3 days | 1 |

### Message Flow

```
Control Center (Backend)
    ↓ (produces)
telescope.commands ──→ Telescope Apps (telescope-robotics, telescope-data-handler)
    ↓ (consumes & processes)
telescope.acknowledgments ←── Telescope Apps (produces acknowledgments)
    ↑ (consumes)
Control Center (monitors acknowledgments)

Telescope Data Handler
    ↓ (produces)
telescope.data ──→ Kafka Connect ──→ PostgreSQL
```

## Directory Structure

```
kafka/
├── docker-compose.yml          # Kafka infrastructure services
├── .env.example               # Environment variables template
├── pyproject.toml             # Python dependencies
├── generate_schemas.py        # Script to generate Avro schemas
├── README.md                  # This file
│
├── schemas/                   # Message schema definitions
│   ├── __init__.py
│   ├── commands.py           # TelescopeCommand schema
│   ├── acknowledgments.py    # CommandAcknowledgment schema
│   ├── data.py               # TelescopeData schema
│   └── status.py             # TelescopeStatus schema
│
├── avro-schemas/             # Generated .avsc files (created by generate_schemas.py)
│   ├── telescope-command.avsc
│   ├── command-acknowledgment.avsc
│   ├── telescope-data.avsc
│   └── telescope-status.avsc
│
├── connectors/               # Kafka Connect configurations
│   ├── postgres-sink.json   # PostgreSQL sink connector config
│   ├── deploy-connector.sh  # Deployment script (Linux/Mac)
│   └── deploy-connector.bat # Deployment script (Windows)
│
└── utils/                    # Python utilities
    ├── __init__.py
    ├── producer.py          # KafkaAvroProducer utility
    └── consumer.py          # KafkaAvroConsumer utility
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.13+
- Access to PostgreSQL database (from `database/` folder)

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your database credentials
# Make sure these match your database/.env settings
```

### 2. Install Python Dependencies

```bash
# From the kafka/ directory
uv sync
```

### 3. Generate Avro Schemas

```bash
uv run generate_schemas.py
```

This creates `.avsc` schema files in the `avro-schemas/` directory.

### 4. Start Kafka Infrastructure

```bash
# Start all Kafka services
docker compose up -d

# Or with Kafka UI for management
docker compose --profile tools up -d
```

Services will be available at:
- **Kafka Broker**: `localhost:9092`
- **Schema Registry**: `http://localhost:8081`
- **Kafka Connect**: `http://localhost:8083`
- **Kafka UI** (optional): `http://localhost:8080`

**Note**: All producers and consumers use **Confluent Schema Registry** for Avro schema management. Schemas are automatically registered on first use. See [SCHEMA_REGISTRY.md](SCHEMA_REGISTRY.md) for detailed documentation.

### 5. Deploy PostgreSQL Sink Connector

Once Kafka Connect is healthy:

```bash
# Windows
cd connectors
deploy-connector.bat

# Linux/Mac
cd connectors
chmod +x deploy-connector.sh
./deploy-connector.sh
```

Or manually:
```bash
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @connectors/postgres-sink.json
```

### 6. Create Database Table for Telescope Data

The sink connector expects a table in PostgreSQL. Add this to your database migrations:

```sql
CREATE TABLE IF NOT EXISTS telescope_data_raw (
    data_id VARCHAR(255) PRIMARY KEY,
    observation_id VARCHAR(255) NOT NULL,
    sequence_number INTEGER NOT NULL,
    timestamp BIGINT NOT NULL,
    data BYTEA,
    processed BOOLEAN DEFAULT FALSE,
    processing_pipeline_version VARCHAR(50),
    sink_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_observation_id ON telescope_data_raw(observation_id);
CREATE INDEX idx_timestamp ON telescope_data_raw(timestamp);
```

or check `./sql/` for migration scripts.

## Troubleshooting

### Connector fails to start
```bash
# Check connector logs
curl http://localhost:8083/connectors/postgres-telescope-data-sink/status

# View detailed logs
docker logs astro-kafka-connect
```

### Cannot connect to Kafka from host
Ensure you're using `localhost:9092` for connections from the host machine and `broker:29092` for connections from within Docker containers.

### Schema Registry errors
```bash
# List all subjects (schemas)
curl http://localhost:8081/subjects

# Get specific schema
curl http://localhost:8081/subjects/telescope.data-value/versions/latest
```

