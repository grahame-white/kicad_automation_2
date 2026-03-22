# CI Pipeline

## What CI currently does

The CI pipeline runs on every pull request and on every push to the `main` branch.

### Steps

1. **Checkout** – checks out the repository at the triggering commit.
2. **Set up Python** – installs the specified Python version (3.12).
3. **Install toolchain** – adds the KiCad 9.0 PPA (`ppa:kicad/kicad-9.0-releases`) and uses `apt-get` to install `kicad` 9.x (which provides `kicad-cli`) and `ngspice` on the Ubuntu runner.
4. **Check toolchain presence** – verifies that `kicad-cli`, `ngspice`, and `python` are available and prints their versions. Fails immediately with an actionable message if any tool is missing.
5. **Install dependencies** – runs `pip install -r requirements.txt` to install `pytest` and any other listed packages.
6. **Run tests** – executes `pytest -q`.  No tests exist yet; this step confirms that pytest is installed and can be invoked without error.

### Design decisions

- All GitHub Actions used in the CI workflow are pinned to a full commit SHA to prevent supply-chain attacks.
- Top-level workflow permissions are set to `none`; individual jobs request only what they need (`contents: read`).
- Dependabot is configured to keep GitHub Actions dependencies up to date automatically.

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
