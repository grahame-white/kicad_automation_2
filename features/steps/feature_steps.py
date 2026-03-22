"""Behave step definitions for feature selection and simulation."""

import os

from behave import given, when

from ci_feature.discovery import discover_features
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
