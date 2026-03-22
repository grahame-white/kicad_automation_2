"""Feature discovery via recursive filesystem scan."""

import os
from typing import List

from ci_feature.manifest import FeatureManifest, load_manifest

_FEATURE_MANIFEST_FILENAME = "feature.yml"


def discover_features(root_path: str) -> List[FeatureManifest]:
    """Discover all features in a repository by locating ``feature.yml`` files.

    Recursively scans *root_path* for files named ``feature.yml``, loads and
    validates each one via :func:`~ci_feature.manifest.load_manifest`, and
    returns the resulting :class:`~ci_feature.manifest.FeatureManifest` objects
    in deterministic order (sorted by the directory path that contains the
    manifest).

    Args:
        root_path: Path to the root of the repository to scan.

    Returns:
        A list of :class:`~ci_feature.manifest.FeatureManifest` instances,
        sorted alphabetically by the absolute path of each manifest's
        containing directory.  Returns an empty list when no ``feature.yml``
        files are found.
    """
    manifest_paths: List[str] = []

    for dirpath, _dirnames, filenames in os.walk(root_path):
        if _FEATURE_MANIFEST_FILENAME in filenames:
            manifest_paths.append(os.path.join(dirpath, _FEATURE_MANIFEST_FILENAME))

    manifest_paths.sort()

    return [load_manifest(path) for path in manifest_paths]
