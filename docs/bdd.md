# BDD with Behave

This project uses [Behave](https://behave.readthedocs.io/) to run BDD (Behaviour-Driven Development) scenarios written in [Gherkin](https://cucumber.io/docs/gherkin/) syntax.

## Directory structure

```
features/
  example.feature          # Gherkin feature files
  steps/
    example_steps.py       # Python step-definition files
```

All feature files live under `features/` and all step-definition modules live under `features/steps/`.

## Running scenarios locally

Install the dependencies and run `behave` from the repository root:

```bash
pip install -r requirements.txt
behave
```

## Adding a new scenario

1. **Write a feature file** – create (or edit) a `.feature` file under `features/`.  Each file describes one feature and may contain one or more scenarios written in Gherkin:

   ```gherkin
   Feature: My new feature
     Scenario: Something useful happens
       Given some precondition
       When an action is taken
       Then the expected outcome is observed
   ```

2. **Implement the steps** – create (or edit) a Python module under `features/steps/` and implement any unrecognised steps using the `@given`, `@when`, and `@then` decorators from `behave`:

   ```python
   from behave import given, then, when

   @given("some precondition")
   def step_some_precondition(context):
       # set up state on the context object
       pass

   @when("an action is taken")
   def step_an_action_is_taken(context):
       # perform the action
       pass

   @then("the expected outcome is observed")
   def step_expected_outcome_is_observed(context):
       # assert the outcome
       pass
   ```

3. **Verify locally** – run `behave` and confirm all scenarios pass before opening a pull request.

## Scenario tags (`@fast` / `@schema` / `@slow`)

Scenarios can be tagged to control execution order and filtering.

| Tag | Meaning | When to use |
|-----|---------|-------------|
| `@fast` | Short-running simulation smoke test; may require KiCad/SPICE toolchain | Quick pass/fail simulation checks |
| `@schema` | Schema or manifest validation, no external tooling required | Validating JSON Schema, YAML manifests, or file structure |
| `@slow` | Long-running, requires KiCad/SPICE toolchain | Full simulation or export scenarios |

Tag a scenario by placing the tag on the line immediately above the `Scenario:` keyword:

```gherkin
Feature: My feature
  @fast
  Scenario: Quick simulation sanity check
    Given the system is ready
    When nothing happens
    Then the result is as expected

  @schema
  Scenario: Manifest validation check
    Given the feature manifest schema is loaded
    When a valid feature manifest is validated
    Then validation succeeds
```

### Running tagged scenarios locally

```bash
# Run only fast scenarios
behave --tags=@fast

# Run only schema scenarios
behave --tags=@schema

# Run only slow scenarios
behave --tags=@slow

# Exclude slow scenarios
behave --tags=~@slow
```

### CI tag ordering

The CI pipeline runs `@fast` scenarios in a dedicated step **before** the full suite.  This ensures that fundamental simulation errors are caught quickly, without waiting for long-running simulations to finish.  The `@schema` scenarios also run in this early step so that manifest or schema issues are surfaced immediately.

## Interface-only observability rule

Scenarios may only reference signals that are declared in the feature's `interface.yml` contract.  Referencing an internal schematic net that is not declared in the interface is a contract violation and must fail **before** any simulation runs.

The helper `validate_signal_name(signal_name, interface)` in `ci_feature/interface.py` is used to enforce this rule.  Step definitions that reference or validate signal names should call this function to check the name against the loaded `InterfaceContract`.  If the name is not present, an `InterfaceValidationError` is raised immediately with a message that includes:

- the **invalid signal name** that was referenced,
- the **interface/feature name** it was validated against, and
- the **list of all valid signal names** declared in that interface.

### Example error

```
InterfaceValidationError: Signal 'NET001' is not declared in interface 'dc-power-supply'.
Valid signals are: V_OUT, GND
```

### Why this rule exists

Internal net names (e.g. `NET001`) are an implementation detail of the schematic and may change without notice.  Allowing scenarios to assert on internal nets would couple tests to the schematic internals, making them brittle and defeating the purpose of the interface contract.

## Feature selection in scenarios

Scenarios can select a feature by name using the `Given the feature "<name>"` step.  This step
uses the manifest discovery system to locate the feature's `feature.yml` file and loads it for
use in subsequent steps.

```gherkin
Feature: Voltage regulator
  Scenario: Output voltage in tolerance
    Given the feature "voltage-regulator"
    ...
```

The step calls `discover_features()` from `ci_feature/discovery.py` to scan the repository for
all `feature.yml` files, then finds the one whose `name` field matches the requested name.  The
loaded `FeatureManifest` is stored on `context.feature_manifest` for use in subsequent steps.

If the requested name is not found, the step fails immediately with a clear error message listing
all feature names that were discovered:

```
AssertionError: Feature 'unknown-feature' not found. Available features: voltage-regulator, current-sensor
```

The repository root used for discovery is set by the `before_scenario` hook in
`features/environment.py`.  It defaults to the root of the repository so no additional
configuration is required.

## CI integration

The CI pipeline runs `behave` automatically on every pull request and push to `main`.  See [ci.md](ci.md) for details of the rest of the CI pipeline (currently focused on the pytest-based tests).
