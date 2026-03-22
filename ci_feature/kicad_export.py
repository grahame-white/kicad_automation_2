"""KiCad netlist export via kicad-cli."""

import os
import subprocess

from ci_feature.manifest import FeatureManifest

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
        NetlistExportError: If ``kicad-cli`` exits with a non-zero status, or
            if the output file is missing or empty after a successful run.  The
            error message includes any captured stdout/stderr from
            ``kicad-cli``.
    """
    schematic_path = os.path.realpath(os.path.join(feature_dir, manifest.schematic))

    feature_output_dir = os.path.join(output_dir, manifest.name)
    os.makedirs(feature_output_dir, exist_ok=True)

    netlist_filename = f"{manifest.name}.net"
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

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise NetlistExportError(
            f"kicad-cli failed for feature '{manifest.name}' "
            f"(exit code {result.returncode}).\n"
            f"Command: {' '.join(cmd)}\n"
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

    return netlist_path
