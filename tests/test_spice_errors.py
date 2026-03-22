"""Unit tests for ngspice error classification in ci_feature.spice_runner."""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, contains_string, equal_to, instance_of

from ci_feature.spice_errors import (
    ConvergenceError,
    MissingModelError,
    SpiceRunError,
    SpiceSyntaxError,
)
from ci_feature.spice_runner import run_spice

_NETLIST_PATH = "/tmp/ci/fixtures/test.spice"
_OUTPUT_DIR = "/tmp/ci_workspace/spice_errors"

# Paths to the error-triggering fixtures shipped with the repository.
_MISSING_MODEL_FIXTURE = os.path.join(
    os.path.dirname(__file__), "..", "ci", "fixtures", "missing_model.spice"
)
_SYNTAX_ERROR_FIXTURE = os.path.join(
    os.path.dirname(__file__), "..", "ci", "fixtures", "syntax_error.spice"
)


def _make_completed_process(returncode=0, stdout="", stderr=""):
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


# ---------------------------------------------------------------------------
# Exception class hierarchy
# ---------------------------------------------------------------------------


def test_missing_model_error_is_subclass_of_spice_run_error():
    """MissingModelError is a subclass of SpiceRunError."""
    assert_that(issubclass(MissingModelError, SpiceRunError), equal_to(True))


def test_spice_syntax_error_is_subclass_of_spice_run_error():
    """SpiceSyntaxError is a subclass of SpiceRunError."""
    assert_that(issubclass(SpiceSyntaxError, SpiceRunError), equal_to(True))


def test_convergence_error_is_subclass_of_spice_run_error():
    """ConvergenceError is a subclass of SpiceRunError."""
    assert_that(issubclass(ConvergenceError, SpiceRunError), equal_to(True))


def test_missing_model_error_is_catchable_as_spice_run_error():
    """MissingModelError can be caught as a SpiceRunError."""
    with pytest.raises(SpiceRunError):
        raise MissingModelError("test")


def test_spice_syntax_error_is_catchable_as_spice_run_error():
    """SpiceSyntaxError can be caught as a SpiceRunError."""
    with pytest.raises(SpiceRunError):
        raise SpiceSyntaxError("test")


def test_convergence_error_is_catchable_as_spice_run_error():
    """ConvergenceError can be caught as a SpiceRunError."""
    with pytest.raises(SpiceRunError):
        raise ConvergenceError("test")


# ---------------------------------------------------------------------------
# MissingModelError classification
# ---------------------------------------------------------------------------


def test_run_spice_raises_missing_model_error_on_include_not_found(fs):
    """run_spice() raises MissingModelError when output contains 'include not found'."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stdout="",
            stderr="ERROR: .include not found: nonexistent_model.lib",
        ),
    ):
        with pytest.raises(MissingModelError):
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)


def test_run_spice_missing_model_error_is_instance_of_missing_model_error(fs):
    """MissingModelError raised by run_spice() is an instance of MissingModelError."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stderr="include not found: missing.lib",
        ),
    ):
        with pytest.raises(MissingModelError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(exc_info.value, instance_of(MissingModelError))


def test_run_spice_missing_model_error_message_includes_stderr(fs):
    """MissingModelError message includes the ngspice stderr output."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stderr="ERROR: .include not found: nonexistent_model.lib",
        ),
    ):
        with pytest.raises(MissingModelError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("nonexistent_model.lib"))


def test_run_spice_missing_model_error_message_includes_exit_code(fs):
    """MissingModelError message includes the non-zero exit code."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stderr="include not found: missing.lib",
        ),
    ):
        with pytest.raises(MissingModelError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("1"))


def test_run_spice_missing_model_error_message_includes_command(fs):
    """MissingModelError message includes the ngspice command."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stderr="include not found: missing.lib",
        ),
    ):
        with pytest.raises(MissingModelError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("ngspice"))


# ---------------------------------------------------------------------------
# SpiceSyntaxError classification
# ---------------------------------------------------------------------------


def test_run_spice_raises_spice_syntax_error_on_parse_error(fs):
    """run_spice() raises SpiceSyntaxError when stderr contains 'parse error'."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stderr="fatal: parse error at line 3",
        ),
    ):
        with pytest.raises(SpiceSyntaxError):
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)


def test_run_spice_raises_spice_syntax_error_on_syntax_error(fs):
    """run_spice() raises SpiceSyntaxError when stderr contains 'syntax error'."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stderr="syntax error: unexpected token '%%%'",
        ),
    ):
        with pytest.raises(SpiceSyntaxError):
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)


def test_run_spice_spice_syntax_error_is_instance_of_spice_syntax_error(fs):
    """SpiceSyntaxError raised by run_spice() is an instance of SpiceSyntaxError."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stderr="parse error at line 5",
        ),
    ):
        with pytest.raises(SpiceSyntaxError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(exc_info.value, instance_of(SpiceSyntaxError))


def test_run_spice_spice_syntax_error_message_includes_stderr(fs):
    """SpiceSyntaxError message includes the ngspice stderr output."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stderr="parse error at line 5: unexpected '%%%'",
        ),
    ):
        with pytest.raises(SpiceSyntaxError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("parse error at line 5"))


def test_run_spice_spice_syntax_error_message_includes_stdout(fs):
    """SpiceSyntaxError message includes the ngspice stdout output."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stdout="ngspice starting",
            stderr="syntax error in model definition",
        ),
    ):
        with pytest.raises(SpiceSyntaxError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("ngspice starting"))


# ---------------------------------------------------------------------------
# ConvergenceError classification
# ---------------------------------------------------------------------------


def test_run_spice_raises_convergence_error_on_no_convergence(fs):
    """run_spice() raises ConvergenceError when output contains 'no convergence'."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stdout="no convergence in transient analysis",
        ),
    ):
        with pytest.raises(ConvergenceError):
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)


def test_run_spice_raises_convergence_error_on_timestep_too_small(fs):
    """run_spice() raises ConvergenceError when output contains 'timestep too small'."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stdout="timestep too small: 1e-18",
        ),
    ):
        with pytest.raises(ConvergenceError):
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)


def test_run_spice_convergence_error_is_instance_of_convergence_error(fs):
    """ConvergenceError raised by run_spice() is an instance of ConvergenceError."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stdout="no convergence in dc analysis",
        ),
    ):
        with pytest.raises(ConvergenceError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(exc_info.value, instance_of(ConvergenceError))


def test_run_spice_convergence_error_message_includes_stdout(fs):
    """ConvergenceError message includes the ngspice stdout output."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stdout="no convergence in transient analysis at t=1.23e-9",
        ),
    ):
        with pytest.raises(ConvergenceError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("no convergence in transient analysis"))


def test_run_spice_convergence_error_message_includes_exit_code(fs):
    """ConvergenceError message includes the non-zero exit code."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stdout="no convergence in dc analysis",
        ),
    ):
        with pytest.raises(ConvergenceError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(str(exc_info.value), contains_string("1"))


# ---------------------------------------------------------------------------
# Generic SpiceRunError (unclassified)
# ---------------------------------------------------------------------------


def test_run_spice_raises_spice_run_error_for_unclassified_failure(fs):
    """run_spice() raises SpiceRunError when output does not match any known pattern."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stdout="some unknown error",
            stderr="something went wrong",
        ),
    ):
        with pytest.raises(SpiceRunError):
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)


def test_run_spice_unclassified_error_is_exactly_spice_run_error(fs):
    """run_spice() raises exactly SpiceRunError (not a subclass) for unclassified failures."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stdout="some unknown error",
            stderr="something went wrong",
        ),
    ):
        with pytest.raises(SpiceRunError) as exc_info:
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(type(exc_info.value), equal_to(SpiceRunError))


# ---------------------------------------------------------------------------
# Case-insensitive classification
# ---------------------------------------------------------------------------


def test_run_spice_missing_model_detection_is_case_insensitive(fs):
    """MissingModelError classification is case-insensitive."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stderr="Include Not Found: model.lib",
        ),
    ):
        with pytest.raises(MissingModelError):
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)


def test_run_spice_syntax_error_detection_is_case_insensitive(fs):
    """SpiceSyntaxError classification is case-insensitive."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stderr="Parse Error at line 7",
        ),
    ):
        with pytest.raises(SpiceSyntaxError):
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)


def test_run_spice_convergence_detection_is_case_insensitive(fs):
    """ConvergenceError classification is case-insensitive."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(
            returncode=1,
            stdout="No Convergence in DC analysis",
        ),
    ):
        with pytest.raises(ConvergenceError):
            run_spice(_NETLIST_PATH, _OUTPUT_DIR)


# ---------------------------------------------------------------------------
# Fixture files exist
# ---------------------------------------------------------------------------


def test_missing_model_fixture_exists():
    """The missing_model.spice fixture file exists in the repository."""
    assert_that(os.path.isfile(_MISSING_MODEL_FIXTURE), equal_to(True))


def test_syntax_error_fixture_exists():
    """The syntax_error.spice fixture file exists in the repository."""
    assert_that(os.path.isfile(_SYNTAX_ERROR_FIXTURE), equal_to(True))
