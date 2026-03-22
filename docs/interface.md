# Interface Contract (`interface.yml`)

Every feature in this repository references an `interface.yml` file that describes the electrical signals exposed by the feature. This file is the single source of truth for interface contracts used in GWT scenarios and simulation.

## Schema

The interface contract is validated against the JSON Schema at [`ci/schemas/interface.schema.json`](../ci/schemas/interface.schema.json).

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Interface identifier. |
| `version` | string | Semantic version (e.g. `"1.0.0"`). |
| `signals` | array | List of signal definitions (at least one entry required). |

### Signal fields (each entry in `signals`)

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Signal name (used in GWT scenarios). |
| `direction` | string | `input` \| `output` \| `bidirectional` |
| `domain` | string | `analog` \| `digital` |
| `unit` | string | SI unit string (e.g., `V`, `A`, `Hz`). |
| `description` | string | Human-readable description of the signal. |

All signal fields are required. No additional properties are permitted at either the top level or within signal entries.

## Minimal example

```yaml
name: dc-power-supply
version: "1.0.0"
signals:
  - name: V_OUT
    direction: output
    domain: analog
    unit: V
    description: Output voltage
  - name: GND
    direction: input
    domain: analog
    unit: V
    description: Ground reference
```

## Validation

You can validate an `interface.yml` against the JSON Schema using `jsonschema`:

```python
import json
import jsonschema
import yaml

with open("ci/schemas/interface.schema.json") as f:
    schema = json.load(f)

with open("path/to/interface.yml") as f:
    interface = yaml.safe_load(f)

jsonschema.validate(instance=interface, schema=schema)
print("interface.yml is valid")
```

A missing required field (for example, omitting `signals`) produces a clear validation error:

```
jsonschema.exceptions.ValidationError: 'signals' is a required property
```

An invalid `direction` value produces:

```
jsonschema.exceptions.ValidationError: 'unknown' is not one of ['input', 'output', 'bidirectional']
```

## Feature-to-interface linkage

Every `feature.yml` must declare an `interface` field pointing to a valid `interface.yml`
within the same feature directory subtree.  When a feature manifest is loaded by
`ci_feature.manifest.load_manifest`, the referenced interface file is automatically
resolved and validated.

### Rules

1. The `interface` field in `feature.yml` must be a **relative path** to an
   `interface.yml` file inside the feature's directory subtree.
2. The referenced `interface.yml` must **exist** at that path.
3. The referenced `interface.yml` must be **parseable YAML** and must **conform to the
   interface JSON Schema** (`ci/schemas/interface.schema.json`).

### Failure modes

| Condition | Error raised | Error message includes |
|-----------|-------------|------------------------|
| `interface.yml` does not exist | `ManifestValidationError` | Feature name + missing path |
| `interface.yml` is not parseable YAML | `ManifestValidationError` | Feature name + path + YAML error |
| `interface.yml` fails schema validation | `ManifestValidationError` | Feature name + path + field name |

Example error when the interface file is missing:

```
ManifestValidationError: Feature 'voltage-regulator' references interface
'/path/to/feature/interface.yml' which does not exist
```

Example error when the interface file is invalid:

```
ManifestValidationError: Feature 'voltage-regulator' has invalid interface
'/path/to/feature/interface.yml': Interface validation failed: 'signals' is a required property
```

### Example feature.yml with interface linkage

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
```

The `interface: interface.yml` entry links this feature to the `interface.yml` file
in the same directory.  If that file is absent or invalid, loading the manifest will
fail with a clear error message that names both the feature and the problematic path.

