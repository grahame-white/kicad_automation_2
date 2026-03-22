"""Validation helpers for SPICE model file presence."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ci_feature.spice_errors import MissingModelError

if TYPE_CHECKING:
    from ci_feature.manifest import FeatureManifest

__all__ = ["validate_model_presence"]


def validate_model_presence(manifest: FeatureManifest, feature_dir: str) -> None:
    """Check that all SPICE model libraries declared in *manifest* exist.

    Resolves each path in ``manifest.models["libraries"]`` relative to
    *feature_dir* and raises :class:`MissingModelError` if any are absent.
    This function is intended to be called as a pre-flight check before
    invoking ngspice, so that CI fails fast with a clear error rather than
    waiting for ngspice to report a missing-include error.

    Args:
        manifest: A :class:`~ci_feature.manifest.FeatureManifest` instance
            whose ``models["libraries"]`` paths will be verified.
        feature_dir: The directory containing the ``feature.yml`` manifest.
            Model library paths are resolved relative to this directory.
            The path is normalised with :func:`os.path.realpath` before use.

    Raises:
        MissingModelError: If one or more model library files do not exist.
            The error message includes the feature name and the full list of
            missing absolute paths.
    """
    libraries = manifest.models.get("libraries", [])
    feature_dir = os.path.realpath(feature_dir)
    missing = []

    for lib in libraries:
        abs_path = os.path.realpath(os.path.join(feature_dir, lib))
        if not os.path.isfile(abs_path):
            missing.append(abs_path)

    if missing:
        missing_list = "\n".join(f"  {p}" for p in missing)
        raise MissingModelError(
            f"Feature '{manifest.name}' is missing "
            f"{len(missing)} model {'file' if len(missing) == 1 else 'files'}:\n"
            f"{missing_list}"
        )
