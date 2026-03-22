import functools
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import jsonschema
import yaml

SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "ci",
    "schemas",
    "feature.schema.json",
)


@functools.lru_cache(maxsize=1)
def _load_schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


class ManifestValidationError(Exception):
    """Raised when a feature manifest fails schema validation or cannot be parsed."""


@dataclass
class FeatureManifest:
    """Represents a parsed and validated feature.yml manifest."""

    name: str
    version: str
    schematic: str
    interface: str
    models: Dict[str, Any]
    configuration: Optional[Dict[str, Any]] = None


def load_manifest(path: str) -> FeatureManifest:
    """Load and validate a feature.yml manifest file.

    Args:
        path: Path to the feature.yml file.

    Returns:
        A :class:`FeatureManifest` instance populated from the file.

    Raises:
        FileNotFoundError: If *path* does not exist.  The message includes the path.
        ManifestValidationError: If the file contains malformed YAML or if the
            parsed data does not satisfy the JSON Schema.  The message includes
            the name of the failing field or a YAML parse description.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Manifest file not found: {path}")

    with open(path) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise ManifestValidationError(
                f"Failed to parse YAML in {path}: {exc}"
            ) from exc

    schema = _load_schema()

    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        raise ManifestValidationError(
            f"Manifest validation failed: {exc.message}"
        ) from exc

    return FeatureManifest(
        name=data["name"],
        version=data["version"],
        schematic=data["schematic"],
        interface=data["interface"],
        models=data["models"],
        configuration=data.get("configuration"),
    )
