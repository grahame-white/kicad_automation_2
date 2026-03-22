"""Unit tests for ci_feature.spice_runner."""

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, contains_string, equal_to, has_entry, instance_of

from ci_feature.spice_errors import MissingModelError, MissingParameterError
from ci_feature.spice_runner import SpiceResult, SpiceRunError, parse_measure_results, run_spice

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
# Pre-flight model presence check via manifest parameter
# ---------------------------------------------------------------------------

_FEATURE_DIR = "/tmp/ci/features/my-feature"


@dataclass
class _FakeManifest:
    """Minimal stand-in for FeatureManifest used in spice_runner pre-flight tests."""

    name: str
    models: Dict[str, Any]
    version: str = "1.0.0"
    schematic: str = "schematic/test.kicad_sch"
    interface: Optional[List[str]] = None
    configuration: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.interface is None:
            self.interface = ["interface.yml"]


def test_run_spice_with_manifest_validates_model_presence(fs):
    """run_spice() calls validate_model_presence before launching ngspice when manifest provided."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="my-feature",
        models={"libraries": ["models/missing.spice"], "required_parameters": []},
    )

    with pytest.raises(MissingModelError):
        run_spice(_NETLIST_PATH, _OUTPUT_DIR, manifest=manifest, feature_dir=_FEATURE_DIR)


def test_run_spice_with_manifest_raises_before_subprocess_when_model_missing(fs):
    """run_spice() raises MissingModelError without calling subprocess when a model is absent."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="my-feature",
        models={"libraries": ["models/absent.spice"], "required_parameters": []},
    )

    with patch("ci_feature.spice_runner.subprocess.run") as mock_run:
        with pytest.raises(MissingModelError):
            run_spice(_NETLIST_PATH, _OUTPUT_DIR, manifest=manifest, feature_dir=_FEATURE_DIR)

    mock_run.assert_not_called()


def test_run_spice_with_manifest_proceeds_when_all_models_present(fs):
    """run_spice() launches ngspice normally when manifest is provided and all models exist."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    fs.create_file(f"{_FEATURE_DIR}/models/ldo.spice", contents="* ldo model\n")
    manifest = _FakeManifest(
        name="my-feature",
        models={"libraries": ["models/ldo.spice"], "required_parameters": []},
    )

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(returncode=0),
    ):
        result = run_spice(_NETLIST_PATH, _OUTPUT_DIR, manifest=manifest, feature_dir=_FEATURE_DIR)

    assert_that(result, instance_of(SpiceResult))


def test_run_spice_without_manifest_skips_model_validation(fs):
    """run_spice() does not perform model validation when no manifest is provided."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(returncode=0),
    ):
        result = run_spice(_NETLIST_PATH, _OUTPUT_DIR)

    assert_that(result, instance_of(SpiceResult))


def test_run_spice_missing_model_error_includes_feature_name(fs):
    """MissingModelError from run_spice pre-flight includes the feature name."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": ["models/missing.spice"], "required_parameters": []},
    )

    with pytest.raises(MissingModelError) as exc_info:
        run_spice(_NETLIST_PATH, _OUTPUT_DIR, manifest=manifest, feature_dir=_FEATURE_DIR)

    assert_that(str(exc_info.value), contains_string("voltage-regulator"))


def test_run_spice_raises_value_error_when_manifest_provided_without_feature_dir(fs):
    """run_spice() raises ValueError when manifest is given but feature_dir is omitted."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    manifest = _FakeManifest(
        name="my-feature",
        models={"libraries": ["models/ldo.spice"], "required_parameters": []},
    )

    with pytest.raises(ValueError, match="feature_dir"):
        run_spice(_NETLIST_PATH, _OUTPUT_DIR, manifest=manifest)


# ---------------------------------------------------------------------------
# Pre-flight required-parameter check via provided_params
# ---------------------------------------------------------------------------


def test_run_spice_raises_missing_parameter_error_when_required_param_absent(fs):
    """run_spice() raises MissingParameterError when a required parameter is not provided."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN"]},
    )

    with pytest.raises(MissingParameterError):
        run_spice(
            _NETLIST_PATH,
            _OUTPUT_DIR,
            manifest=manifest,
            feature_dir=_FEATURE_DIR,
            provided_params={},
        )


def test_run_spice_raises_missing_parameter_error_before_subprocess(fs):
    """run_spice() raises MissingParameterError without calling subprocess when params missing."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN"]},
    )

    with patch("ci_feature.spice_runner.subprocess.run") as mock_run:
        with pytest.raises(MissingParameterError):
            run_spice(
                _NETLIST_PATH,
                _OUTPUT_DIR,
                manifest=manifest,
                feature_dir=_FEATURE_DIR,
                provided_params={},
            )

    mock_run.assert_not_called()


def test_run_spice_missing_parameter_error_includes_feature_name(fs):
    """MissingParameterError from run_spice pre-flight includes the feature name."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN"]},
    )

    with pytest.raises(MissingParameterError) as exc_info:
        run_spice(
            _NETLIST_PATH,
            _OUTPUT_DIR,
            manifest=manifest,
            feature_dir=_FEATURE_DIR,
            provided_params={},
        )

    assert_that(str(exc_info.value), contains_string("voltage-regulator"))


def test_run_spice_missing_parameter_error_includes_missing_param_name(fs):
    """MissingParameterError from run_spice pre-flight includes the missing parameter name."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN"]},
    )

    with pytest.raises(MissingParameterError) as exc_info:
        run_spice(
            _NETLIST_PATH,
            _OUTPUT_DIR,
            manifest=manifest,
            feature_dir=_FEATURE_DIR,
            provided_params={},
        )

    assert_that(str(exc_info.value), contains_string("V_IN"))


def test_run_spice_proceeds_when_all_required_params_provided(fs):
    """run_spice() launches ngspice normally when all required parameters are provided."""
    fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN"]},
    )

    with patch(
        "ci_feature.spice_runner.subprocess.run",
        return_value=_make_completed_process(returncode=0),
    ):
        result = run_spice(
            _NETLIST_PATH,
            _OUTPUT_DIR,
            manifest=manifest,
            feature_dir=_FEATURE_DIR,
            provided_params={"V_IN": 5.0},
        )

    assert_that(result, instance_of(SpiceResult))


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


# ---------------------------------------------------------------------------
# parse_measure_results
# ---------------------------------------------------------------------------


class TestParseMeasureResults:
    """Tests for parse_measure_results()."""

    def test_returns_empty_dict_for_empty_string(self):
        """parse_measure_results() returns {} for empty log content."""
        assert_that(parse_measure_results(""), equal_to({}))

    def test_parses_single_measure_result(self):
        """parse_measure_results() extracts a single .meas result line."""
        log = "v_out               =  3.300000e+00\n"
        result = parse_measure_results(log)
        assert_that(result, has_entry("V_OUT", equal_to(3.3)))

    def test_result_key_is_uppercased(self):
        """parse_measure_results() upper-cases the measurement name."""
        log = "v_out = 3.3\n"
        result = parse_measure_results(log)
        assert "V_OUT" in result
        assert "v_out" not in result

    def test_parses_multiple_measure_results(self):
        """parse_measure_results() extracts all .meas result lines."""
        log = "v_out = 3.3\nv_in = 5.0\n"
        result = parse_measure_results(log)
        assert_that(result, has_entry("V_OUT", equal_to(3.3)))
        assert_that(result, has_entry("V_IN", equal_to(5.0)))

    def test_parses_scientific_notation(self):
        """parse_measure_results() handles scientific notation (e.g. 2.500000e+00)."""
        log = "v_mid               =  2.500000e+00\n"
        result = parse_measure_results(log)
        assert_that(result, has_entry("V_MID", equal_to(2.5)))

    def test_parses_negative_value(self):
        """parse_measure_results() handles negative values."""
        log = "v_neg = -1.2e-03\n"
        result = parse_measure_results(log)
        assert_that(result, has_entry("V_NEG", equal_to(-1.2e-3)))

    def test_ignores_table_header_lines(self):
        """parse_measure_results() ignores .print table header lines."""
        log = "Index   v-sweep         v(mid)\n0           5.000000e+00    2.500000e+00\n"
        result = parse_measure_results(log)
        # Table header/data rows have no '=' so nothing should be parsed
        assert_that(result, equal_to({}))

    def test_ignores_non_matching_lines(self):
        """parse_measure_results() silently skips lines that do not match name=value."""
        log = "No. of Data Rows : 1\nDoing analysis at TEMP = 27\n"
        result = parse_measure_results(log)
        # Neither line starts with a bare identifier followed by '=', so nothing is parsed
        assert_that(result, equal_to({}))

    def test_mixed_log_with_measure_and_print(self):
        """parse_measure_results() extracts only the .meas line in a mixed log."""
        log = (
            "Index   v-sweep         v(mid)\n"
            "0           5.000000e+00    2.500000e+00\n"
            "v_out               =  3.300000e+00\n"
            "No. of Data Rows : 1\n"
        )
        result = parse_measure_results(log)
        assert_that(result, has_entry("V_OUT", equal_to(3.3)))


class TestRunSpicePopulatesSignals:
    """run_spice() populates SpiceResult.signals from the log file when available."""

    def test_signals_is_empty_dict_when_log_file_absent(self, fs):
        """SpiceResult.signals is empty when the log file does not exist."""
        fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")

        with patch(
            "ci_feature.spice_runner.subprocess.run",
            return_value=_make_completed_process(returncode=0),
        ):
            result = run_spice(_NETLIST_PATH, _OUTPUT_DIR)

        assert_that(result.signals, equal_to({}))

    def test_signals_populated_from_log_file(self, fs):
        """SpiceResult.signals is populated when the log file contains .meas results."""
        fs.create_file(_NETLIST_PATH, contents="* netlist\n.end\n")
        log_content = "v_out               =  3.300000e+00\n"

        def fake_run(cmd, **kwargs):
            # Write the log file as ngspice would
            fs.create_file(_LOG_PATH, contents=log_content)
            return _make_completed_process(returncode=0)

        with patch("ci_feature.spice_runner.subprocess.run", side_effect=fake_run):
            result = run_spice(_NETLIST_PATH, _OUTPUT_DIR)

        assert_that(result.signals, has_entry("V_OUT", equal_to(3.3)))
