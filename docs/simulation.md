# Simulation with ngspice

This document explains how the CI pipeline runs ngspice SPICE simulations and
describes the expected output structure.

## Overview

The `run_spice()` function in `ci_feature/spice_runner.py` wraps `ngspice` for
use in automated CI pipelines.  It runs ngspice in batch mode, captures all
output, and raises a typed exception on failure so callers can distinguish
simulation errors from infrastructure errors.

## ngspice Invocation

ngspice is invoked in batch mode using the `-b` flag, which suppresses the
interactive prompt and runs the netlist to completion:

```
ngspice -b -o <output_dir>/ngspice.log <netlist_path>
```

| Flag | Purpose |
|------|---------|
| `-b` | Batch mode — run non-interactively and exit when the netlist is complete |
| `-o <log>` | Write simulation output to the specified log file |

## Minimal Fixture

A known-good netlist lives at `ci/fixtures/minimal.spice`.  It implements a
simple resistor voltage divider and runs a `.dc` sweep:

```spice
* Minimal resistor divider
V1 in 0 DC 5V
R1 in mid 1k
R2 mid 0 1k
.dc V1 5 5 1
.print dc V(mid)
.end
```

The `.dc` analysis evaluates `V1` at a single operating point of 5 V (start=5,
stop=5, step=1).  With `R1 = R2 = 1 kΩ`, the midpoint voltage `V(mid)` is
expected to be **2.5 V**.

## API

```python
from ci_feature.spice_runner import run_spice, SpiceRunError, SpiceResult

try:
    result: SpiceResult = run_spice("ci/fixtures/minimal.spice", "/tmp/spice_out", timeout=60)
except SpiceRunError as exc:
    print(f"Simulation failed: {exc}")
else:
    print(f"stdout: {result.stdout}")
    print(f"stderr: {result.stderr}")
    print(f"log:    {result.log_path}")
```

### `SpiceResult` fields

| Field | Type | Description |
|-------|------|-------------|
| `returncode` | `int` | ngspice exit code (0 on success) |
| `stdout` | `str` | Captured standard output |
| `stderr` | `str` | Captured standard error |
| `log_path` | `str` | Absolute path to the ngspice log file |

### `SpiceRunError`

Raised when:

- The netlist file does not exist.
- `ngspice` is not installed or cannot be launched.
- `ngspice` exits with a non-zero status code.
- `ngspice` does not complete within the *timeout* seconds.

The exception message always includes the attempted command and any captured
stdout/stderr so failures are immediately actionable.

## Output Structure

For a simulation run with `output_dir="/tmp/spice_out"`, the following file
is created:

```
/tmp/spice_out/
└── ngspice.log     # full simulation transcript written by ngspice -o
```

The `SpiceResult.log_path` field points to `ngspice.log` inside `output_dir`.
