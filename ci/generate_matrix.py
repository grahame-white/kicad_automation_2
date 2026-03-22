"""Generate a GitHub Actions matrix JSON array of feature directories.

Discovers all feature directories in the repository and prints a JSON array
of their paths relative to the repository root.  The output is suitable for
use as a GitHub Actions matrix value::

    echo "matrix=$(python ci/generate_matrix.py)" >> $GITHUB_OUTPUT

Usage::

    python ci/generate_matrix.py [root_path]

If *root_path* is omitted, the repository root is inferred as the parent
directory of this script's location (i.e. the repository root when the
script lives at ``ci/generate_matrix.py``).
"""

import json
import os
import sys

# Allow the script to be run from any working directory by ensuring the repo
# root is on sys.path so that ci_feature can be imported.
_SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from ci_feature.discovery import discover_features  # noqa: E402


def generate_matrix(root_path: str) -> list[str]:
    """Return a sorted list of feature directory paths relative to *root_path*.

    Each entry is a POSIX-style path suitable for use in a ``behave``
    invocation such as ``behave <entry>/``.

    Args:
        root_path: Absolute path to the repository root.

    Returns:
        A sorted list of unique feature directory paths relative to
        *root_path*, deduplicated and in deterministic order.
    """
    manifests = discover_features(root_path)
    real_root = os.path.realpath(root_path)

    paths: list[str] = []
    for manifest in manifests:
        if not manifest.directory:
            continue
        feature_dir = os.path.realpath(manifest.directory)
        rel = os.path.relpath(feature_dir, real_root)
        # Normalise to forward slashes for cross-platform consistency and
        # GitHub Actions matrix value readability.
        paths.append(rel.replace(os.sep, "/"))

    return sorted(set(paths))


def main() -> None:
    """Entry point: print the matrix JSON array to stdout."""
    root_path = sys.argv[1] if len(sys.argv) > 1 else _REPO_ROOT
    matrix = generate_matrix(root_path)
    print(json.dumps(matrix))


if __name__ == "__main__":
    main()
