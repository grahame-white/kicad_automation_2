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
| `interface` | string | Relative path to `interface.yml`. |
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

## Validation

Install the `jsonschema` Python library (already listed in `requirements.txt`), then run:

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
