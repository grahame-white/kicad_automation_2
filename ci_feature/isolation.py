"""Feature isolation validation for ci_feature.

Ensures all file paths referenced in a feature manifest are:
1. Relative (not absolute)
2. Contained within the feature's own directory subtree
"""

import os
from typing import Any, Dict, Generator, Tuple


class IsolationViolationError(Exception):
    """Raised when a feature manifest references paths outside its directory subtree."""


def _iter_manifest_paths(
    manifest_data: Dict[str, Any],
) -> Generator[Tuple[str, str], None, None]:
    """Yield (field_name, path) pairs for all file paths referenced in a manifest."""
    if "schematic" in manifest_data:
        yield "schematic", manifest_data["schematic"]
    if "interface" in manifest_data:
        yield "interface", manifest_data["interface"]
    if "models" in manifest_data and isinstance(manifest_data["models"], dict):
        libraries = manifest_data["models"].get("libraries", [])
        if isinstance(libraries, list):
            for i, lib in enumerate(libraries):
                if isinstance(lib, str):
                    yield f"models.libraries[{i}]", lib


def validate_isolation(feature_dir: str, manifest_data: Dict[str, Any]) -> None:
    """Validate that all paths in the manifest are relative and within the feature directory.

    Feature isolation rules:

    1. All paths in ``feature.yml`` must be relative (not absolute).
    2. All paths must resolve to locations within the feature's directory subtree.

    Args:
        feature_dir: Path to the directory containing the ``feature.yml`` file.
        manifest_data: Parsed manifest data dict.

    Raises:
        IsolationViolationError: If any path is absolute or resolves outside the feature
            directory.  The error message names the offending field and path, explains
            which isolation rule was violated, and suggests how to fix it.
    """
    feature_dir_real = os.path.realpath(feature_dir)

    for field, path in _iter_manifest_paths(manifest_data):
        if os.path.isabs(path):
            raise IsolationViolationError(
                f"'{field}' contains absolute path '{path}'. "
                f"All paths in feature.yml must be relative to the feature directory. "
                f"Use a relative path instead of an absolute path."
            )

        resolved = os.path.normpath(os.path.join(feature_dir_real, path))
        rel = os.path.relpath(resolved, feature_dir_real)
        if rel.startswith(".."):
            raise IsolationViolationError(
                f"'{field}' path '{path}' resolves outside the feature directory "
                f"'{feature_dir_real}'. All paths in feature.yml must be contained "
                f"within the feature's directory subtree. Remove any '../' components "
                f"that escape the feature directory."
            )
