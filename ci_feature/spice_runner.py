"""ngspice runner for SPICE netlist simulation."""

import os
import shlex
import subprocess
from dataclasses import dataclass

__all__ = [
    "SpiceRunError",
    "SpiceResult",
    "run_spice",
]


class SpiceRunError(Exception):
    """Raised when ngspice execution fails or cannot be launched."""


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
            if ``ngspice`` exits with a non-zero status; if *netlist_path*
            does not exist; or if ``ngspice`` does not complete within
            *timeout* seconds.  Error messages include the command that was
            attempted and any captured stdout/stderr.
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
        raise SpiceRunError(
            f"Failed to run ngspice.\n"
            f"Command: {shlex.join(cmd)}\n"
            f"Original error: {exc.__class__.__name__}: {exc}"
        ) from exc

    if result.returncode != 0:
        raise SpiceRunError(
            f"ngspice failed (exit code {result.returncode}).\n"
            f"Command: {shlex.join(cmd)}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    return SpiceResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        log_path=log_path,
    )
