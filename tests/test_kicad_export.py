"""Unit tests for ci_feature.kicad_export."""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, contains_string, equal_to, instance_of

from ci_feature.kicad_export import NetlistExportError, export_netlist
from ci_feature.manifest import FeatureManifest

# A minimal FeatureManifest used across tests.
_MANIFEST = FeatureManifest(
    name="voltage-regulator",
    version="1.0.0",
    schematic="schematic/voltage-regulator.kicad_sch",
    interface=["interface.yml"],
    models={"libraries": ["models/ldo.spice"], "required_parameters": ["V_IN"]},
)

_FEATURE_DIR = "/repo/features/voltage-regulator"
_OUTPUT_DIR = "/tmp/ci_workspace"
_EXPECTED_NETLIST_PATH = f"{_OUTPUT_DIR}/voltage-regulator/voltage-regulator.net"


def _make_completed_process(returncode=0, stdout="", stderr=""):
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


# ---------------------------------------------------------------------------
# Successful export
# ---------------------------------------------------------------------------


def test_export_netlist_returns_netlist_path(fs):
    """export_netlist() returns the path to the generated netlist file."""
    fs.create_dir(_FEATURE_DIR)
    fs.create_dir(f"{_FEATURE_DIR}/schematic")

    def fake_run(cmd, **kwargs):
        # Simulate kicad-cli writing the netlist file.
        fs.create_file(_EXPECTED_NETLIST_PATH, contents="(nets)")
        return _make_completed_process(returncode=0)

    with patch("ci_feature.kicad_export.subprocess.run", side_effect=fake_run):
        result = export_netlist(_MANIFEST, _OUTPUT_DIR, feature_dir=_FEATURE_DIR)

    assert_that(result, equal_to(_EXPECTED_NETLIST_PATH))


def test_export_netlist_creates_output_directory(fs):
    """export_netlist() creates the per-feature output subdirectory if it does not exist."""
    fs.create_dir(_FEATURE_DIR)

    def fake_run(cmd, **kwargs):
        fs.create_file(_EXPECTED_NETLIST_PATH, contents="(nets)")
        return _make_completed_process(returncode=0)

    with patch("ci_feature.kicad_export.subprocess.run", side_effect=fake_run):
        export_netlist(_MANIFEST, _OUTPUT_DIR, feature_dir=_FEATURE_DIR)

    assert_that(os.path.isdir(f"{_OUTPUT_DIR}/voltage-regulator"), equal_to(True))


def test_export_netlist_passes_correct_command(fs):
    """export_netlist() invokes kicad-cli with the correct arguments."""
    fs.create_dir(_FEATURE_DIR)
    captured_cmd = []

    def fake_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        fs.create_file(_EXPECTED_NETLIST_PATH, contents="(nets)")
        return _make_completed_process(returncode=0)

    with patch("ci_feature.kicad_export.subprocess.run", side_effect=fake_run):
        export_netlist(_MANIFEST, _OUTPUT_DIR, feature_dir=_FEATURE_DIR)

    assert_that(captured_cmd[0], equal_to("kicad-cli"))
    assert_that(captured_cmd[1], equal_to("sch"))
    assert_that(captured_cmd[2], equal_to("export"))
    assert_that(captured_cmd[3], equal_to("netlist"))
    assert_that("--output" in captured_cmd, equal_to(True))
    assert_that(
        any(arg.endswith("voltage-regulator.kicad_sch") for arg in captured_cmd), equal_to(True)
    )


# ---------------------------------------------------------------------------
# Non-zero exit code
# ---------------------------------------------------------------------------


def test_export_netlist_raises_on_nonzero_exit(fs):
    """export_netlist() raises NetlistExportError when kicad-cli exits non-zero."""
    fs.create_dir(_FEATURE_DIR)

    with patch(
        "ci_feature.kicad_export.subprocess.run",
        return_value=_make_completed_process(
            returncode=1, stdout="some output", stderr="some error"
        ),
    ):
        with pytest.raises(NetlistExportError):
            export_netlist(_MANIFEST, _OUTPUT_DIR, feature_dir=_FEATURE_DIR)


def test_export_netlist_error_includes_exit_code(fs):
    """NetlistExportError message includes the non-zero exit code."""
    fs.create_dir(_FEATURE_DIR)

    with patch(
        "ci_feature.kicad_export.subprocess.run",
        return_value=_make_completed_process(returncode=2, stdout="", stderr=""),
    ):
        with pytest.raises(NetlistExportError) as exc_info:
            export_netlist(_MANIFEST, _OUTPUT_DIR, feature_dir=_FEATURE_DIR)

    assert_that(str(exc_info.value), contains_string("2"))


def test_export_netlist_error_includes_stdout(fs):
    """NetlistExportError message includes stdout from kicad-cli."""
    fs.create_dir(_FEATURE_DIR)

    with patch(
        "ci_feature.kicad_export.subprocess.run",
        return_value=_make_completed_process(returncode=1, stdout="this is stdout", stderr=""),
    ):
        with pytest.raises(NetlistExportError) as exc_info:
            export_netlist(_MANIFEST, _OUTPUT_DIR, feature_dir=_FEATURE_DIR)

    assert_that(str(exc_info.value), contains_string("this is stdout"))


def test_export_netlist_error_includes_stderr(fs):
    """NetlistExportError message includes stderr from kicad-cli."""
    fs.create_dir(_FEATURE_DIR)

    with patch(
        "ci_feature.kicad_export.subprocess.run",
        return_value=_make_completed_process(
            returncode=1, stdout="", stderr="fatal: schematic not found"
        ),
    ):
        with pytest.raises(NetlistExportError) as exc_info:
            export_netlist(_MANIFEST, _OUTPUT_DIR, feature_dir=_FEATURE_DIR)

    assert_that(str(exc_info.value), contains_string("fatal: schematic not found"))


def test_export_netlist_error_includes_feature_name(fs):
    """NetlistExportError message includes the feature name for actionability."""
    fs.create_dir(_FEATURE_DIR)

    with patch(
        "ci_feature.kicad_export.subprocess.run",
        return_value=_make_completed_process(returncode=1, stdout="", stderr=""),
    ):
        with pytest.raises(NetlistExportError) as exc_info:
            export_netlist(_MANIFEST, _OUTPUT_DIR, feature_dir=_FEATURE_DIR)

    assert_that(str(exc_info.value), contains_string("voltage-regulator"))


# ---------------------------------------------------------------------------
# Missing or empty output file
# ---------------------------------------------------------------------------


def test_export_netlist_raises_when_output_file_missing(fs):
    """export_netlist() raises NetlistExportError when the output file is not created."""
    fs.create_dir(_FEATURE_DIR)

    with patch(
        "ci_feature.kicad_export.subprocess.run",
        return_value=_make_completed_process(returncode=0),
    ):
        with pytest.raises(NetlistExportError) as exc_info:
            export_netlist(_MANIFEST, _OUTPUT_DIR, feature_dir=_FEATURE_DIR)

    assert_that(str(exc_info.value), contains_string(_EXPECTED_NETLIST_PATH))


def test_export_netlist_raises_when_output_file_empty(fs):
    """export_netlist() raises NetlistExportError when the output file is empty."""
    fs.create_dir(_FEATURE_DIR)

    def fake_run(cmd, **kwargs):
        fs.create_file(_EXPECTED_NETLIST_PATH, contents="")
        return _make_completed_process(returncode=0)

    with patch("ci_feature.kicad_export.subprocess.run", side_effect=fake_run):
        with pytest.raises(NetlistExportError) as exc_info:
            export_netlist(_MANIFEST, _OUTPUT_DIR, feature_dir=_FEATURE_DIR)

    assert_that(str(exc_info.value), contains_string("voltage-regulator"))
    assert_that(str(exc_info.value), contains_string(_EXPECTED_NETLIST_PATH))


def test_export_netlist_missing_file_error_is_netlist_export_error(fs):
    """NetlistExportError for missing output file is an instance of NetlistExportError."""
    fs.create_dir(_FEATURE_DIR)

    with patch(
        "ci_feature.kicad_export.subprocess.run",
        return_value=_make_completed_process(returncode=0),
    ):
        with pytest.raises(NetlistExportError) as exc_info:
            export_netlist(_MANIFEST, _OUTPUT_DIR, feature_dir=_FEATURE_DIR)

    assert_that(exc_info.value, instance_of(NetlistExportError))
