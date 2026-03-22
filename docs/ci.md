# CI Pipeline

## What CI currently does

The CI pipeline runs on every pull request and on every push to the `main` branch.

### Steps

1. **Checkout** – checks out the repository at the triggering commit.
2. **Set up Python** – installs the specified Python version (3.12).
3. **Install dependencies** – runs `pip install -r requirements.txt` to install `pytest` and any other listed packages.
4. **Run tests** – executes `pytest -q`.  No tests exist yet; this step confirms that pytest is installed and can be invoked without error.

### Design decisions

- All GitHub Actions used in the CI workflow are pinned to a full commit SHA to prevent supply-chain attacks.
- Top-level workflow permissions are set to `none`; individual jobs request only what they need (`contents: read`).
- Dependabot is configured to keep GitHub Actions dependencies up to date automatically.
