"""Scenario discovery: pair feature manifests with their ``.feature`` scenario files."""

import os
from pathlib import Path
from typing import List, Tuple

from ci_feature.discovery import FEATURE_MANIFEST_FILENAME, PRUNE_DIRS, discover_features
from ci_feature.manifest import FeatureManifest

__all__ = ["discover_scenarios"]

_SCENARIO_FILE_EXTENSION = ".feature"


def discover_scenarios(root_path: str) -> List[Tuple[FeatureManifest, Path]]:
    """Discover all scenario files paired with their feature manifests.

    For every feature found by :func:`~ci_feature.discovery.discover_features`,
    recursively scans the feature's directory for ``*.feature`` scenario files
    and produces a ``(manifest, scenario_path)`` pair for each one found.

    Subdirectories that are themselves feature roots (i.e. they contain a
    ``feature.yml`` file) are not descended into — those scenarios will be
    attributed to their own manifest when that manifest is processed.

    The returned list is sorted deterministically by ``(feature directory,
    scenario file path)`` so that output is stable across CI runs regardless
    of filesystem traversal order.

    Args:
        root_path: Path to the root of the repository to scan.

    Returns:
        A list of ``(FeatureManifest, Path)`` tuples, sorted by
        ``(manifest.directory, scenario_file_path)``.  Returns an empty list
        when no feature manifests are found or when no manifests contain any
        ``*.feature`` files.
    """
    manifests = discover_features(root_path)

    pairs: List[Tuple[FeatureManifest, Path]] = []

    for manifest in manifests:
        feature_dir = manifest.directory
        if not feature_dir:
            continue

        scenario_paths: List[Path] = []
        for dirpath, dirnames, filenames in os.walk(feature_dir):
            dirnames[:] = sorted(
                d
                for d in dirnames
                if d not in PRUNE_DIRS
                and not os.path.isfile(os.path.join(dirpath, d, FEATURE_MANIFEST_FILENAME))
            )
            for filename in sorted(filenames):
                if filename.endswith(_SCENARIO_FILE_EXTENSION):
                    scenario_paths.append(Path(os.path.join(dirpath, filename)))

        scenario_paths.sort()
        for scenario_path in scenario_paths:
            pairs.append((manifest, scenario_path))

    pairs.sort(key=lambda pair: (pair[0].directory or "", str(pair[1])))

    return pairs
