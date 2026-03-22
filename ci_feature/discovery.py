"""Feature discovery via recursive filesystem scan."""

import os
from typing import List

from ci_feature.manifest import FeatureManifest, load_manifest

_FEATURE_MANIFEST_FILENAME = "feature.yml"

# Directories that are never source directories and should be skipped during
# discovery to avoid unnecessary I/O (e.g. .git/objects can be very large).
_PRUNE_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "node_modules",
        "venv",
    }
)


def discover_features(root_path: str) -> List[FeatureManifest]:
    """Discover all features in a repository by locating ``feature.yml`` files.

    Recursively scans *root_path* for files named ``feature.yml``, loads and
    validates each one via :func:`~ci_feature.manifest.load_manifest`, and
    returns the resulting :class:`~ci_feature.manifest.FeatureManifest` objects
    in deterministic order (sorted alphabetically by each manifest's file path).

    Common non-source directories (e.g. ``.git``, ``__pycache__``, ``.venv``)
    are pruned from the walk to avoid unnecessary I/O.

    Args:
        root_path: Path to the root of the repository to scan.

    Returns:
        A list of :class:`~ci_feature.manifest.FeatureManifest` instances,
        sorted alphabetically by each manifest's file path (as produced by
        :func:`os.walk`, which is relative if *root_path* is relative).
        Returns an empty list when no ``feature.yml`` files are found.
    """
    manifest_paths: List[str] = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = sorted(d for d in dirnames if d not in _PRUNE_DIRS)
        if _FEATURE_MANIFEST_FILENAME in filenames:
            manifest_paths.append(os.path.join(dirpath, _FEATURE_MANIFEST_FILENAME))

    manifest_paths.sort()

    return [load_manifest(path) for path in manifest_paths]
