"""Generate Avro schema files (.avsc) from Python dataclasses."""

import json
from pathlib import Path

from dataclasses_avroschema import AvroModel

from schemas.acknowledgments import CommandAcknowledgment
from schemas.commands import TelescopeCommand
from schemas.data import TelescopeData
from schemas.status import TelescopeStatus


def generate_schemas(output_dir: Path) -> None:
    """
    Generate .avsc files from dataclass schemas.

    Args:
        output_dir: Directory where schema files will be written
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    schemas: dict[str, AvroModel] = {
        "telescope-command.avsc": TelescopeCommand,
        "command-acknowledgment.avsc": CommandAcknowledgment,
        "telescope-data.avsc": TelescopeData,
        "telescope-status.avsc": TelescopeStatus,
    }

    for filename, schema_class in schemas.items():
        schema_dict = schema_class.avro_schema_to_python()
        output_path = output_dir / filename

        with open(output_path, "w") as f:
            json.dump(schema_dict, f, indent=2)

        print(f"✓ Generated {filename}")


if __name__ == "__main__":
    # Generate schemas to the avro-schemas directory
    script_dir = Path(__file__).parent
    output_directory = script_dir / "avro-schemas"

    print("Generating Avro schema files...")
    generate_schemas(output_directory)
    print(f"\nAll schemas generated in {output_directory}")
