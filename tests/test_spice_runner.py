"""Unit tests for ci_feature.spice_runner."""

import os
import shutil
import subprocess
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, contains_string, equal_to, instance_of

from ci_feature.spice_runner import SpiceResult, SpiceRunError, run_spice

_NETLIST_PATH = "/tmp/ci/fixtures/minimal.spice"
_OUTPUT_DIR = "/tmp/ci_workspace/spice"
_LOG_PATH = f"{_OUTPUT_DIR}/ngspice.log"

# Path to the known-good fixture shipped with the repository.
_FIXTURE_NETLIST = os.path.join(os.path.dirname(__file__), "..", "ci", "fixtures", "minimal.spice")


def _make_completed_process(returncode=0, stdout="", stderr=""):
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


# ---------------------------------------------------------------------------
# Successful run
# ---------------------------------------------------------------------------


def test_run_spice_returns_spice_result(fs):
    """run_spice() returns a SpiceResult on success."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(returncode=0, stdout="ngspice output"),
    ):
        result = run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(result, instance_of(SpiceResult))


def test_run_spice_result_has_zero_returncode(fs):
    """run_spice() result has returncode 0 on success."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(returncode=0),
    ):
        result = run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(result.returncode, equal_to(0))


def test_run_spice_result_captures_stdout(fs):
    """run_spice() captures ngspice stdout."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(returncode=0, stdout="simulation complete"),
    ):
        result = run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(result.stdout, contains_string("simulation complete"))


def test_run_spice_result_captures_stderr(fs):
    """run_spice() captures ngspice stderr."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(returncode=0, stderr="warning: something"),
    ):
        result = run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(result.stderr, contains_string("warning: something"))


def test_run_spice_result_log_path_is_in_output_dir(fs):
    """run_spice() result log_path is inside output_dir."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(returncode=0),
    ):
        result = run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(result.log_path, equal_to(_LOG_PATH))


def test_run_spice_creates_output_directory(fs):
    """run_spice() creates output_dir if it does not exist."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(returncode=0),
    ):
        run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(os.path.isdir(_OUTPUT_DIR), equal_to(True))


def test_run_spice_passes_batch_flag(fs):
    """run_spice() invokes ngspice with the -b (batch) flag."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    captured_cmd = []

    def fake_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        return _make_completed_process(returncode=0)

    with patch("ci_feature.spice_runner.subprocess.run", side_effect=fake_run):
        run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(captured_cmd[0], equal_to("ngspice"))
    assert_that("-b" in captured_cmd, equal_to(True))


def test_run_spice_passes_netlist_path(fs):
    """run_spice() passes the netlist path to ngspice."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    captured_cmd = []

    def fake_run(cmd, **kwargs):
        captured_cmd.extend(cmd)
        return _make_completed_process(returncode=0)

    with patch("ci_feature.spice_runner.subprocess.run", side_effect=fake_run):
        run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(any(arg.endswith("minimal.spice") for arg in captured_cmd), equal_to(True))


def test_run_spice_passes_timeout_to_subprocess(fs):
    """run_spice() passes the timeout argument to subprocess.run."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    captured_kwargs = {}

    def fake_run(cmd, **kwargs):
        captured_kwargs.update(kwargs)
        return _make_completed_process(returncode=0)

    with patch("ci_feature.spice_runner.subprocess.run", side_effect=fake_run):
        run_spice(_NETLIST_PATH, _OUTPUT_DIR, timeout=120)

    assert_that(captured_kwargs.get("timeout"), equal_to(120))


def test_run_spice_default_timeout_is_sixty(fs):
    """run_spice() uses a default timeout of 60 seconds."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    captured_kwargs = {}

    def fake_run(cmd, **kwargs):
        captured_kwargs.update(kwargs)
        return _make_completed_process(returncode=0)

    with patch("ci_feature.spice_runner.subprocess.run", side_effect=fake_run):
        run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(captured_kwargs.get("timeout"), equal_to(60))


# ---------------------------------------------------------------------------
# Missing netlist
# ---------------------------------------------------------------------------


def test_run_spice_raises_when_netlist_missing(fs):
    """run_spice() raises SpiceRunError when the netlist file does not exist."""
    with pytest.raises(SpiceRunError) as exc_info:
        run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string(_NETLIST_PATH))


def test_run_spice_missing_netlist_error_includes_command(fs):
    """SpiceRunError for missing netlist includes the would-be command."""
    with pytest.raises(SpiceRunError) as exc_info:
        run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("ngspice"))


def test_run_spice_missing_netlist_error_is_spice_run_error(fs):
    """SpiceRunError for missing netlist is an instance of SpiceRunError."""
    with pytest.raises(SpiceRunError) as exc_info:
        run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(exc_info.value, instance_of(SpiceRunError))


# ---------------------------------------------------------------------------
# Non-zero exit code
# ---------------------------------------------------------------------------


def test_run_spice_raises_on_nonzero_exit(fs):
    """run_spice() raises SpiceRunError when ngspice exits non-zero."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(returncode=1, stdout="", stderr="error"),
    ):
        with pytest.raises(SpiceRunError):
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)


def test_run_spice_error_includes_exit_code(fs):
    """SpiceRunError message includes the non-zero exit code."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(returncode=2, stdout="", stderr=""),
    ):
        with pytest.raises(SpiceRunError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("2"))


def test_run_spice_error_includes_stdout(fs):
    """SpiceRunError message includes stdout from ngspice."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(returncode=1, stdout="this is stdout", stderr=""),
    ):
        with pytest.raises(SpiceRunError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("this is stdout"))


def test_run_spice_error_includes_stderr(fs):
    """SpiceRunError message includes stderr from ngspice."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(returncode=1, stdout="", stderr="fatal: parse error"),
    ):
        with pytest.raises(SpiceRunError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("fatal: parse error"))


# ---------------------------------------------------------------------------
# subprocess launch failures
# ---------------------------------------------------------------------------


def test_run_spice_raises_when_ngspice_not_found(fs):
    """run_spice() raises SpiceRunError when ngspice is not installed."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        side_effect=FileNotFoundError("No such file or directory: 'ngspice'"),
    ):
        with pytest.raises(SpiceRunError):
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)


def test_run_spice_error_message_includes_command_when_ngspice_not_found(fs):
    """SpiceRunError for missing ngspice includes the attempted command."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        side_effect=FileNotFoundError("No such file or directory: 'ngspice'"),
    ):
        with pytest.raises(SpiceRunError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("ngspice"))


def test_run_spice_chains_original_exception_on_file_not_found(fs):
    """SpiceRunError chains the original FileNotFoundError as __cause__."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    original = FileNotFoundError("No such file or directory: 'ngspice'")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        side_effect=original,
    ):
        with pytest.raises(SpiceRunError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(exc_info.value.__cause__, instance_of(FileNotFoundError))


def test_run_spice_raises_spice_run_error_on_os_error(fs):
    """run_spice() raises SpiceRunError when subprocess.run raises OSError."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        side_effect=OSError("permission denied"),
    ):
        with pytest.raises(SpiceRunError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("permission denied"))


def test_run_spice_raises_spice_run_error_on_timeout(fs):
    """run_spice() raises SpiceRunError when subprocess.run times out."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["ngspice"], timeout=30),
    ):
        with pytest.raises(SpiceRunError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("ngspice"))


def test_run_spice_timeout_includes_partial_stdout(fs):
    """SpiceRunError for timeout includes partial stdout when available."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    exc = subprocess.TimeoutExpired(cmd=["ngspice"], timeout=30, output="partial output text")

    with patch("ci_feature.spice_runner.subprocess.run", side_effect=exc):
        with pytest.raises(SpiceRunError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("partial output text"))


def test_run_spice_timeout_includes_partial_stderr(fs):
    """SpiceRunError for timeout includes partial stderr when available."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    exc = subprocess.TimeoutExpired(cmd=["ngspice"], timeout=30, stderr="partial stderr text")

    with patch("ci_feature.spice_runner.subprocess.run", side_effect=exc):
        with pytest.raises(SpiceRunError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("partial stderr text"))


# ---------------------------------------------------------------------------
# Integration test — skipped when ngspice is not installed
# ---------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("ngspice") is None, reason="ngspice not installed")
def test_run_spice_with_real_fixture():
    """run_spice() succeeds against the known-good minimal fixture when ngspice is available."""
    with tempfile.TemporaryDirectory() as output_dir:
        result = run_spice(_FIXTURE_NETLIST, output_dir)

        assert_that(result, instance_of(SpiceResult))
        assert_that(result.returncode, equal_to(0))
        assert_that(os.path.isfile(result.log_path), equal_to(True))
