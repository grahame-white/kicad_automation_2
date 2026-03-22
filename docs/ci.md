# CI Pipeline

## What CI currently does

The CI pipeline runs on every pull request and on every push to the `main` branch.

### Steps

1. **Checkout** – checks out the repository at the triggering commit.
2. **Set up Python** – installs the specified Python version (3.12).
3. **Check toolchain presence** – verifies that `kicad-cli`, `ngspice`, and `python` are available and prints their versions. Fails immediately with an actionable message if any tool is missing.
4. **Install dependencies** – runs `pip install -r requirements.txt` to install `pytest` and any other listed packages.
5. **Run tests** – executes `pytest -q`.  No tests exist yet; this step confirms that pytest is installed and can be invoked without error.

### Design decisions

- All GitHub Actions used in the CI workflow are pinned to a full commit SHA to prevent supply-chain attacks.
- Top-level workflow permissions are set to `none`; individual jobs request only what they need (`contents: read`).
- Dependabot is configured to keep GitHub Actions dependencies up to date automatically.

## Toolchain requirements

The CI pipeline requires the following tools to be present on the runner. A dedicated **Check toolchain presence** step verifies each tool before any other work begins and fails with an explicit, actionable message if a tool is missing.

| Tool | Purpose | Install reference |
|------|---------|-------------------|
| `kicad-cli` | Schematic and PCB export / DRC | <https://www.kicad.org/download/> |
| `ngspice` | SPICE simulation | <https://ngspice.sourceforge.io/> |
| `python` | BDD step definitions and automation scripts | <https://www.python.org/downloads/> |

If a tool is missing the step prints a message such as:

```
ERROR: kicad-cli not found. Please install KiCad (https://www.kicad.org/download/).
```

and exits with a non-zero status so that the CI job fails immediately rather than producing a cryptic error later.
