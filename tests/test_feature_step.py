"""Unit tests for features/steps/feature_steps.py."""

from unittest.mock import MagicMock, patch

import pytest
from hamcrest import assert_that, contains_string, equal_to, none

from ci_feature.manifest import FeatureManifest
from features.steps.feature_steps import step_the_feature


def _make_manifest(name, directory=None):
    """Create a minimal FeatureManifest with the given name for testing."""
    return FeatureManifest(
        name=name,
        version="1.0.0",
        schematic=f"schematic/{name}.kicad_sch",
        interface=["interface.yml"],
        models={"libraries": [], "required_parameters": []},
        directory=directory,
    )


def test_step_loads_manifest_by_name():
    """step_the_feature stores the matching manifest on context.feature_manifest."""
    context = MagicMock()
    context.feature_root = "/repo"
    manifests = [_make_manifest("voltage-regulator"), _make_manifest("current-sensor")]

    with patch("features.steps.feature_steps.discover_features", return_value=manifests):
        step_the_feature(context, "voltage-regulator")

    assert_that(context.feature_manifest, equal_to(manifests[0]))


def test_step_selects_correct_manifest_when_multiple_exist():
    """step_the_feature selects the correct manifest when multiple features are discovered."""
    context = MagicMock()
    context.feature_root = "/repo"
    manifests = [_make_manifest("voltage-regulator"), _make_manifest("current-sensor")]

    with patch("features.steps.feature_steps.discover_features", return_value=manifests):
        step_the_feature(context, "current-sensor")

    assert_that(context.feature_manifest, equal_to(manifests[1]))


def test_step_stores_feature_dir_from_manifest():
    """step_the_feature stores context.feature_dir from the matched manifest's directory field."""
    context = MagicMock()
    context.feature_root = "/repo"
    manifests = [
        _make_manifest("voltage-regulator", directory="/repo/schematics/voltage-regulator"),
        _make_manifest("current-sensor"),
    ]

    with patch("features.steps.feature_steps.discover_features", return_value=manifests):
        step_the_feature(context, "voltage-regulator")

    assert_that(context.feature_dir, equal_to("/repo/schematics/voltage-regulator"))


def test_step_stores_none_feature_dir_when_manifest_has_no_directory():
    """step_the_feature stores None for context.feature_dir when manifest.directory is None."""
    context = MagicMock()
    context.feature_root = "/repo"
    manifests = [_make_manifest("voltage-regulator", directory=None)]

    with patch("features.steps.feature_steps.discover_features", return_value=manifests):
        step_the_feature(context, "voltage-regulator")

    assert_that(context.feature_dir, none())


def test_step_not_found_raises_assertion_error():
    """step_the_feature raises AssertionError when the requested feature name is not found."""
    context = MagicMock()
    context.feature_root = "/repo"
    manifests = [_make_manifest("voltage-regulator"), _make_manifest("current-sensor")]

    with patch("features.steps.feature_steps.discover_features", return_value=manifests):
        with pytest.raises(AssertionError):
            step_the_feature(context, "unknown-feature")


def test_step_not_found_message_lists_available_names():
    """step_the_feature error message lists all discovered feature names."""
    context = MagicMock()
    context.feature_root = "/repo"
    manifests = [_make_manifest("voltage-regulator"), _make_manifest("current-sensor")]

    with patch("features.steps.feature_steps.discover_features", return_value=manifests):
        with pytest.raises(AssertionError) as exc_info:
            step_the_feature(context, "unknown-feature")

    assert_that(str(exc_info.value), contains_string("voltage-regulator"))
    assert_that(str(exc_info.value), contains_string("current-sensor"))


def test_step_not_found_message_includes_requested_name():
    """step_the_feature error message includes the name that was requested."""
    context = MagicMock()
    context.feature_root = "/repo"
    manifests = [_make_manifest("voltage-regulator")]

    with patch("features.steps.feature_steps.discover_features", return_value=manifests):
        with pytest.raises(AssertionError) as exc_info:
            step_the_feature(context, "unknown-feature")

    assert_that(str(exc_info.value), contains_string("unknown-feature"))


def test_step_not_found_when_no_features_discovered():
    """step_the_feature fails with a clear message when no features are discovered at all."""
    context = MagicMock()
    context.feature_root = "/repo"

    with patch("features.steps.feature_steps.discover_features", return_value=[]):
        with pytest.raises(AssertionError) as exc_info:
            step_the_feature(context, "voltage-regulator")

    assert_that(str(exc_info.value), contains_string("voltage-regulator"))
    assert_that(str(exc_info.value), contains_string("No features were discovered"))
