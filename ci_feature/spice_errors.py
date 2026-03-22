"""Exception classes for ngspice error classification."""

__all__ = [
    "ConvergenceError",
    "MissingModelError",
    "SpiceRunError",
    "SpiceSyntaxError",
]


class SpiceRunError(Exception):
    """Raised when ngspice execution fails or cannot be launched."""


class MissingModelError(SpiceRunError):
    """Raised when ngspice cannot find a required model or include file."""


class SpiceSyntaxError(SpiceRunError):
    """Raised when ngspice reports a syntax or parse error in the netlist."""


class ConvergenceError(SpiceRunError):
    """Raised when ngspice fails to converge during simulation."""
