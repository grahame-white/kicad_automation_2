# Feature Manifest (`feature.yml`)

Every feature in this repository is described by a `feature.yml` manifest file placed at the root of the feature directory. This file is the single source of truth for feature discovery, configuration, and CI orchestration.

## Schema

The manifest is validated against the JSON Schema at [`ci/schemas/feature.schema.json`](../ci/schemas/feature.schema.json).

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique feature identifier. |
| `version` | string | Semantic version (e.g. `"1.0.0"`). |
| `schematic` | string | Relative path to the KiCad schematic file. |
| `interface` | string or array of strings | Relative path(s) to interface contract YAML file(s) (often named `interface.yml`). Use a list when the feature satisfies multiple interface contracts. |
| `models.libraries` | array of strings | Relative paths to SPICE model files. |
| `models.required_parameters` | array of strings | Parameter names that must be supplied at runtime. |

### Optional fields

| Field | Type | Description |
|-------|------|-------------|
| `configuration` | object | Default values for parameters. Keys are parameter names; values are numbers, strings, or booleans. |

## Minimal example

```yaml
name: voltage-regulator
version: "1.0.0"
schematic: schematic/voltage-regulator.kicad_sch
interface: interface.yml
models:
  libraries:
    - models/ldo.spice
  required_parameters:
    - V_IN
    - V_OUT
configuration:
  V_IN: 5.0
```

When a feature satisfies more than one interface contract, declare them as a list:

```yaml
name: voltage-regulator
version: "1.0.0"
schematic: schematic/voltage-regulator.kicad_sch
interface:
  - interface.yml
  - thermal-interface.yml
models:
  libraries:
    - models/ldo.spice
  required_parameters:
    - V_IN
    - V_OUT
```

## Python API

Use `ci_feature.manifest.load_manifest()` to load and validate a manifest in one step:

```python
from ci_feature.manifest import load_manifest, ManifestValidationError

manifest = load_manifest("path/to/feature.yml")
print(manifest.name)        # e.g. "voltage-regulator"
print(manifest.version)     # e.g. "1.0.0"
print(manifest.schematic)   # e.g. "schematic/voltage-regulator.kicad_sch"
print(manifest.interface)   # e.g. ["interface.yml"] (always a list, even for a single entry)
print(manifest.models)      # dict with "libraries" and "required_parameters"
print(manifest.configuration)  # dict of defaults, or None if omitted
```

### Validation errors

`load_manifest()` raises descriptive exceptions for every failure mode:

| Situation | Exception | Example message |
|-----------|-----------|-----------------|
| File does not exist | `FileNotFoundError` | `Manifest file not found: path/to/feature.yml` |
| Malformed YAML | `ManifestValidationError` | `Failed to parse YAML in path/to/feature.yml: …` |
| Missing required field | `ManifestValidationError` | `Manifest validation failed: 'name' is a required property` |
| Invalid field value | `ManifestValidationError` | `Manifest validation failed: …` |

Example — handling errors:

```python
from ci_feature.manifest import load_manifest, ManifestValidationError

try:
    manifest = load_manifest("path/to/feature.yml")
except FileNotFoundError as exc:
    print(f"File not found: {exc}")
except ManifestValidationError as exc:
    print(f"Invalid manifest: {exc}")
```

## Model library rules

Every path listed under `models.libraries` must exist on the filesystem before ngspice is
invoked. Pass the manifest and its directory to `run_spice()` to enforce this automatically,
or call `ci_feature.model_validation.validate_model_presence()` directly as a pre-flight check.

### Behaviour

- All paths in `models.libraries` are resolved **relative to the feature directory** (the
  directory containing `feature.yml`).
- If every path resolves to an existing file, validation passes silently.
- If one or more paths are missing, a `MissingModelError` is raised **before** ngspice is
  started. The error message includes:
  - The feature name.
  - The full absolute path of every missing file.

### Enforcement via `run_spice()`

When `manifest` and `feature_dir` are supplied to `run_spice()`, the pre-flight check runs
automatically before the ngspice subprocess is launched:

```python
from ci_feature.manifest import load_manifest
from ci_feature.spice_runner import run_spice
from ci_feature.spice_errors import MissingModelError
import os

manifest = load_manifest("path/to/feature.yml")
feature_dir = os.path.dirname(os.path.realpath("path/to/feature.yml"))

# validate_model_presence is called automatically before ngspice starts
result = run_spice("path/to/netlist.spice", "path/to/output", manifest=manifest, feature_dir=feature_dir)
```

### Standalone enforcement

`validate_model_presence()` can also be called directly:

```python
from ci_feature.manifest import load_manifest
from ci_feature.model_validation import validate_model_presence
from ci_feature.spice_errors import MissingModelError
import os

manifest = load_manifest("path/to/feature.yml")
feature_dir = os.path.dirname(os.path.realpath("path/to/feature.yml"))

try:
    validate_model_presence(manifest, feature_dir)
except MissingModelError as exc:
    print(f"Pre-flight check failed: {exc}")
```

### Error format

When model files are missing, the error message follows this pattern:

```
Feature '<name>' is missing <n> model file[s]:
  /absolute/path/to/first/missing.spice
  /absolute/path/to/second/missing.spice
```

## Required parameterisation

Every parameter name listed in `models.required_parameters` must be supplied by
the scenario before ngspice runs.  This ensures that simulation failures caused
by missing substitution values are caught early — before the ngspice subprocess
is launched — with a clear, actionable error.

### Behaviour

- All names in `models.required_parameters` are compared against the keys of the
  `provided_params` mapping passed to `run_spice()` or `validate_required_parameters()`.
- If every required name is present in `provided_params`, validation passes silently.
- Extra parameters that are present in `provided_params` but not listed in
  `models.required_parameters` are silently accepted.
- If one or more required names are absent, a `MissingParameterError` is raised
  **before** ngspice is started.  The error message includes:
  - The feature name.
  - Every missing parameter name.

### Enforcement via `run_spice()`

Pass the parameter mapping via the `provided_params` keyword argument:

```python
from ci_feature.manifest import load_manifest
from ci_feature.spice_runner import run_spice
from ci_feature.spice_errors import MissingParameterError
import os

manifest = load_manifest("path/to/feature.yml")
feature_dir = os.path.dirname(os.path.realpath("path/to/feature.yml"))

# validate_required_parameters is called automatically before ngspice starts
result = run_spice(
    "path/to/netlist.spice",
    "path/to/output",
    manifest=manifest,
    feature_dir=feature_dir,
    provided_params={"V_IN": 5.0, "V_OUT": 3.3},
)
```

### Standalone enforcement

`validate_required_parameters()` can also be called directly:

```python
from ci_feature.manifest import load_manifest
from ci_feature.spice_runner import validate_required_parameters
from ci_feature.spice_errors import MissingParameterError

manifest = load_manifest("path/to/feature.yml")

try:
    validate_required_parameters(manifest, {"V_IN": 5.0, "V_OUT": 3.3})
except MissingParameterError as exc:
    print(f"Pre-flight check failed: {exc}")
```

### Error format

When required parameters are missing, the error message follows this pattern:

```
Feature '<name>' is missing <n> required parameter[s]:
  PARAM_ONE
  PARAM_TWO
```

## Low-level validation

You can also validate a manifest dict directly against the JSON Schema at
[`ci/schemas/feature.schema.json`](../ci/schemas/feature.schema.json) using
`jsonschema`:

```python
import json
import jsonschema
import yaml

with open("ci/schemas/feature.schema.json") as f:
    schema = json.load(f)

with open("path/to/feature.yml") as f:
    manifest = yaml.safe_load(f)

jsonschema.validate(instance=manifest, schema=schema)
print("feature.yml is valid")
```

A missing required field (for example, omitting `name`) produces a clear validation error:

```
jsonschema.exceptions.ValidationError: 'name' is a required property
```
