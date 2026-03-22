"""Interface contract loader and validator for ci_feature.

Loads and validates ``interface.yml`` files against the JSON Schema at
``ci/schemas/interface.schema.json``.
"""

import functools
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List

import jsonschema
import yaml

__all__ = [
    "InterfaceContract",
    "InterfaceValidationError",
    "load_interface",
]

SCHEMA_PATH = os.path.realpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "ci",
        "schemas",
        "interface.schema.json",
    )
)


@functools.lru_cache(maxsize=1)
def _load_schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


class InterfaceValidationError(Exception):
    """Raised when an interface.yml fails schema validation or cannot be parsed."""


@dataclass
class InterfaceContract:
    """Represents a parsed and validated interface.yml contract."""

    name: str
    version: str
    signals: List[Dict[str, Any]]


def load_interface(path: str) -> InterfaceContract:
    """Load and validate an ``interface.yml`` file.

    Args:
        path: Path to the ``interface.yml`` file.

    Returns:
        An :class:`InterfaceContract` instance populated from the file.

    Raises:
        FileNotFoundError: If *path* does not exist.  The message includes the path.
        InterfaceValidationError: If the file contains malformed YAML or if the
            parsed data does not satisfy the JSON Schema.  The message includes
            the name of the failing field or a YAML parse description.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Interface file not found: {path}")

    with open(path) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise InterfaceValidationError(f"Failed to parse YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise InterfaceValidationError(
            f"Interface root must be a mapping/object, got {type(data).__name__}"
        )

    schema = _load_schema()

    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        field_path = None
        json_path = getattr(exc, "json_path", None)
        if json_path:
            field_path = json_path.lstrip("$.")
        elif exc.path:
            field_path = ".".join(str(p) for p in exc.path)

        if field_path:
            message = f"Interface validation failed at '{field_path}': {exc.message}"
        else:
            message = f"Interface validation failed: {exc.message}"

        raise InterfaceValidationError(message) from exc

    return InterfaceContract(
        name=data["name"],
        version=data["version"],
        signals=data["signals"],
    )
