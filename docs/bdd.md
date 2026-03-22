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

## CI integration

The CI pipeline runs `behave` automatically on every pull request and push to `main`.  See [ci.md](ci.md) for details of the rest of the CI pipeline (currently focused on the pytest-based tests).
