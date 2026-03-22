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

Every `feature.yml` must declare an `interface` field pointing to one or more valid
`interface.yml` files within the same feature directory subtree.  When a feature manifest
is loaded by `ci_feature.manifest.load_manifest`, every referenced interface file is
automatically resolved and validated.

An interface contract describes a reusable electrical API.  **Multiple features can each
implement the same interface contract** — each feature has its own copy of the
`interface.yml` (isolation rules require all paths to remain inside the feature's own
directory subtree).  Equally, **a single feature may satisfy multiple interface contracts**
by listing more than one path in the `interface` field.

### Rules

1. The `interface` field in `feature.yml` must be a **relative path string** or a
   **non-empty list of relative path strings**, all pointing to `interface.yml` files
   inside the feature's directory subtree.
2. Every referenced `interface.yml` must **exist** at its declared path.
3. Every referenced `interface.yml` must be **parseable YAML** and must **conform to the
   interface JSON Schema** (`ci/schemas/interface.schema.json`).

### Failure modes

| Condition | Error raised | Error message includes |
|-----------|-------------|------------------------|
| An `interface.yml` does not exist | `ManifestValidationError` | Feature name + missing path |
| An `interface.yml` is not parseable YAML | `ManifestValidationError` | Feature name + path + YAML error |
| An `interface.yml` fails schema validation | `ManifestValidationError` | Feature name + path + field name |

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

### Example feature.yml — single interface

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

The `interface: interface.yml` entry links this feature to a single `interface.yml` in
the same directory.

### Example feature.yml — multiple interfaces

A feature can satisfy more than one interface contract by declaring a list:

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

Both `interface.yml` and `thermal-interface.yml` must exist in the feature directory and
pass schema validation.  The `FeatureManifest.interface` attribute is always a list of
strings — even when a single string is declared in `feature.yml`, it is normalised to a
one-element list.

### Multiple features implementing the same interface

The most common relationship is **many-to-one**: several independent features each provide
their own implementation of the same interface contract.  Because isolation rules require
every path to remain inside the feature's own directory subtree, each feature owns a copy
of the `interface.yml` that describes the contract it satisfies.  The CI system validates
each copy independently.

Example — two features each implementing the `dc-power-supply` contract:

```
features/
  voltage-regulator/
    feature.yml          # interface: interface.yml
    interface.yml        # name: dc-power-supply, version: "1.0.0", signals: [...]
    schematic/...
    models/...
  switched-mode-psu/
    feature.yml          # interface: interface.yml
    interface.yml        # name: dc-power-supply, version: "1.0.0", signals: [...]
    schematic/...
    models/...
```

Both `voltage-regulator/interface.yml` and `switched-mode-psu/interface.yml` describe the
same `dc-power-supply` contract.  There is no shared file — each feature is fully
self-contained.  CI validates each independently and will fail if either copy becomes
malformed or goes missing.

