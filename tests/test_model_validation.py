"""Unit tests for ci_feature.model_validation."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest
from hamcrest import assert_that, contains_string, equal_to, instance_of

from ci_feature.model_validation import validate_model_presence
from ci_feature.spice_errors import MissingModelError

_FEATURE_DIR = "/features/voltage-regulator"


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
# All model files present — validation passes
# ---------------------------------------------------------------------------


def test_validate_model_presence_passes_when_all_files_exist(fs):
    """validate_model_presence() returns None when all libraries exist."""
    fs.create_file(f"{_FEATURE_DIR}/models/ldo.spice", contents="* ldo model\n")
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": ["models/ldo.spice"], "required_parameters": ["V_IN"]},
    )

    result = validate_model_presence(manifest, _FEATURE_DIR)

    assert_that(result, equal_to(None))


def test_validate_model_presence_passes_with_multiple_files(fs):
    """validate_model_presence() returns None when all multiple libraries exist."""
    fs.create_file(f"{_FEATURE_DIR}/models/ldo.spice", contents="* ldo\n")
    fs.create_file(f"{_FEATURE_DIR}/models/nmos.spice", contents="* nmos\n")
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={
            "libraries": ["models/ldo.spice", "models/nmos.spice"],
            "required_parameters": [],
        },
    )

    result = validate_model_presence(manifest, _FEATURE_DIR)

    assert_that(result, equal_to(None))


def test_validate_model_presence_passes_with_empty_libraries(fs):
    """validate_model_presence() returns None when libraries list is empty."""
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": [], "required_parameters": []},
    )

    result = validate_model_presence(manifest, _FEATURE_DIR)

    assert_that(result, equal_to(None))


# ---------------------------------------------------------------------------
# One model file missing — MissingModelError raised
# ---------------------------------------------------------------------------


def test_validate_model_presence_raises_when_one_file_missing(fs):
    """validate_model_presence() raises MissingModelError when one library is missing."""
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": ["models/missing.spice"], "required_parameters": []},
    )

    with pytest.raises(MissingModelError):
        validate_model_presence(manifest, _FEATURE_DIR)


def test_validate_model_presence_error_includes_feature_name(fs):
    """MissingModelError message includes the feature name."""
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": ["models/missing.spice"], "required_parameters": []},
    )

    with pytest.raises(MissingModelError) as exc_info:
        validate_model_presence(manifest, _FEATURE_DIR)

    assert_that(str(exc_info.value), contains_string("voltage-regulator"))


def test_validate_model_presence_error_includes_missing_path(fs):
    """MissingModelError message includes the full absolute path of the missing file."""
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": ["models/missing.spice"], "required_parameters": []},
    )

    with pytest.raises(MissingModelError) as exc_info:
        validate_model_presence(manifest, _FEATURE_DIR)

    missing_path = f"{_FEATURE_DIR}/models/missing.spice"
    assert_that(str(exc_info.value), contains_string(missing_path))


def test_validate_model_presence_error_is_missing_model_error(fs):
    """MissingModelError is the exact exception type raised."""
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="my-feature",
        models={"libraries": ["absent.spice"], "required_parameters": []},
    )

    with pytest.raises(MissingModelError) as exc_info:
        validate_model_presence(manifest, _FEATURE_DIR)

    assert_that(exc_info.value, instance_of(MissingModelError))


def test_validate_model_presence_not_raised_when_present_files_coexist_with_check(fs):
    """validate_model_presence() only raises for actually missing files."""
    fs.create_file(f"{_FEATURE_DIR}/models/present.spice", contents="* present\n")
    manifest = _FakeManifest(
        name="voltage-regulator",
        models={"libraries": ["models/present.spice"], "required_parameters": []},
    )

    # Should not raise — file exists
    validate_model_presence(manifest, _FEATURE_DIR)


# ---------------------------------------------------------------------------
# Multiple missing files — all paths listed in the error
# ---------------------------------------------------------------------------


def test_validate_model_presence_raises_when_multiple_files_missing(fs):
    """validate_model_presence() raises MissingModelError when multiple libraries are missing."""
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="multi-model-feature",
        models={
            "libraries": ["models/alpha.spice", "models/beta.spice", "models/gamma.spice"],
            "required_parameters": [],
        },
    )

    with pytest.raises(MissingModelError):
        validate_model_presence(manifest, _FEATURE_DIR)


def test_validate_model_presence_error_lists_all_missing_paths(fs):
    """MissingModelError message lists every missing path when multiple are absent."""
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="multi-model-feature",
        models={
            "libraries": ["models/alpha.spice", "models/beta.spice"],
            "required_parameters": [],
        },
    )

    with pytest.raises(MissingModelError) as exc_info:
        validate_model_presence(manifest, _FEATURE_DIR)

    error_msg = str(exc_info.value)
    assert_that(error_msg, contains_string("alpha.spice"))
    assert_that(error_msg, contains_string("beta.spice"))


def test_validate_model_presence_error_includes_feature_name_for_multiple_missing(fs):
    """MissingModelError message includes feature name when multiple files are missing."""
    fs.create_dir(_FEATURE_DIR)
    manifest = _FakeManifest(
        name="my-special-feature",
        models={
            "libraries": ["models/alpha.spice", "models/beta.spice"],
            "required_parameters": [],
        },
    )

    with pytest.raises(MissingModelError) as exc_info:
        validate_model_presence(manifest, _FEATURE_DIR)

    assert_that(str(exc_info.value), contains_string("my-special-feature"))


def test_validate_model_presence_only_reports_missing_files(fs):
    """validate_model_presence() reports only the missing files, not the present ones."""
    fs.create_file(f"{_FEATURE_DIR}/models/present.spice", contents="* present\n")
    manifest = _FakeManifest(
        name="partial-feature",
        models={
            "libraries": ["models/present.spice", "models/absent.spice"],
            "required_parameters": [],
        },
    )

    with pytest.raises(MissingModelError) as exc_info:
        validate_model_presence(manifest, _FEATURE_DIR)

    error_msg = str(exc_info.value)
    assert_that(error_msg, contains_string("absent.spice"))


# ---------------------------------------------------------------------------
# validate_model_presence re-exported from spice_runner
# ---------------------------------------------------------------------------


def test_validate_model_presence_importable_from_spice_runner():
    """validate_model_presence is importable from ci_feature.spice_runner."""
    from ci_feature.spice_runner import validate_model_presence as vmp

    assert_that(callable(vmp), equal_to(True))
