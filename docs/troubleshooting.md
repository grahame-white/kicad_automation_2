# Troubleshooting ngspice Errors

This document describes common ngspice failure modes, how they are detected,
and what to do when they occur.

## Error Classes

The SPICE runner classifies ngspice failures into four typed exception classes,
each of which is a subclass of `SpiceRunError`:

| Exception | Detection Pattern | Meaning |
|---|---|---|
| `MissingModelError` | `include not found` in output | A `.include` file or model library could not be opened |
| `SpiceSyntaxError` | `parse error` or `syntax error` in output | The netlist contains a syntax or parse error |
| `ConvergenceError` | `no convergence` or `timestep too small` in output | The simulation failed to converge |
| `SpiceRunError` | Non-zero exit, unclassified | Any other ngspice failure |

All exception messages include:
- The ngspice command that was executed
- The full stdout from ngspice
- The full stderr from ngspice
- The exit code

---

## MissingModelError

**Triggered by:** A `.include` directive that references a file ngspice cannot open.

**Example netlist** (`ci/fixtures/missing_model.spice`):

```spice
* Fixture that triggers a missing model/include error
.include "nonexistent_model.lib"
V1 in 0 DC 5V
R1 in out 1k
.dc V1 5 5 1
.print dc V(out)
.end
```

**Typical ngspice output:**

```
ERROR: .include not found: nonexistent_model.lib
```

**How to fix:**
- Verify the path in the `.include` directive is correct relative to the netlist file.
- Ensure the model library file exists and is readable.
- Check that the KiCad schematic references a model library that is installed.

---

## SpiceSyntaxError

**Triggered by:** A netlist line that ngspice cannot parse.

**Example netlist** (`ci/fixtures/syntax_error.spice`):

```spice
* Fixture that triggers a syntax/parse error
V1 in 0 DC 5V
.model BROKEN_MODEL %%% invalid_syntax_here
.dc V1 5 5 1
.print dc V(in)
.end
```

**Typical ngspice output:**

```
parse error at line 3
```

**How to fix:**
- Review the line number reported in the error message.
- Check for typos in component values, model names, or analysis commands.
- Validate the netlist against the ngspice manual for correct syntax.

---

## ConvergenceError

**Triggered by:** The simulator being unable to find a steady-state solution.

**Typical ngspice output:**

```
no convergence in transient analysis at t=1.23e-9
```

or

```
timestep too small: 1e-18
```

**How to fix:**
- Add `.options` directives to relax convergence tolerances:
  ```spice
  .options abstol=1e-10 reltol=0.01
  ```
- Check for discontinuities or unrealistic component values in the schematic.
- For transient analyses, ensure the initial conditions are consistent.
- Consider simplifying the circuit or splitting into smaller sub-circuits.

---

## SpiceRunError (Generic)

**Triggered by:** Any ngspice failure not matched by the patterns above.

This includes:
- ngspice not installed or not on `PATH`
- Netlist file not found
- Process timeout
- OS-level errors

**How to fix:**
- Confirm ngspice is installed: `ngspice --version`
- Check that the netlist path is correct and readable.
- If a timeout occurred, increase the `timeout` parameter passed to `run_spice()`.

---

## Catching Errors in Python

Because all typed exceptions inherit from `SpiceRunError`, you can catch
either all spice errors or just specific ones:

```python
from ci_feature.spice_errors import (
    ConvergenceError,
    MissingModelError,
    SpiceRunError,
    SpiceSyntaxError,
)
from ci_feature.spice_runner import run_spice

try:
    result = run_spice("my_circuit.spice", "/tmp/output")
except MissingModelError as exc:
    print(f"Missing model file — check .include paths:\n{exc}")
except SpiceSyntaxError as exc:
    print(f"Netlist syntax error — review the netlist:\n{exc}")
except ConvergenceError as exc:
    print(f"Convergence failure — check circuit values:\n{exc}")
except SpiceRunError as exc:
    # Catches any remaining SpiceRunError (including the subclasses above
    # if you remove the specific handlers).
    print(f"ngspice run failed:\n{exc}")
```
