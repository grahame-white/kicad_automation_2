"""Unit tests for the 'When the simulation is run' step in features/steps/feature_steps.py."""

import os
from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, contains_string, equal_to, is_

from ci_feature.kicad_export import NetlistExportError
from ci_feature.manifest import FeatureManifest
from ci_feature.spice_errors import (
    ConvergenceError,
    MissingModelError,
    MissingParameterError,
    SpiceRunError,
)
from ci_feature.spice_runner import SpiceResult
from features.steps.feature_steps import step_simulation_is_run


def _make_manifest(name, configuration=None):
    """Create a minimal FeatureManifest with the given name for testing."""
    return FeatureManifest(
        name=name,
        version="1.0.0",
        schematic=f"schematic/{name}.kicad_sch",
        interface=["interface.yml"],
        models={"libraries": [], "required_parameters": []},
        configuration=configuration,
        directory=f"/repo/schematics/{name}",
    )


def _make_spice_result():
    """Create a minimal SpiceResult for testing."""
    return SpiceResult(
        returncode=0,
        stdout="ngspice output",
        stderr="",
        log_path="/repo/reports/simulation/voltage-regulator/ngspice.log",
    )


def _make_context(feature_root="/repo", manifest=None, feature_dir=None):
    """Create a mock Behave context with standard attributes."""
    context = MagicMock()
    context.feature_root = feature_root
    context.feature_manifest = manifest
    context.feature_dir = feature_dir
    context.simulation_result = None
    return context


class TestSimulationStepSuccess:
    """Tests for successful simulation runs."""

    def test_step_stores_simulation_result_on_context(self):
        """step_simulation_is_run stores the SpiceResult on context.simulation_result."""
        manifest = _make_manifest("voltage-regulator")
        context = _make_context(manifest=manifest, feature_dir="/repo/schematics/voltage-regulator")
        spice_result = _make_spice_result()

        with (
            patch(
                "features.steps.feature_steps.export_netlist",
                return_value="/repo/reports/simulation/voltage-regulator/voltage-regulator.net",
            ),
            patch("features.steps.feature_steps.run_spice", return_value=spice_result),
        ):
            step_simulation_is_run(context)

        assert_that(context.simulation_result, equal_to(spice_result))

    def test_step_calls_export_netlist_with_manifest_and_output_dir(self):
        """step_simulation_is_run calls export_netlist with the manifest and output_dir."""
        manifest = _make_manifest("voltage-regulator")
        context = _make_context(manifest=manifest, feature_dir="/repo/schematics/voltage-regulator")
        expected_output_dir = os.path.join("/repo", "reports", "simulation")

        with (
            patch(
                "features.steps.feature_steps.export_netlist",
                return_value="/some/netlist.net",
            ) as mock_export,
            patch("features.steps.feature_steps.run_spice", return_value=_make_spice_result()),
        ):
            step_simulation_is_run(context)

        mock_export.assert_called_once_with(
            manifest, expected_output_dir, "/repo/schematics/voltage-regulator"
        )

    def test_step_calls_run_spice_with_netlist_path_from_export(self):
        """step_simulation_is_run passes the netlist path from export_netlist to run_spice."""
        manifest = _make_manifest("voltage-regulator")
        context = _make_context(manifest=manifest, feature_dir="/repo/schematics/voltage-regulator")
        netlist_path = "/repo/reports/simulation/voltage-regulator/voltage-regulator.net"

        with (
            patch("features.steps.feature_steps.export_netlist", return_value=netlist_path),
            patch(
                "features.steps.feature_steps.run_spice", return_value=_make_spice_result()
            ) as mock_run_spice,
        ):
            step_simulation_is_run(context)

        call_kwargs = mock_run_spice.call_args
        assert_that(call_kwargs.kwargs["netlist_path"], equal_to(netlist_path))

    def test_step_calls_run_spice_with_manifest(self):
        """step_simulation_is_run passes the manifest to run_spice."""
        manifest = _make_manifest("voltage-regulator")
        context = _make_context(manifest=manifest, feature_dir="/repo/schematics/voltage-regulator")

        with (
            patch("features.steps.feature_steps.export_netlist", return_value="/some/netlist.net"),
            patch(
                "features.steps.feature_steps.run_spice", return_value=_make_spice_result()
            ) as mock_run_spice,
        ):
            step_simulation_is_run(context)

        call_kwargs = mock_run_spice.call_args
        assert_that(call_kwargs.kwargs["manifest"], equal_to(manifest))

    def test_step_calls_run_spice_with_feature_dir(self):
        """step_simulation_is_run passes feature_dir to run_spice."""
        manifest = _make_manifest("voltage-regulator")
        feature_dir = "/repo/schematics/voltage-regulator"
        context = _make_context(manifest=manifest, feature_dir=feature_dir)

        with (
            patch("features.steps.feature_steps.export_netlist", return_value="/some/netlist.net"),
            patch(
                "features.steps.feature_steps.run_spice", return_value=_make_spice_result()
            ) as mock_run_spice,
        ):
            step_simulation_is_run(context)

        call_kwargs = mock_run_spice.call_args
        assert_that(call_kwargs.kwargs["feature_dir"], equal_to(feature_dir))

    def test_step_passes_manifest_configuration_as_provided_params(self):
        """step_simulation_is_run passes manifest.configuration as provided_params to run_spice."""
        config = {"V_IN": 5.0, "V_OUT": 3.3}
        manifest = _make_manifest("voltage-regulator", configuration=config)
        context = _make_context(manifest=manifest, feature_dir="/repo/schematics/voltage-regulator")

        with (
            patch("features.steps.feature_steps.export_netlist", return_value="/some/netlist.net"),
            patch(
                "features.steps.feature_steps.run_spice", return_value=_make_spice_result()
            ) as mock_run_spice,
        ):
            step_simulation_is_run(context)

        call_kwargs = mock_run_spice.call_args
        assert_that(call_kwargs.kwargs["provided_params"], equal_to(config))

    def test_step_passes_none_when_no_configuration(self):
        """step_simulation_is_run passes None as provided_params when configuration is None."""
        manifest = _make_manifest("voltage-regulator", configuration=None)
        context = _make_context(manifest=manifest, feature_dir="/repo/schematics/voltage-regulator")

        with (
            patch("features.steps.feature_steps.export_netlist", return_value="/some/netlist.net"),
            patch(
                "features.steps.feature_steps.run_spice", return_value=_make_spice_result()
            ) as mock_run_spice,
        ):
            step_simulation_is_run(context)

        call_kwargs = mock_run_spice.call_args
        assert_that(call_kwargs.kwargs["provided_params"], is_(None))

    def test_step_uses_dot_as_feature_dir_when_context_feature_dir_is_none(self):
        """step_simulation_is_run uses '.' as feature_dir when context.feature_dir is None."""
        manifest = _make_manifest("voltage-regulator")
        context = _make_context(manifest=manifest, feature_dir=None)

        with (
            patch("features.steps.feature_steps.export_netlist", return_value="/some/netlist.net"),
            patch(
                "features.steps.feature_steps.run_spice", return_value=_make_spice_result()
            ) as mock_run_spice,
        ):
            step_simulation_is_run(context)

        call_kwargs = mock_run_spice.call_args
        assert_that(call_kwargs.kwargs["feature_dir"], equal_to("."))

    def test_step_output_dir_is_under_feature_root_reports(self):
        """step_simulation_is_run places simulation output under feature_root/reports/simulation."""
        manifest = _make_manifest("voltage-regulator")
        context = _make_context(
            feature_root="/repo",
            manifest=manifest,
            feature_dir="/repo/schematics/voltage-regulator",
        )

        with (
            patch(
                "features.steps.feature_steps.export_netlist", return_value="/some/netlist.net"
            ) as mock_export,
            patch("features.steps.feature_steps.run_spice", return_value=_make_spice_result()),
        ):
            step_simulation_is_run(context)

        export_output_dir = mock_export.call_args[0][1]
        assert_that(export_output_dir, equal_to(os.path.join("/repo", "reports", "simulation")))


class TestSimulationStepNoManifest:
    """Tests for the case where no manifest is loaded."""

    def test_step_raises_assertion_error_when_no_manifest(self):
        """step_simulation_is_run raises AssertionError when context.feature_manifest is None."""
        context = _make_context(manifest=None)

        with pytest.raises(AssertionError):
            step_simulation_is_run(context)

    def test_step_error_message_mentions_given_step(self):
        """step_simulation_is_run error message guides the user to use the Given step first."""
        context = _make_context(manifest=None)

        with pytest.raises(AssertionError) as exc_info:
            step_simulation_is_run(context)

        assert_that(str(exc_info.value), contains_string("Given the feature"))


class TestSimulationStepExportFailure:
    """Tests for failures during netlist export."""

    def test_step_propagates_netlist_export_error(self):
        """step_simulation_is_run propagates NetlistExportError from export_netlist."""
        manifest = _make_manifest("voltage-regulator")
        context = _make_context(manifest=manifest, feature_dir="/repo/schematics/voltage-regulator")

        with patch(
            "features.steps.feature_steps.export_netlist",
            side_effect=NetlistExportError("kicad-cli failed"),
        ):
            with pytest.raises(NetlistExportError) as exc_info:
                step_simulation_is_run(context)

        assert_that(str(exc_info.value), contains_string("kicad-cli failed"))

    def test_step_does_not_call_run_spice_when_export_fails(self):
        """step_simulation_is_run does not call run_spice when export_netlist raises."""
        manifest = _make_manifest("voltage-regulator")
        context = _make_context(manifest=manifest, feature_dir="/repo/schematics/voltage-regulator")

        with (
            patch(
                "features.steps.feature_steps.export_netlist",
                side_effect=NetlistExportError("kicad-cli failed"),
            ),
            patch("features.steps.feature_steps.run_spice") as mock_run_spice,
        ):
            with pytest.raises(NetlistExportError):
                step_simulation_is_run(context)

        mock_run_spice.assert_not_called()


class TestSimulationStepSpiceFailures:
    """Tests for failures during ngspice simulation."""

    def test_step_propagates_missing_model_error(self):
        """step_simulation_is_run propagates MissingModelError from run_spice."""
        manifest = _make_manifest("voltage-regulator")
        context = _make_context(manifest=manifest, feature_dir="/repo/schematics/voltage-regulator")

        with (
            patch("features.steps.feature_steps.export_netlist", return_value="/some/netlist.net"),
            patch(
                "features.steps.feature_steps.run_spice",
                side_effect=MissingModelError("model file not found"),
            ),
        ):
            with pytest.raises(MissingModelError) as exc_info:
                step_simulation_is_run(context)

        assert_that(str(exc_info.value), contains_string("model file not found"))

    def test_step_propagates_missing_parameter_error(self):
        """step_simulation_is_run propagates MissingParameterError from run_spice."""
        manifest = _make_manifest("voltage-regulator")
        context = _make_context(manifest=manifest, feature_dir="/repo/schematics/voltage-regulator")

        with (
            patch("features.steps.feature_steps.export_netlist", return_value="/some/netlist.net"),
            patch(
                "features.steps.feature_steps.run_spice",
                side_effect=MissingParameterError("missing V_IN"),
            ),
        ):
            with pytest.raises(MissingParameterError) as exc_info:
                step_simulation_is_run(context)

        assert_that(str(exc_info.value), contains_string("missing V_IN"))

    def test_step_propagates_convergence_error(self):
        """step_simulation_is_run propagates ConvergenceError from run_spice."""
        manifest = _make_manifest("voltage-regulator")
        context = _make_context(manifest=manifest, feature_dir="/repo/schematics/voltage-regulator")

        with (
            patch("features.steps.feature_steps.export_netlist", return_value="/some/netlist.net"),
            patch(
                "features.steps.feature_steps.run_spice",
                side_effect=ConvergenceError("no convergence"),
            ),
        ):
            with pytest.raises(ConvergenceError) as exc_info:
                step_simulation_is_run(context)

        assert_that(str(exc_info.value), contains_string("no convergence"))

    def test_step_propagates_spice_run_error(self):
        """step_simulation_is_run propagates SpiceRunError from run_spice."""
        manifest = _make_manifest("voltage-regulator")
        context = _make_context(manifest=manifest, feature_dir="/repo/schematics/voltage-regulator")

        with (
            patch("features.steps.feature_steps.export_netlist", return_value="/some/netlist.net"),
            patch(
                "features.steps.feature_steps.run_spice",
                side_effect=SpiceRunError("ngspice failed"),
            ),
        ):
            with pytest.raises(SpiceRunError) as exc_info:
                step_simulation_is_run(context)

        assert_that(str(exc_info.value), contains_string("ngspice failed"))

    def test_simulation_result_is_not_set_when_run_spice_fails(self):
        """context.simulation_result remains None when run_spice raises an exception."""
        manifest = _make_manifest("voltage-regulator")
        context = _make_context(manifest=manifest, feature_dir="/repo/schematics/voltage-regulator")

        with (
            patch("features.steps.feature_steps.export_netlist", return_value="/some/netlist.net"),
            patch(
                "features.steps.feature_steps.run_spice",
                side_effect=SpiceRunError("ngspice failed"),
            ),
        ):
            with pytest.raises(SpiceRunError):
                step_simulation_is_run(context)

        assert_that(context.simulation_result, is_(None))
