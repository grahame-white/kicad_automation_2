import functools
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import jsonschema
import yaml

SCHEMA_PATH = os.path.realpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "ci",
        "schemas",
        "feature.schema.json",
    )
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
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Manifest file not found: {path}")

    with open(path) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise ManifestValidationError(f"Failed to parse YAML in {path}: {exc}") from exc

    schema = _load_schema()

    # Ensure the manifest has a mapping/object at the root.  This provides a
    # clearer error than opaque schema messages when the YAML is empty or is
    # not a mapping (e.g. a bare scalar or list).
    if not isinstance(data, dict):
        raise ManifestValidationError(
            f"Manifest root must be a mapping/object, got {type(data).__name__}"
        )

    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        # Enhance the error message with the failing field path when available.
        # json_path is available on ValidationError in jsonschema >= 4.18.0,
        # which matches the pinned version in requirements.txt.
        field_path = None
        json_path = getattr(exc, "json_path", None)
        if json_path:
            # Trim leading "$." for brevity ("$.models.libraries" → "models.libraries").
            field_path = json_path.lstrip("$.")
        elif exc.path:
            field_path = ".".join(str(p) for p in exc.path)

        if field_path:
            message = f"Manifest validation failed at '{field_path}': {exc.message}"
        else:
            message = f"Manifest validation failed: {exc.message}"

        raise ManifestValidationError(message) from exc

    return FeatureManifest(
        name=data["name"],
        version=data["version"],
        schematic=data["schematic"],
        interface=data["interface"],
        models=data["models"],
        configuration=data.get("configuration"),
    )
