# Canonical GWT Sentence List

This document lists every supported Gherkin **Given-When-Then** sentence for
use in `.feature` files.  Each entry shows the canonical phrasing, the type
of every parameter, and a concrete example.

---

## Given

### `Given the feature "<name>"`

Select a feature by name using the manifest discovery system.  The loaded
`FeatureManifest` is stored on `context.feature_manifest` and
`context.feature_dir` for use in subsequent steps.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `string` | The `name` field from the feature's `feature.yml` |

**Example:**

```gherkin
Given the feature "voltage-regulator"
```

**Failure modes:**

- Feature name not found → `AssertionError` listing all discovered feature names.

---

## When

### `When the simulation is run`

Export the KiCad netlist for the current feature and run `ngspice` in batch
mode.  Stores the resulting `SpiceResult` (including any `.meas` measurements)
on `context.simulation_result` for use in subsequent `Then` assertion steps.

**Example:**

```gherkin
When the simulation is run
```

**Failure modes:**

| Condition | Exception |
|-----------|-----------|
| No feature manifest loaded | `AssertionError` |
| `kicad-cli` fails or is not installed | `NetlistExportError` |
| SPICE model file missing | `MissingModelError` |
| Required SPICE parameter absent | `MissingParameterError` |
| ngspice convergence failure | `ConvergenceError` |
| ngspice syntax/parse error | `SpiceSyntaxError` |
| Other ngspice failure | `SpiceRunError` |

---

## Then

### `Then "<signal>" is within "<tolerance>" of "<expected>"`

Assert that a named interface signal value, measured by the simulation via a
`.meas` directive, is within a specified tolerance of an expected value.

The *signal* must be declared in the feature's `interface.yml`.  The measured
value is looked up from `context.simulation_result.signals`, which is
populated by parsing ngspice `.meas` output lines of the form
`<name> = <value>` in the simulation log.

| Parameter | Type | Description |
|-----------|------|-------------|
| `signal` | `string` | Signal name as declared in the feature's `interface.yml` |
| `tolerance` | `"<number> <unit>"` | Maximum allowed deviation from the expected value |
| `expected` | `"<number> <unit>"` | Target value to compare the measurement against |

Both *tolerance* and *expected* must follow the `"<number> <unit>"` format,
for example `"0.1 V"` or `"3.3 V"`.  The numeric parts are compared; units
are included in failure messages for readability.

**Example:**

```gherkin
Then "V_OUT" is within "0.1 V" of "3.3 V"
```

**Failure message format:**

```
AssertionError: Signal 'V_OUT': measured 3.6 V, expected 3.3 ± 0.1 V
```

**Failure modes:**

| Condition | Exception |
|-----------|-----------|
| Signal not in `interface.yml` | `InterfaceValidationError` with signal name, interface name, and valid names |
| No simulation result on context | `AssertionError` |
| Signal name absent from `.meas` output | `AssertionError` with hint to add a `.meas` directive |
| Measured value outside tolerance | `AssertionError` with measured value, expected value, and tolerance |

**Adding measurements to a netlist:**

To make a signal available for assertion, add a `.meas` directive whose name
matches the interface signal name (SPICE is case-insensitive):

```spice
* Measure the DC output voltage at V_IN = 5 V
.meas dc V_OUT find V(vout) at=5
```

ngspice will then write a line such as:

```
v_out               =  3.300000e+00
```

to the simulation log, which `run_spice()` parses and stores in
`SpiceResult.signals["V_OUT"]`.

---

## Full scenario example

```gherkin
Feature: Voltage regulator output
  @slow
  Scenario: Output voltage is within 3 % of 3.3 V
    Given the feature "voltage-regulator"
    When the simulation is run
    Then "V_OUT" is within "0.1 V" of "3.3 V"
```
