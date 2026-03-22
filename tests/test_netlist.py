"""Unit tests for ci_feature.netlist."""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, contains_string, equal_to

from ci_feature.kicad_export import NetlistExportError, export_netlist
from ci_feature.manifest import FeatureManifest
from ci_feature.netlist import normalize_netlist

_INPUT_PATH = "/tmp/raw.net"
_OUTPUT_PATH = "/tmp/normalized.net"
_NETLIST_CONTENT = b"(nets (net (code 1) (name GND)))"


# ---------------------------------------------------------------------------
# Pass-through behaviour
# ---------------------------------------------------------------------------


def test_normalize_netlist_output_matches_input(fs):
    """normalize_netlist() copies input content to output unchanged."""
    fs.create_file(_INPUT_PATH, contents=_NETLIST_CONTENT)

    normalize_netlist(_INPUT_PATH, _OUTPUT_PATH)

    with open(_OUTPUT_PATH, "rb") as fh:
        result = fh.read()
    assert_that(result, equal_to(_NETLIST_CONTENT))


def test_normalize_netlist_creates_output_file(fs):
    """normalize_netlist() creates the output file."""
    fs.create_file(_INPUT_PATH, contents=_NETLIST_CONTENT)

    normalize_netlist(_INPUT_PATH, _OUTPUT_PATH)

    assert_that(os.path.isfile(_OUTPUT_PATH), equal_to(True))


def test_normalize_netlist_in_place(fs):
    """normalize_netlist() works when input_path and output_path are the same."""
    fs.create_file(_INPUT_PATH, contents=_NETLIST_CONTENT)

    normalize_netlist(_INPUT_PATH, _INPUT_PATH)

    with open(_INPUT_PATH, "rb") as fh:
        result = fh.read()
    assert_that(result, equal_to(_NETLIST_CONTENT))


# ---------------------------------------------------------------------------
# Hook is invoked by export_netlist
# ---------------------------------------------------------------------------


def test_export_netlist_calls_normalize_netlist(fs):
    """export_netlist() invokes normalize_netlist() with the raw netlist path."""
    manifest = FeatureManifest(
        name="voltage-regulator",
        version="1.0.0",
        schematic="schematic/voltage-regulator.kicad_sch",
        interface=["interface.yml"],
        models={"libraries": [], "required_parameters": []},
    )
    feature_dir = "/repo/features/voltage-regulator"
    output_dir = "/tmp/ci_workspace"
    expected_netlist = f"{output_dir}/voltage-regulator/voltage-regulator.net"

    fs.create_dir(feature_dir)

    def fake_run(cmd, **kwargs):
        fs.create_file(expected_netlist, contents="(nets)")
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    with patch("ci_feature.kicad_export.subprocess.run", side_effect=fake_run):
        with patch("ci_feature.kicad_export.normalize_netlist") as mock_normalize:
            export_netlist(manifest, output_dir, feature_dir=feature_dir)

    mock_normalize.assert_called_once_with(expected_netlist, expected_netlist)


def test_export_netlist_wraps_normalize_error_as_netlist_export_error(fs):
    """export_netlist() wraps OSError from normalize_netlist() as NetlistExportError."""
    manifest = FeatureManifest(
        name="voltage-regulator",
        version="1.0.0",
        schematic="schematic/voltage-regulator.kicad_sch",
        interface=["interface.yml"],
        models={"libraries": [], "required_parameters": []},
    )
    feature_dir = "/repo/features/voltage-regulator"
    output_dir = "/tmp/ci_workspace"
    expected_netlist = f"{output_dir}/voltage-regulator/voltage-regulator.net"

    fs.create_dir(feature_dir)

    def fake_run(cmd, **kwargs):
        fs.create_file(expected_netlist, contents="(nets)")
        result = MagicMock(spec=subprocess.CompletedProcess)
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    with patch("ci_feature.kicad_export.subprocess.run", side_effect=fake_run):
        with patch(
            "ci_feature.kicad_export.normalize_netlist",
            side_effect=OSError("disk full"),
        ):
            with pytest.raises(NetlistExportError) as exc_info:
                export_netlist(manifest, output_dir, feature_dir=feature_dir)

    assert_that(str(exc_info.value), contains_string("voltage-regulator"))
    assert_that(str(exc_info.value), contains_string("disk full"))
