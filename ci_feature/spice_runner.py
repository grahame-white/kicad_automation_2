"""ngspice runner for SPICE netlist simulation."""

import os
import shlex
import subprocess
from dataclasses import dataclass

from ci_feature.spice_errors import (
    ConvergenceError,
    MissingModelError,
    SpiceRunError,
    SpiceSyntaxError,
)

__all__ = [
    "ConvergenceError",
    "MissingModelError",
    "SpiceRunError",
    "SpiceSyntaxError",
    "SpiceResult",
    "run_spice",
]


@dataclass
class SpiceResult:
    """Result of a successful ngspice run.

    Attributes:
        returncode: The exit code returned by ngspice (0 on success).
        stdout: Captured standard output from ngspice.
        stderr: Captured standard error from ngspice.
        log_path: Absolute path to the ngspice log file written to *output_dir*.
    """

    returncode: int
    stdout: str
    stderr: str
    log_path: str


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


def run_spice(netlist_path: str, output_dir: str, timeout: int = 60) -> SpiceResult:
    """Run ngspice on *netlist_path* and capture all output.

    Executes ``ngspice`` in batch mode (``-b``) on the given SPICE netlist,
    writing a log file to *output_dir* and returning a :class:`SpiceResult`
    with the captured stdout, stderr, and log path.

    Args:
        netlist_path: Path to the SPICE netlist file to simulate.
        output_dir: Directory where the simulation log will be written.  The
            directory is created if it does not already exist.
        timeout: Maximum number of seconds to wait for ngspice to complete.
            Defaults to 60.  Raises :class:`SpiceRunError` if the process does
            not finish within this time.

    Returns:
        A :class:`SpiceResult` containing the exit code, captured stdout,
        captured stderr, and the path to the written log file.

    Raises:
        SpiceRunError: If ``ngspice`` cannot be launched (e.g. not installed);
            if ``ngspice`` does not complete within *timeout* seconds; or if
            *netlist_path* does not exist.  Error messages include the command
            that was attempted and any captured stdout/stderr.
        MissingModelError: If ngspice output indicates a missing model or
            include file (subclass of :class:`SpiceRunError`).
        SpiceSyntaxError: If ngspice output indicates a syntax or parse error
            in the netlist (subclass of :class:`SpiceRunError`).
        ConvergenceError: If ngspice output indicates a simulation convergence
            failure (subclass of :class:`SpiceRunError`).
    """
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

    return SpiceResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        log_path=log_path,
    )
