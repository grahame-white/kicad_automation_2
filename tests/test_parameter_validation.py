"""Unit tests for validate_required_parameters in ci_feature.spice_runner."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest
from hamcrest import assert_that, contains_string, equal_to, instance_of

from ci_feature.spice_errors import MissingParameterError
from ci_feature.spice_runner import validate_required_parameters


@dataclass
class _FakeManifest:
    """Minimal stand-in for FeatureManifest used in these tests."""

    name: str
    models: Dict[str, Any]
    version: str = "1.0.0"
    schematic: str = "schematic/voltage-regulator.kicad_sch"
    interface: List[str] = None
    configuration: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.interface is None:
            self.interface = ["interface.yml"]


# ---------------------------------------------------------------------------
# All required parameters provided — validation passes
# ---------------------------------------------------------------------------


def test_validate_required_parameters_passes_when_all_provided():
    """validate_required_parameters() returns None when all required params are present."""
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN", "V_OUT"]},
    )

    result = validate_required_parameters(manifest, {"V_IN": 5.0, "V_OUT": 3.3})

    assert_that(result, equal_to(None))


def test_validate_required_parameters_passes_with_no_required_params():
    """validate_required_parameters() returns None when required_parameters is empty."""
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": []},
    )

    result = validate_required_parameters(manifest, {})

    assert_that(result, equal_to(None))


def test_validate_required_parameters_passes_with_extra_params_provided():
    """Extra parameters not in required list are silently accepted."""
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN"]},
    )

    result = validate_required_parameters(manifest, {"V_IN": 5.0, "EXTRA_PARAM": 42})

    assert_that(result, equal_to(None))


def test_validate_required_parameters_passes_with_none_params_and_no_required():
    """validate_required_parameters() returns None when provided_params is None and nothing
    required."""
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": []},
    )

    result = validate_required_parameters(manifest, None)

    assert_that(result, equal_to(None))


# ---------------------------------------------------------------------------
# One required parameter missing — MissingParameterError raised
# ---------------------------------------------------------------------------


def test_validate_required_parameters_raises_when_one_missing():
    """validate_required_parameters() raises MissingParameterError when one param is absent."""
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN"]},
    )

    with pytest.raises(MissingParameterError):
        validate_required_parameters(manifest, {})


def test_validate_required_parameters_error_includes_missing_name():
    """MissingParameterError message includes the missing parameter name."""
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN"]},
    )

    with pytest.raises(MissingParameterError) as exc_info:
        validate_required_parameters(manifest, {})

    assert_that(str(exc_info.value), contains_string("V_IN"))


def test_validate_required_parameters_error_includes_feature_name():
    """MissingParameterError message includes the feature name."""
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN"]},
    )

    with pytest.raises(MissingParameterError) as exc_info:
        validate_required_parameters(manifest, {})

    assert_that(str(exc_info.value), contains_string("voltage-regulator"))


def test_validate_required_parameters_error_is_missing_parameter_error():
    """MissingParameterError is the exact exception type raised."""
    manifest = _FakeManifest(
        name="my-feature",
        models={"libraries": [], "required_parameters": ["FREQ"]},
    )

    with pytest.raises(MissingParameterError) as exc_info:
        validate_required_parameters(manifest, {})

    assert_that(exc_info.value, instance_of(MissingParameterError))


def test_validate_required_parameters_raises_when_one_of_many_missing():
    """MissingParameterError is raised when only one of several required params is missing."""
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN", "V_OUT"]},
    )

    with pytest.raises(MissingParameterError) as exc_info:
        validate_required_parameters(manifest, {"V_IN": 5.0})

    assert_that(str(exc_info.value), contains_string("V_OUT"))


# ---------------------------------------------------------------------------
# Multiple missing parameters — all listed in the error message
# ---------------------------------------------------------------------------


def test_validate_required_parameters_raises_when_multiple_missing():
    """validate_required_parameters() raises MissingParameterError when multiple params missing."""
    manifest = _FakeManifest(
        name="multi-param-feature",
        models={"libraries": [], "required_parameters": ["V_IN", "V_OUT", "FREQ"]},
    )

    with pytest.raises(MissingParameterError):
        validate_required_parameters(manifest, {})


def test_validate_required_parameters_error_lists_all_missing_params():
    """MissingParameterError message lists every missing parameter when multiple are absent."""
    manifest = _FakeManifest(
        name="multi-param-feature",
        models={"libraries": [], "required_parameters": ["V_IN", "V_OUT"]},
    )

    with pytest.raises(MissingParameterError) as exc_info:
        validate_required_parameters(manifest, {})

    error_msg = str(exc_info.value)
    assert_that(error_msg, contains_string("V_IN"))
    assert_that(error_msg, contains_string("V_OUT"))


def test_validate_required_parameters_error_includes_feature_name_for_multiple_missing():
    """MissingParameterError message includes feature name when multiple params are missing."""
    manifest = _FakeManifest(
        name="my-special-feature",
        models={"libraries": [], "required_parameters": ["V_IN", "V_OUT"]},
    )

    with pytest.raises(MissingParameterError) as exc_info:
        validate_required_parameters(manifest, {})

    assert_that(str(exc_info.value), contains_string("my-special-feature"))


def test_validate_required_parameters_only_reports_missing_params():
    """validate_required_parameters() reports only missing params, not the provided ones."""
    manifest = _FakeManifest(
        name="partial-feature",
        models={"libraries": [], "required_parameters": ["V_IN", "V_OUT"]},
    )

    with pytest.raises(MissingParameterError) as exc_info:
        validate_required_parameters(manifest, {"V_IN": 5.0})

    error_msg = str(exc_info.value)
    assert_that(error_msg, contains_string("V_OUT"))


# ---------------------------------------------------------------------------
# validate_required_parameters with None provided_params when params required
# ---------------------------------------------------------------------------


def test_validate_required_parameters_raises_when_none_provided_but_params_required():
    """MissingParameterError is raised when provided_params is None but params are required."""
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN"]},
    )

    with pytest.raises(MissingParameterError) as exc_info:
        validate_required_parameters(manifest, None)

    assert_that(str(exc_info.value), contains_string("V_IN"))


# ---------------------------------------------------------------------------
# validate_required_parameters importable from spice_runner
# ---------------------------------------------------------------------------


def test_validate_required_parameters_importable_from_spice_runner():
    """validate_required_parameters is importable from ci_feature.spice_runner."""
    from ci_feature.spice_runner import validate_required_parameters as vrp

    assert_that(callable(vrp), equal_to(True))


# ---------------------------------------------------------------------------
# Duplicate required parameters — de-duplicated before reporting
# ---------------------------------------------------------------------------


def test_validate_required_parameters_deduplicates_required_list():
    """Duplicate entries in required_parameters are counted only once."""
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN", "V_IN"]},
    )

    with pytest.raises(MissingParameterError) as exc_info:
        validate_required_parameters(manifest, {})

    error_msg = str(exc_info.value)
    # Should report 1 missing parameter, not 2
    assert_that(error_msg, contains_string("1 required parameter"))


def test_validate_required_parameters_passes_with_duplicate_required_when_provided():
    """Duplicate entries in required_parameters pass when the parameter is provided once."""
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": ["V_IN", "V_IN"]},
    )

    result = validate_required_parameters(manifest, {"V_IN": 5.0})

    assert_that(result, equal_to(None))
