"""KiCad netlist export via kicad-cli."""

import os
import shlex
import subprocess

from ci_feature.manifest import FeatureManifest
from ci_feature.netlist import normalize_netlist

__all__ = [
    "NetlistExportError",
    "export_netlist",
]


class NetlistExportError(Exception):
    """Raised when netlist export fails or produces an empty/missing output file."""


def export_netlist(manifest: FeatureManifest, output_dir: str, feature_dir: str = ".") -> str:
    """Export a KiCad netlist for the given feature manifest using ``kicad-cli``.

    Runs ``kicad-cli sch export netlist`` on the schematic referenced in
    *manifest* and writes the result to a per-feature subdirectory inside
    *output_dir*.

    Args:
        manifest: A validated :class:`~ci_feature.manifest.FeatureManifest`
            describing the feature whose schematic should be exported.
        output_dir: Path to the root CI workspace directory.  A subdirectory
            named after the feature will be created inside it to hold the
            exported netlist.
        feature_dir: Path to the feature's root directory.  Used to resolve
            the relative ``schematic`` path stored in *manifest*.  Defaults to
            the current working directory.

    Returns:
        The absolute path to the generated netlist file.

    Raises:
        NetlistExportError: If *manifest.name* contains path separators or
            parent-directory references that could escape *output_dir*; if
            ``kicad-cli`` cannot be launched (e.g. not installed); if
            ``kicad-cli`` exits with a non-zero status; or if the output file
            is missing or empty after a successful run.  Error messages include
            any captured stdout/stderr from ``kicad-cli`` and the command that
            was attempted, so the failure is immediately actionable.
    """
    # Resolve output_dir to an absolute path so the returned netlist path is
    # always absolute regardless of the caller's working directory.
    output_dir = os.path.realpath(output_dir)

    schematic_path = os.path.realpath(os.path.join(feature_dir, manifest.schematic))

    # Validate the feature name before using it as a filesystem path component.
    # os.path.basename strips any leading directory components, so if the result
    # differs from the original name the name contains path separators (or
    # parent-directory references like "..") that could escape output_dir.
    # Also check for backslashes explicitly since they are not path separators on
    # Linux but could cause portability issues or indicate a malformed name.
    feature_name = os.path.basename(manifest.name)
    if feature_name != manifest.name or feature_name in ("", ".", "..") or "\\" in manifest.name:
        raise NetlistExportError(
            f"Invalid feature name '{manifest.name}'. Feature names must not contain "
            f"path separators or parent directory references."
        )

    feature_output_dir = os.path.join(output_dir, feature_name)
    os.makedirs(feature_output_dir, exist_ok=True)

    netlist_filename = f"{feature_name}.net"
    netlist_path = os.path.join(feature_output_dir, netlist_filename)

    cmd = [
        "kicad-cli",
        "sch",
        "export",
        "netlist",
        "--output",
        netlist_path,
        schematic_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        raise NetlistExportError(
            f"Failed to run kicad-cli for feature '{manifest.name}'.\n"
            f"Command: {shlex.join(cmd)}\n"
            f"Original error: {exc.__class__.__name__}: {exc}"
        ) from exc

    if result.returncode != 0:
        raise NetlistExportError(
            f"kicad-cli failed for feature '{manifest.name}' "
            f"(exit code {result.returncode}).\n"
            f"Command: {shlex.join(cmd)}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    if not os.path.isfile(netlist_path):
        raise NetlistExportError(
            f"kicad-cli completed successfully but the expected netlist file was not created: "
            f"{netlist_path}"
        )

    if os.path.getsize(netlist_path) == 0:
        raise NetlistExportError(
            f"kicad-cli produced an empty netlist file for feature '{manifest.name}': "
            f"{netlist_path}"
        )

    try:
        normalize_netlist(netlist_path, netlist_path)
    except NetlistExportError:
        # Preserve any explicit NetlistExportError raised by normalize_netlist.
        raise
    except Exception as exc:
        # Wrap unexpected errors to keep the export_netlist API contract.
        raise NetlistExportError(
            f"Failed to normalize netlist for feature '{manifest.name}' at '{netlist_path}'. "
            f"Original error: {exc.__class__.__name__}: {exc}"
        ) from exc

    return netlist_path
