"""ngspice runner for SPICE netlist simulation."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional

from ci_feature.model_validation import validate_model_presence
from ci_feature.spice_errors import (
    ConvergenceError,
    MissingModelError,
    MissingParameterError,
    SpiceRunError,
    SpiceSyntaxError,
)

if TYPE_CHECKING:
    from ci_feature.manifest import FeatureManifest

__all__ = [
    "ConvergenceError",
    "MissingModelError",
    "MissingParameterError",
    "SpiceRunError",
    "SpiceSyntaxError",
    "SpiceResult",
    "parse_measure_results",
    "run_spice",
    "validate_model_presence",
    "validate_required_parameters",
]

# Matches ngspice .meas result lines of the form:
#   <name>   =   <float>
# Names are case-insensitive in SPICE; this pattern captures them for
# upper-casing by the caller.  The float allows optional sign, integer part,
# decimal part, and exponent (e.g. 2.500000e+00, -1.2e-3, .5, 5).
_MEAS_RESULT_RE = re.compile(
    r"^\s*(\w+)\s*=\s*([-+]?\d*(?:\.\d+)?(?:[eE][-+]?\d+)?)",
    re.MULTILINE,
)


def parse_measure_results(log_content: str) -> Dict[str, float]:
    """Parse ngspice ``.meas`` result lines from simulation log output.

    Scans *log_content* for lines produced by ngspice ```.meas``` directives,
    which have the form::

        <name>   =   <value>

    and returns a mapping of **upper-cased** name to float value.  Names are
    upper-cased so that they match interface signal names without requiring the
    SPICE netlist to use a specific case (SPICE is case-insensitive).

    Lines that do not match the pattern, or whose value cannot be converted to
    a float, are silently skipped.

    Args:
        log_content: The full text content of the ngspice log file (i.e. the
            file written by ``ngspice -b -o <log> <netlist>``).

    Returns:
        A ``dict`` mapping upper-cased measurement names to their float values.
        Returns an empty dict when no matching lines are found.
    """
    results: Dict[str, float] = {}
    for match in _MEAS_RESULT_RE.finditer(log_content):
        name = match.group(1).upper()
        try:
            results[name] = float(match.group(2))
        except ValueError:
            pass
    return results


@dataclass
class SpiceResult:
    """Result of a successful ngspice run.

    Attributes:
        returncode: The exit code returned by ngspice (0 on success).
        stdout: Captured standard output from ngspice.
        stderr: Captured standard error from ngspice.
        log_path: Absolute path to the ngspice log file written to *output_dir*.
        signals: Mapping of upper-cased ``.meas`` measurement names to their
            float values, parsed from the ngspice log file.  Empty when the
            log file cannot be read or contains no ``name = value`` lines.
    """

    returncode: int
    stdout: str
    stderr: str
    log_path: str
    signals: Dict[str, float] = field(default_factory=dict)


def validate_required_parameters(
    manifest: FeatureManifest, provided_params: Optional[Dict[str, Any]]
) -> None:
    """Check that all required SPICE model parameters are present in *provided_params*.

    Compares the parameter names listed in ``manifest.models["required_parameters"]``
    against the keys of *provided_params* and raises :class:`MissingParameterError` if
    any required names are absent.  This function is intended to be called as a
    pre-flight check before invoking ngspice, so that CI fails fast with a clear
    error rather than producing a misleading ngspice simulation failure.

    Extra parameters that are present in *provided_params* but not listed in
    ``manifest.models["required_parameters"]`` are silently accepted.

    Args:
        manifest: A :class:`~ci_feature.manifest.FeatureManifest` instance whose
            ``models["required_parameters"]`` list will be verified.
        provided_params: A mapping of parameter names to values supplied by the
            scenario.  ``None`` or an empty dict is treated as no parameters
            provided.

    Raises:
        MissingParameterError: If one or more required parameters are absent from
            *provided_params*.  The error message includes the feature name and the
            full list of missing parameter names.
    """
    required = list(dict.fromkeys(manifest.models.get("required_parameters", [])))
    provided = set(provided_params.keys()) if provided_params else set()
    missing = [p for p in required if p not in provided]

    if missing:
        missing_list = "\n".join(f"  {p}" for p in missing)
        raise MissingParameterError(
            f"Feature '{manifest.name}' is missing "
            f"{len(missing)} required {'parameter' if len(missing) == 1 else 'parameters'}:\n"
            f"{missing_list}"
        )


def _raise_classified_error(returncode: int, stdout: str, stderr: str, cmd: list[str]) -> None:
    """Inspect ngspice output and raise the most specific exception type.

    Examines *stdout* and *stderr* for well-known ngspice error patterns and
    raises the appropriate typed exception.  Falls back to :class:`SpiceRunError`
    when no recognised pattern is found.

    Args:
        returncode: The non-zero exit code returned by ngspice.
        stdout: Captured standard output from the failed ngspice process.
        stderr: Captured standard error from the failed ngspice process.
        cmd: The command list that was executed, used in the error message.

    Raises:
        MissingModelError: When output contains ``include not found``.
        SpiceSyntaxError: When output contains ``parse error`` or ``syntax error``.
        ConvergenceError: When output contains ``no convergence`` or
            ``timestep too small``.
        SpiceRunError: For all other non-zero exit codes.
    """
    combined = f"{stdout}\n{stderr}".lower()
    msg = (
        f"ngspice failed (exit code {returncode}).\n"
        f"Command: {shlex.join(cmd)}\n"
        f"stdout: {stdout}\n"
        f"stderr: {stderr}"
    )
    if "include not found" in combined:
        raise MissingModelError(msg)
    if "parse error" in combined or "syntax error" in combined:
        raise SpiceSyntaxError(msg)
    if "no convergence" in combined or "timestep too small" in combined:
        raise ConvergenceError(msg)
    raise SpiceRunError(msg)


def run_spice(
    netlist_path: str,
    output_dir: str,
    timeout: int = 60,
    manifest: Optional[FeatureManifest] = None,
    feature_dir: Optional[str] = None,
    provided_params: Optional[Dict[str, Any]] = None,
) -> SpiceResult:
    """Run ngspice on *netlist_path* and capture all output.

    Executes ``ngspice`` in batch mode (``-b``) on the given SPICE netlist,
    writing a log file to *output_dir* and returning a :class:`SpiceResult`
    with the captured stdout, stderr, and log path.

    When *manifest* and *feature_dir* are provided, every model library path
    listed in ``manifest.models["libraries"]`` is verified to exist before
    ngspice is launched.  If any file is absent, :class:`MissingModelError`
    is raised immediately — before the subprocess starts — so CI fails fast
    with a clear, actionable error.

    When *manifest* is provided and ``manifest.models["required_parameters"]``
    is non-empty, every listed parameter name is verified to be present in
    *provided_params*.  If any are absent, :class:`MissingParameterError` is
    raised before ngspice is invoked.

    Args:
        netlist_path: Path to the SPICE netlist file to simulate.
        output_dir: Directory where the simulation log will be written.  The
            directory is created if it does not already exist.
        timeout: Maximum number of seconds to wait for ngspice to complete.
            Defaults to 60.  Raises :class:`SpiceRunError` if the process does
            not finish within this time.
        manifest: Optional :class:`~ci_feature.manifest.FeatureManifest`
            whose ``models["libraries"]`` paths are checked for existence and
            whose ``models["required_parameters"]`` are validated against
            *provided_params* before ngspice is invoked.  Must be supplied
            together with *feature_dir*.
        feature_dir: Directory containing the ``feature.yml`` file; used to
            resolve model library paths from *manifest* to absolute paths.
            Required when *manifest* is provided.
        provided_params: Mapping of parameter names to values supplied by the
            scenario.  Validated against ``manifest.models["required_parameters"]``
            when *manifest* is provided.  ``None`` is treated as no parameters
            provided.

    Returns:
        A :class:`SpiceResult` containing the exit code, captured stdout,
        captured stderr, and the path to the written log file.

    Raises:
        ValueError: If *manifest* is provided without *feature_dir*.
        MissingModelError: If *manifest* is supplied and one or more model
            library files listed in ``manifest.models["libraries"]`` do not
            exist on the filesystem (raised before ngspice is invoked).
        MissingParameterError: If *manifest* is supplied and one or more names
            listed in ``manifest.models["required_parameters"]`` are absent from
            *provided_params* (raised before ngspice is invoked).
        SpiceRunError: If ``ngspice`` cannot be launched (e.g. not installed);
            if ``ngspice`` does not complete within *timeout* seconds; if
            *netlist_path* does not exist; or if ``ngspice`` exits with a
            non-zero status that does not match any known error pattern.
            Error messages include the command that was attempted and any
            captured stdout/stderr.
        SpiceSyntaxError: If ngspice output indicates a syntax or parse error
            in the netlist (raised instead of :class:`SpiceRunError` when a
            non-zero exit is classified as a syntax error).
        ConvergenceError: If ngspice output indicates a simulation convergence
            failure (raised instead of :class:`SpiceRunError` when a non-zero
            exit is classified as a convergence error).
    """
    if manifest is not None:
        if feature_dir is None:
            raise ValueError("feature_dir must be provided when manifest is provided")
        validate_model_presence(manifest, feature_dir)
        validate_required_parameters(manifest, provided_params)

    netlist_path = os.path.realpath(netlist_path)
    output_dir = os.path.realpath(output_dir)

    log_path = os.path.join(output_dir, "ngspice.log")

    cmd = [
        "ngspice",
        "-b",
        "-o",
        log_path,
        netlist_path,
    ]

    if not os.path.isfile(netlist_path):
        raise SpiceRunError(f"Netlist file not found: {netlist_path}\nCommand: {shlex.join(cmd)}")

    os.makedirs(output_dir, exist_ok=True)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        message = (
            f"Failed to run ngspice.\n"
            f"Command: {shlex.join(cmd)}\n"
            f"Original error: {exc.__class__.__name__}: {exc}"
        )
        if isinstance(exc, subprocess.TimeoutExpired):
            # subprocess.TimeoutExpired may contain partial output/stderr when capture_output=True.
            if getattr(exc, "output", None):
                message += f"\nPartial stdout: {exc.output}"
            if getattr(exc, "stderr", None):
                message += f"\nPartial stderr: {exc.stderr}"
        raise SpiceRunError(message) from exc

    if result.returncode != 0:
        _raise_classified_error(result.returncode, result.stdout, result.stderr, cmd)

    signals: Dict[str, float] = {}
    try:
        with open(log_path) as f:
            signals = parse_measure_results(f.read())
    except OSError:
        pass

    return SpiceResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        log_path=log_path,
        signals=signals,
    )
