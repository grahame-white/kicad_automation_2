# CI Pipeline

## What CI currently does

The CI pipeline runs on every pull request and on every push to the `main` branch.

It is structured as two sequential jobs: `fast-check` and `full-suite`. See [Fail-fast gating](#fail-fast-gating) for details.

### `fast-check` job steps

1. **Checkout** – checks out the repository at the triggering commit.
2. **Set up Python** – installs the specified Python version (3.12).
3. **Shared CI setup** – runs `.github/actions/ci-setup` (composite action) which installs the KiCad/ngspice toolchain, checks tool presence, and installs Python dependencies.  See [Toolchain requirements](#toolchain-requirements).
4. **Run tests** – executes `pytest -q` to run the unit test suite under `tests/`.  Exit code 5 ("no tests collected") is treated as success to allow the step to pass on a fresh checkout before any test files are added.
5. **Run fast BDD scenarios** – executes `behave --tags=@fast` to run only the `@fast`-tagged scenarios.  Failures here block the `full-suite` job from running.

### `full-suite` job steps

1. **Checkout** – checks out the repository at the triggering commit.
2. **Set up Python** – installs the specified Python version (3.12).
3. **Shared CI setup** – runs `.github/actions/ci-setup` (same composite action as `fast-check`).
4. **Run BDD scenarios** – executes the full Behave suite with the HTML formatter, producing `reports/behave-report.html`.
5. **Upload behave reports** – uploads the `reports/` directory as a downloadable artifact named `behave-reports`.

### Design decisions

- All GitHub Actions used in the CI workflow are pinned to a full commit SHA to prevent supply-chain attacks.
- Top-level workflow permissions are set to `none`; individual jobs request only what they need (`contents: read`).
- Dependabot is configured to keep GitHub Actions dependencies up to date automatically.

## Fail-fast gating

The CI pipeline uses a two-stage approach to give quick feedback on fundamental errors before investing time in the full simulation suite.

```
fast-check  ──►  full-suite
```

- **`fast-check`** runs `behave --tags=@fast` (plus `pytest`).  These scenarios are tagged `@fast` because they complete quickly and cover the most critical paths.  If any `@fast` scenario fails, the job fails immediately and the `full-suite` job is **blocked** from running.
- **`full-suite`** depends on `fast-check` via `needs: fast-check`.  It only starts if `fast-check` passes, then runs the complete Behave suite and uploads the HTML report as part of the `reports/` artifact.

This means:

- A broken fundamental always fails the PR quickly, without waiting for the full (slower) simulation suite.
- The full suite only consumes runner resources when the fast scenarios are healthy.
- CI output clearly shows two separate stages so it is easy to see at a glance which stage failed.
- When `fast-check` is red, `full-suite` never runs, so no `reports/` artifact (including `behave-report.html`) will be generated or uploaded for that run.

## Toolchain requirements

The CI pipeline requires the following tools to be present on the runner. A dedicated **Check toolchain presence** step verifies each tool before any other work begins and fails with an explicit, actionable message if a tool is missing. The table below documents the versions and sources that CI currently uses.

| Tool | Purpose | Tested version / source | Install reference |
|------|---------|-------------------------|-------------------|
| `kicad-cli` | Schematic and PCB export / DRC | 9.x (via `ppa:kicad/kicad-9.0-releases`, apt package `kicad`) | <https://www.kicad.org/download/> |
| `ngspice` | SPICE simulation | Version from `ubuntu-latest` runner image (apt package `ngspice`) | <https://ngspice.sourceforge.io/> |
| `python` | BDD step definitions and automation scripts | 3.12.x (via `actions/setup-python` in CI) | <https://www.python.org/downloads/> |

If a tool is missing the step prints a message such as:

```
ERROR: kicad-cli not found. In CI, this should be provided by the 'Install toolchain' step (apt package 'kicad') or the runner image. Please update that step or the image.
```

and exits with a non-zero status so that the CI job fails immediately rather than producing a cryptic error later.

## Feature discovery

The CI pipeline uses automatic feature discovery — there is no central registry of features.
The `discover_features(root_path)` function in `ci_feature/discovery.py` recursively scans the
repository for `feature.yml` files, loads and validates each one, and returns the results as a
sorted list of `FeatureManifest` objects.

### How it works

1. `os.walk` descends into every subdirectory under `root_path`.
2. Any directory that contains a file named `feature.yml` is treated as a feature directory.
3. Each `feature.yml` is loaded and validated via `load_manifest()` (see
   [Feature manifest](feature-manifest.md)).
4. The resulting manifests are returned **sorted alphabetically by each manifest's file path**,
   guaranteeing a deterministic and repeatable order across CI runs.

### Usage

```python
from ci_feature.discovery import discover_features

features = discover_features(root_path="/repo")
# Returns list[FeatureManifest], sorted alphabetically by each manifest's file path
```

### Design decisions

- **No central registry** – adding a new feature only requires creating a `feature.yml` file;
  no other registration step is needed.
- **Deterministic order** – results are sorted by path so that CI output is reproducible and
  easy to compare across runs.
- **Fail-fast validation** – `load_manifest()` validates each manifest against the JSON Schema
  during discovery, so malformed manifests are caught immediately.

## Scenario discovery and ordering

The CI pipeline pairs each feature manifest with its associated ``*.feature`` scenario files
using automatic scenario discovery — there is no central registry of scenarios.
The `discover_scenarios(root_path)` function in `ci_feature/scenario_discovery.py` builds on
`discover_features()` by scanning each feature's directory for ``*.feature`` files and returning
a sorted list of ``(FeatureManifest, Path)`` pairs.

### How it works

1. `discover_features(root_path)` is called to locate all feature manifests (see
   [Feature discovery](#feature-discovery) above).
2. For each discovered manifest, every ``*.feature`` file within that feature's directory
   subtree is found via `os.walk`.
3. The resulting ``(manifest, scenario_path)`` pairs are returned **sorted by
   ``(feature directory, scenario file path)``**, guaranteeing a deterministic and repeatable
   order across CI runs.

### Usage

```python
from ci_feature.scenario_discovery import discover_scenarios

pairs = discover_scenarios(root_path="/repo")
# Returns: [(FeatureManifest, Path), ...] sorted by (feature_dir, scenario_file)
```

### Design decisions

- **Deterministic order** – results are sorted by ``(feature directory, scenario file path)``
  so that batching and parallelism decisions are stable and reproducible across CI runs.
- **No central registry** – adding a scenario only requires creating a ``*.feature`` file
  inside the relevant feature directory; no other registration step is needed.
- **Composable** – `discover_scenarios` delegates feature discovery to `discover_features`,
  so isolation and validation behaviour are shared. The directory-pruning rules (e.g. `.git`,
  `__pycache__`, `.venv`) are defined once in `ci_feature.discovery` and reused by both
  passes, eliminating the risk of the two drifting apart.

## Netlist artefacts

The CI pipeline exports a KiCad netlist for each feature's schematic using
`kicad-cli sch export netlist`.  The `export_netlist()` function in
`ci_feature/kicad_export.py` handles this step.

### Output location

Netlists are written to a per-feature subdirectory within the CI workspace
directory (default: `/tmp/ci_workspace`):

```
{output_dir}/{feature-name}/{feature-name}.net
```

For example, a feature named `voltage-regulator` produces:

```
/tmp/ci_workspace/voltage-regulator/voltage-regulator.net
```

### Usage

```python
from ci_feature.kicad_export import export_netlist

netlist_path = export_netlist(manifest, output_dir="/tmp/ci_workspace", feature_dir="/repo/features/voltage-regulator")
# Returns path to the generated netlist file, e.g. /tmp/ci_workspace/voltage-regulator/voltage-regulator.net
```

### Error handling

- If `kicad-cli` exits with a non-zero status, a `NetlistExportError` is raised
  with the exit code and the full stdout/stderr captured from `kicad-cli`,
  making the failure immediately actionable.
- If the expected output file is missing or empty after a successful `kicad-cli`
  run, a `NetlistExportError` is raised with the expected file path.

## Behavioural test reports

After the **Run BDD scenarios** step completes (whether it passes or fails), the CI pipeline uploads the contents of the `reports/` directory as a downloadable artifact named **`behave-reports`**.

### What is included

| Path | Contents |
|------|----------|
| `reports/junit/` | JUnit XML files — one per feature file — produced by Behave's built-in JUnit formatter.  These are compatible with most CI report parsers and test-result viewers. |
| `reports/behave-report.html` | Self-contained HTML report produced by `behave-html-formatter`.  Open the file in any browser for a colour-coded, collapsible view of features, scenarios and step outcomes. |

### How to download the reports

1. Open the **Actions** tab of the repository on GitHub.
2. Select the workflow run of interest.
3. Scroll to the **Artifacts** section at the bottom of the summary page.
4. Click **`behave-reports`** to download the ZIP archive.
5. Unzip, then:
   - Open `behave-report.html` in any browser for the colour-coded, human-readable summary.
   - Open the XML files under `junit/` in any JUnit-compatible viewer for tooling integration.
