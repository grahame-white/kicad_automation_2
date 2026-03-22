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
invoked. CI enforces this rule by calling
`ci_feature.model_validation.validate_model_presence()` as a pre-flight check.

### Behaviour

- All paths in `models.libraries` are resolved **relative to the feature directory** (the
  directory containing `feature.yml`).
- If every path resolves to an existing file, validation passes silently.
- If one or more paths are missing, a `MissingModelError` is raised **before** ngspice is
  started. The error message includes:
  - The feature name.
  - The full absolute path of every missing file.

### Example

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
