"""Behave step definitions for feature selection and simulation."""

import os

from behave import given, then, when

from ci_feature.discovery import discover_features
from ci_feature.interface import InterfaceValidationError, load_interface, validate_signal_name
from ci_feature.kicad_export import export_netlist
from ci_feature.spice_runner import run_spice


@given('the feature "{name}"')
def step_the_feature(context, name):
    """Select a feature by name using the manifest discovery system.

    Calls ``discover_features(context.feature_root)`` to locate all feature
    manifests, then finds the one whose ``name`` field matches *name* and
    stores it on ``context.feature_manifest`` and ``context.feature_dir`` for
    use in subsequent steps.

    Raises:
        AssertionError: When *name* is not found, with a message listing all
            discovered feature names.
    """
    features = discover_features(context.feature_root)
    for feature in features:
        if feature.name == name:
            context.feature_manifest = feature
            context.feature_dir = feature.directory
            return
    available = [f.name for f in features]
    if not available:
        raise AssertionError(
            f"Feature '{name}' not found. No features were discovered in the repository."
        )
    raise AssertionError(f"Feature '{name}' not found. Available features: {', '.join(available)}")


@when("the simulation is run")
def step_simulation_is_run(context):
    """Export the feature netlist and run ngspice simulation.

    Retrieves ``context.feature_manifest`` and ``context.feature_dir`` (set by
    the ``Given the feature`` step), exports the KiCad netlist via
    :func:`~ci_feature.kicad_export.export_netlist`, then invokes ngspice via
    :func:`~ci_feature.spice_runner.run_spice`.  The :class:`SpiceResult` is
    stored on ``context.simulation_result`` for use in subsequent ``Then``
    assertion steps.

    Model presence and required parameter checks are performed by
    :func:`~ci_feature.spice_runner.run_spice` before ngspice is launched.
    Any failure is surfaced as the specific exception type raised by the
    underlying module so that the step failure message is immediately
    actionable.

    Raises:
        AssertionError: When no feature manifest is loaded (i.e. the
            ``Given the feature`` step was not called).
        NetlistExportError: When ``kicad-cli`` cannot be launched, returns a
            non-zero exit code, or produces an empty/missing output file.
        MissingModelError: When one or more SPICE model library files declared
            in the manifest are absent from the filesystem.
        MissingParameterError: When one or more required SPICE parameters
            declared in the manifest are absent from the feature configuration.
        SpiceRunError: When ngspice cannot be launched, times out, or exits
            with a non-zero status not matched by a more specific error class.
        SpiceSyntaxError: When ngspice reports a syntax or parse error in the
            netlist or included SPICE sources.
        ConvergenceError: When ngspice reports a convergence failure.
    """
    manifest = context.feature_manifest
    if manifest is None:
        raise AssertionError(
            "No feature manifest loaded. Use 'Given the feature \"<name>\"' first."
        )

    feature_dir = getattr(context, "feature_dir", None) or getattr(manifest, "directory", None)
    if not feature_dir:
        raise AssertionError(
            "Feature directory is not available. Ensure the manifest discovery step "
            "has set either context.feature_dir or manifest.directory."
        )

    output_dir = os.path.join(context.feature_root, "reports", "simulation")

    netlist_path = export_netlist(manifest, output_dir, feature_dir)

    context.simulation_result = run_spice(
        netlist_path=netlist_path,
        output_dir=os.path.dirname(netlist_path),
        manifest=manifest,
        feature_dir=feature_dir,
        provided_params=manifest.configuration,
    )


def _parse_value_with_unit(value_str: str) -> tuple:
    """Parse a value string of the form ``"<number> <unit>"`` into ``(float, str)``.

    Args:
        value_str: A string such as ``"3.3 V"`` or ``"0.1 V"``.

    Returns:
        A two-tuple of ``(numeric_value, unit_string)``.

    Raises:
        AssertionError: When *value_str* does not contain exactly two
            whitespace-separated tokens, or the first token is not a valid
            float.
    """
    parts = value_str.strip().split(None, 1)
    if len(parts) != 2:
        raise AssertionError(
            f"Cannot parse '{value_str}': expected '<number> <unit>' (e.g. '3.3 V')."
        )
    try:
        return float(parts[0]), parts[1].strip()
    except ValueError:
        raise AssertionError(f"Cannot parse numeric value from '{parts[0]}' in '{value_str}'.")


@then('"{signal}" is within "{tolerance}" of "{expected}"')
def step_signal_is_within_tolerance(context, signal, tolerance, expected):
    """Assert that a named interface signal value is within a specified tolerance.

    Validates that *signal* is declared in the feature's interface contract
    (using :func:`~ci_feature.interface.validate_signal_name`), then asserts
    that the simulated value stored in ``context.simulation_result.signals``
    is within *tolerance* of *expected*.

    Both *tolerance* and *expected* must be strings of the form
    ``"<number> <unit>"`` (e.g. ``"0.1 V"``).  The numeric parts are compared;
    units are included in failure messages for readability.

    Raises:
        InterfaceValidationError: If *signal* is not declared in any of the
            feature's interface contracts.  The error message includes the
            invalid name, the interface name, and the valid signal names.
        AssertionError: If no feature manifest is loaded, if the feature
            directory is unavailable, if no simulation result is available,
            if *signal* is not present in ``simulation_result.signals``,
            or if the measured value lies outside the tolerance band.
            Failure messages include the signal name, measured value,
            expected value, and tolerance.
    """
    manifest = context.feature_manifest
    if manifest is None:
        raise AssertionError(
            "No feature manifest loaded. Use 'Given the feature \"<name>\"' first."
        )

    feature_dir = getattr(context, "feature_dir", None) or getattr(manifest, "directory", None)
    if not feature_dir:
        raise AssertionError(
            "Feature directory is not available. Ensure the manifest discovery step "
            "has set either context.feature_dir or manifest.directory."
        )

    # Validate the signal against every interface contract in the manifest
    # (M3-03 logic).  Raise InterfaceValidationError if not found in any.
    last_error: InterfaceValidationError | None = None
    for iface_path in manifest.interface:
        abs_path = os.path.join(feature_dir, iface_path)
        contract = load_interface(abs_path)
        try:
            validate_signal_name(signal, contract)
            last_error = None
            break
        except InterfaceValidationError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error

    # Check that a simulation result is available.
    simulation_result = context.simulation_result
    if simulation_result is None:
        raise AssertionError(
            "No simulation result available. "
            "Run the simulation first using 'When the simulation is run'."
        )

    # Look up the measured value from the parsed .meas results.
    if signal not in simulation_result.signals:
        available = ", ".join(simulation_result.signals) or "none"
        raise AssertionError(
            f"Signal '{signal}' was not measured in the simulation. "
            f"Available measurements: {available}. "
            f"Add a '.meas' directive to the netlist that assigns the name '{signal}'."
        )

    measured = simulation_result.signals[signal]

    # Parse tolerance and expected values.
    tol_value, tol_unit = _parse_value_with_unit(tolerance)
    exp_value, exp_unit = _parse_value_with_unit(expected)

    lower = exp_value - tol_value
    upper = exp_value + tol_value

    if not (lower <= measured <= upper):
        raise AssertionError(
            f"Signal '{signal}': measured {measured} {exp_unit}, "
            f"expected {exp_value} \u00b1 {tol_value} {exp_unit}"
        )
