"""Behave step definitions for feature selection via the manifest discovery system."""

from behave import given

from ci_feature.discovery import discover_features


@given('the feature "{name}"')
def step_the_feature(context, name):
    """Select a feature by name using the manifest discovery system.

    Calls ``discover_features(context.feature_root)`` to locate all feature
    manifests, then finds the one whose ``name`` field matches *name* and
    stores it on ``context.feature_manifest`` for use in subsequent steps.

    Raises:
        AssertionError: When *name* is not found, with a message listing all
            discovered feature names.
    """
    features = discover_features(context.feature_root)
    for feature in features:
        if feature.name == name:
            context.feature_manifest = feature
            return
    available = [f.name for f in features]
    if not available:
        raise AssertionError(
            f"Feature '{name}' not found. No features were discovered in the repository."
        )
    raise AssertionError(f"Feature '{name}' not found. Available features: {', '.join(available)}")
