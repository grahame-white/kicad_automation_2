"""Unit tests for the 'Then ... is within ... of ...' step in features/steps/feature_steps.py."""

from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, contains_string

from ci_feature.interface import InterfaceContract, InterfaceValidationError
from ci_feature.manifest import FeatureManifest
from ci_feature.spice_runner import SpiceResult
from features.steps.feature_steps import step_signal_is_within_tolerance

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manifest(name="voltage-regulator"):
    return FeatureManifest(
        name=name,
        version="1.0.0",
        schematic=f"schematic/{name}.kicad_sch",
        interface=["interface.yml"],
        models={"libraries": [], "required_parameters": []},
        directory=f"/repo/schematics/{name}",
    )


def _make_interface_contract(signal_names=None):
    if signal_names is None:
        signal_names = ["V_OUT"]
    signals = [
        {
            "name": n,
            "direction": "output",
            "domain": "analog",
            "unit": "V",
            "description": f"{n} signal",
        }
        for n in signal_names
    ]
    return InterfaceContract(name="dc-power-supply", version="1.0.0", signals=signals)


def _make_spice_result(signal_values=None):
    if signal_values is None:
        signal_values = {"V_OUT": 3.3}
    return SpiceResult(
        returncode=0,
        stdout="",
        stderr="",
        log_path="/repo/reports/simulation/ngspice.log",
        signals=signal_values,
    )


def _make_context(manifest=None, simulation_result=None, feature_dir=None):
    context = MagicMock()
    context.feature_manifest = manifest
    context.feature_dir = (
        feature_dir if feature_dir is not None else (manifest.directory if manifest else None)
    )
    context.simulation_result = simulation_result
    return context


# ---------------------------------------------------------------------------
# Signal within tolerance — step passes
# ---------------------------------------------------------------------------


class TestSignalWithinTolerancePasses:
    """step_signal_is_within_tolerance does not raise when measured value is within bounds."""

    def test_signal_exactly_at_expected_passes(self):
        """Measured value equal to expected passes."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result({"V_OUT": 3.3}),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

    def test_signal_at_upper_bound_passes(self):
        """Measured value equal to expected + tolerance passes."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result({"V_OUT": 3.4}),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

    def test_signal_at_lower_bound_passes(self):
        """Measured value equal to expected - tolerance passes."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result({"V_OUT": 3.2}),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

    def test_signal_strictly_inside_tolerance_passes(self):
        """Measured value between bounds passes."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result({"V_OUT": 3.25}),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")


# ---------------------------------------------------------------------------
# Signal outside tolerance — step fails with detailed message
# ---------------------------------------------------------------------------


class TestSignalOutsideToleranceFails:
    """step_signal_is_within_tolerance raises AssertionError with a rich message."""

    def test_signal_above_tolerance_raises_assertion_error(self):
        """Measured value above expected + tolerance raises AssertionError."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result({"V_OUT": 3.5}),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            with pytest.raises(AssertionError):
                step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

    def test_signal_below_tolerance_raises_assertion_error(self):
        """Measured value below expected - tolerance raises AssertionError."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result({"V_OUT": 3.0}),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            with pytest.raises(AssertionError):
                step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

    def test_failure_message_includes_signal_name(self):
        """AssertionError message includes the signal name."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result({"V_OUT": 3.5}),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            with pytest.raises(AssertionError) as exc_info:
                step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

        assert_that(str(exc_info.value), contains_string("V_OUT"))

    def test_failure_message_includes_measured_value(self):
        """AssertionError message includes the measured value."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result({"V_OUT": 3.5}),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            with pytest.raises(AssertionError) as exc_info:
                step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

        assert_that(str(exc_info.value), contains_string("3.5"))

    def test_failure_message_includes_expected_value(self):
        """AssertionError message includes the expected value."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result({"V_OUT": 3.5}),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            with pytest.raises(AssertionError) as exc_info:
                step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

        assert_that(str(exc_info.value), contains_string("3.3"))

    def test_failure_message_includes_tolerance(self):
        """AssertionError message includes the tolerance value."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result({"V_OUT": 3.5}),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            with pytest.raises(AssertionError) as exc_info:
                step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

        assert_that(str(exc_info.value), contains_string("0.1"))


# ---------------------------------------------------------------------------
# Signal not in interface — immediate InterfaceValidationError
# ---------------------------------------------------------------------------


class TestSignalNotInInterface:
    """step_signal_is_within_tolerance raises InterfaceValidationError for undeclared signals."""

    def test_undeclared_signal_raises_interface_validation_error(self):
        """Signal not in any interface contract raises InterfaceValidationError."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result(),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(signal_names=["V_OUT", "GND"]),
        ):
            with pytest.raises(InterfaceValidationError):
                step_signal_is_within_tolerance(context, "NET001", "0.1 V", "3.3 V")

    def test_error_message_includes_invalid_signal_name(self):
        """InterfaceValidationError message includes the invalid signal name."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result(),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(signal_names=["V_OUT", "GND"]),
        ):
            with pytest.raises(InterfaceValidationError) as exc_info:
                step_signal_is_within_tolerance(context, "NET001", "0.1 V", "3.3 V")

        assert_that(str(exc_info.value), contains_string("NET001"))

    def test_interface_error_raised_before_checking_simulation_result(self):
        """InterfaceValidationError is raised even when simulation_result is None."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=None,
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(signal_names=["V_OUT"]),
        ):
            with pytest.raises(InterfaceValidationError):
                step_signal_is_within_tolerance(context, "NET001", "0.1 V", "3.3 V")


# ---------------------------------------------------------------------------
# No simulation result
# ---------------------------------------------------------------------------


class TestNoSimulationResult:
    """step_signal_is_within_tolerance raises AssertionError when simulation_result is None."""

    def test_raises_assertion_error_when_no_simulation_result(self):
        """AssertionError is raised when context.simulation_result is None."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=None,
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            with pytest.raises(AssertionError):
                step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

    def test_error_message_suggests_running_simulation(self):
        """AssertionError message guides the user to run the simulation step."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=None,
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            with pytest.raises(AssertionError) as exc_info:
                step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

        assert_that(str(exc_info.value), contains_string("simulation"))


# ---------------------------------------------------------------------------
# Signal not in simulation result signals dict
# ---------------------------------------------------------------------------


class TestSignalNotMeasured:
    """step_signal_is_within_tolerance raises AssertionError when signal not in signals dict."""

    def test_raises_assertion_error_when_signal_not_in_signals(self):
        """AssertionError is raised when the declared signal was not measured."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result({}),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            with pytest.raises(AssertionError):
                step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

    def test_error_message_includes_signal_name(self):
        """AssertionError message includes the missing signal name."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result({}),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            with pytest.raises(AssertionError) as exc_info:
                step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

        assert_that(str(exc_info.value), contains_string("V_OUT"))

    def test_error_message_hints_at_meas_directive(self):
        """AssertionError message mentions .meas directive."""
        context = _make_context(
            manifest=_make_manifest(),
            simulation_result=_make_spice_result({}),
        )
        with patch(
            "features.steps.feature_steps.load_interface",
            return_value=_make_interface_contract(),
        ):
            with pytest.raises(AssertionError) as exc_info:
                step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

        assert_that(str(exc_info.value), contains_string(".meas"))


# ---------------------------------------------------------------------------
# No manifest loaded
# ---------------------------------------------------------------------------


class TestNoManifest:
    """step_signal_is_within_tolerance raises AssertionError when manifest is None."""

    def test_raises_assertion_error_when_no_manifest(self):
        """AssertionError is raised when context.feature_manifest is None."""
        context = _make_context(manifest=None, simulation_result=_make_spice_result())
        with pytest.raises(AssertionError):
            step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

    def test_error_message_mentions_given_step(self):
        """AssertionError message guides user to call the Given step first."""
        context = _make_context(manifest=None, simulation_result=_make_spice_result())
        with pytest.raises(AssertionError) as exc_info:
            step_signal_is_within_tolerance(context, "V_OUT", "0.1 V", "3.3 V")

        assert_that(str(exc_info.value), contains_string("Given the feature"))
