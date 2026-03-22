# Architecture

## Feature Isolation Rules

Every `feature.yml` manifest must reference only files that live **inside** the feature's own
directory.  This is enforced automatically when a manifest is loaded via
`ci_feature.manifest.load_manifest()`.

### Rules

1. **Paths must be relative** — Absolute paths (e.g. `/usr/share/models/ldo.spice`) are not
   permitted.
2. **Paths must stay within the feature directory** — Paths that escape the feature's directory
   subtree via `../` components (e.g. `../../shared/model.spice`) are not permitted.

These rules apply to every file-path field in `feature.yml`:

| Field | Description |
|-------|-------------|
| `schematic` | Path to the KiCad schematic file |
| `interface` | Path to the interface definition file |
| `models.libraries[]` | Paths to SPICE model library files |

### Rationale

Enforcing path locality ensures that features are:

- **Portable** — A feature directory can be moved or copied without breaking path references.
- **Self-contained** — All files referenced by a feature are bundled with it.
- **Auditable** — Reviewers can verify a feature's file dependencies at a glance without
  chasing paths across the repository.

### Enforcement

Isolation is validated in `ci_feature.manifest.load_manifest()` by calling
`ci_feature.isolation.validate_isolation()` after JSON Schema validation succeeds.

Violations raise `ci_feature.isolation.IsolationViolationError` with a message that:

- Names the offending field (e.g. `'schematic'`) and the offending path.
- States which isolation rule was violated.
- Suggests how to fix the problem.

### Examples

**Valid** — all paths are relative and within the feature directory:

```yaml
schematic: schematic/my-feature.kicad_sch
interface: interface.yml
models:
  libraries:
    - models/component.spice
```

**Invalid** — absolute path:

```yaml
schematic: /usr/share/kicad/my-feature.kicad_sch  # ← not allowed; use a relative path
```

**Invalid** — path escaping the feature subtree:

```yaml
schematic: ../../shared/my-feature.kicad_sch  # ← not allowed; remove ../ components
```

### API

```python
from ci_feature.isolation import IsolationViolationError, validate_isolation

# Called automatically by load_manifest(); can also be used directly.
validate_isolation("/path/to/feature-dir", manifest_data_dict)
```

`load_manifest()` raises `IsolationViolationError` (not `ManifestValidationError`) for isolation
failures, allowing callers to distinguish between schema errors and path-locality errors.
