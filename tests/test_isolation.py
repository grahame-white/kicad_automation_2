"""Unit tests for ci_feature.isolation."""

import os
import textwrap

import pytest
from hamcrest import assert_that, contains_string, equal_to

import ci_feature.interface as interface_module
import ci_feature.manifest as manifest_module
from ci_feature.isolation import IsolationViolationError, validate_isolation
from ci_feature.manifest import load_manifest

# Resolved absolute paths to the schema files so pyfakefs can expose them.
_SCHEMA_REAL_PATH = os.path.realpath(manifest_module.SCHEMA_PATH)
_INTERFACE_SCHEMA_REAL_PATH = os.path.realpath(interface_module.SCHEMA_PATH)

# A fixed feature directory and manifest path inside the fake filesystem.
_FEATURE_DIR = "/repo/features/my-feature"
_MANIFEST_PATH = f"{_FEATURE_DIR}/feature.yml"
_INTERFACE_PATH = f"{_FEATURE_DIR}/interface.yml"

VALID_MANIFEST_DATA = {
    "name": "my-feature",
    "version": "1.0.0",
    "schematic": "schematic/my-feature.kicad_sch",
    "interface": "interface.yml",
    "models": {
        "libraries": ["models/component.spice"],
        "required_parameters": ["V_IN"],
    },
}

VALID_MANIFEST_YAML = textwrap.dedent("""\
    name: my-feature
    version: "1.0.0"
    schematic: schematic/my-feature.kicad_sch
    interface: interface.yml
    models:
      libraries:
        - models/component.spice
      required_parameters:
        - V_IN
""")

VALID_INTERFACE_YAML = textwrap.dedent("""\
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
""")


@pytest.fixture(autouse=True)
def clear_schema_cache():
    """Clear the schema LRU caches before and after every test for isolation."""
    manifest_module._load_schema.cache_clear()
    interface_module._load_schema.cache_clear()
    yield
    manifest_module._load_schema.cache_clear()
    interface_module._load_schema.cache_clear()


@pytest.fixture
def fake_fs(fs):
    """Fake filesystem pre-loaded with the real JSON Schemas so load_manifest() can find them."""
    fs.add_real_file(_SCHEMA_REAL_PATH, read_only=True)
    fs.add_real_file(_INTERFACE_SCHEMA_REAL_PATH, read_only=True)
    return fs


# ---------------------------------------------------------------------------
# validate_isolation() — direct unit tests
# ---------------------------------------------------------------------------


def test_valid_manifest_passes():
    """validate_isolation() does not raise for a manifest with all relative, local paths."""
    validate_isolation(_FEATURE_DIR, VALID_MANIFEST_DATA)


def test_absolute_schematic_path_fails():
    """validate_isolation() raises IsolationViolationError for an absolute schematic path."""
    data = {**VALID_MANIFEST_DATA, "schematic": "/absolute/path/my.kicad_sch"}
    with pytest.raises(IsolationViolationError) as exc_info:
        validate_isolation(_FEATURE_DIR, data)
    assert_that(str(exc_info.value), contains_string("/absolute/path/my.kicad_sch"))


def test_absolute_interface_path_fails():
    """validate_isolation() raises IsolationViolationError for an absolute interface path."""
    data = {**VALID_MANIFEST_DATA, "interface": "/absolute/interface.yml"}
    with pytest.raises(IsolationViolationError) as exc_info:
        validate_isolation(_FEATURE_DIR, data)
    assert_that(str(exc_info.value), contains_string("/absolute/interface.yml"))


def test_absolute_library_path_fails():
    """validate_isolation() raises IsolationViolationError for an absolute library path."""
    data = {
        **VALID_MANIFEST_DATA,
        "models": {
            **VALID_MANIFEST_DATA["models"],
            "libraries": ["/absolute/lib.spice"],
        },
    }
    with pytest.raises(IsolationViolationError) as exc_info:
        validate_isolation(_FEATURE_DIR, data)
    assert_that(str(exc_info.value), contains_string("/absolute/lib.spice"))


def test_dotdot_escaping_schematic_fails():
    """validate_isolation() raises IsolationViolationError for a ../ schematic path."""
    data = {**VALID_MANIFEST_DATA, "schematic": "../../shared/my.kicad_sch"}
    with pytest.raises(IsolationViolationError) as exc_info:
        validate_isolation(_FEATURE_DIR, data)
    assert_that(str(exc_info.value), contains_string("../../shared/my.kicad_sch"))


def test_dotdot_escaping_library_fails():
    """validate_isolation() raises IsolationViolationError for a ../ library path."""
    data = {
        **VALID_MANIFEST_DATA,
        "models": {
            **VALID_MANIFEST_DATA["models"],
            "libraries": ["../shared/lib.spice"],
        },
    }
    with pytest.raises(IsolationViolationError) as exc_info:
        validate_isolation(_FEATURE_DIR, data)
    assert_that(str(exc_info.value), contains_string("../shared/lib.spice"))


def test_error_message_contains_offending_path():
    """Error message includes the offending path."""
    offending = "../../etc/passwd"
    data = {**VALID_MANIFEST_DATA, "schematic": offending}
    with pytest.raises(IsolationViolationError) as exc_info:
        validate_isolation(_FEATURE_DIR, data)
    assert_that(str(exc_info.value), contains_string(offending))


def test_error_message_names_field_for_dotdot():
    """Error message names the field that contains the offending path."""
    data = {**VALID_MANIFEST_DATA, "schematic": "../../bad.kicad_sch"}
    with pytest.raises(IsolationViolationError) as exc_info:
        validate_isolation(_FEATURE_DIR, data)
    assert_that(str(exc_info.value), contains_string("schematic"))


def test_error_message_names_field_for_absolute():
    """Error message names the field that contains the absolute path."""
    data = {**VALID_MANIFEST_DATA, "interface": "/absolute/interface.yml"}
    with pytest.raises(IsolationViolationError) as exc_info:
        validate_isolation(_FEATURE_DIR, data)
    assert_that(str(exc_info.value), contains_string("interface"))


def test_error_message_explains_isolation_rule_for_absolute():
    """Error message for an absolute path explains the isolation rule."""
    data = {**VALID_MANIFEST_DATA, "schematic": "/absolute/path.kicad_sch"}
    with pytest.raises(IsolationViolationError) as exc_info:
        validate_isolation(_FEATURE_DIR, data)
    assert_that(str(exc_info.value), contains_string("relative"))


def test_error_message_suggests_fix_for_dotdot():
    """Error message for a path-escaping violation suggests removing ../ components."""
    data = {**VALID_MANIFEST_DATA, "schematic": "../../shared/my.kicad_sch"}
    with pytest.raises(IsolationViolationError) as exc_info:
        validate_isolation(_FEATURE_DIR, data)
    assert_that(str(exc_info.value), contains_string("../"))


# ---------------------------------------------------------------------------
# load_manifest() integration tests
# ---------------------------------------------------------------------------


def test_load_manifest_valid_relative_paths_pass(fake_fs):
    """load_manifest() succeeds when all paths are relative and within the feature directory."""
    fake_fs.create_dir(_FEATURE_DIR)
    fake_fs.create_file(_MANIFEST_PATH, contents=VALID_MANIFEST_YAML)
    fake_fs.create_file(_INTERFACE_PATH, contents=VALID_INTERFACE_YAML)
    manifest = load_manifest(_MANIFEST_PATH)
    assert_that(manifest.name, equal_to("my-feature"))


def test_load_manifest_raises_for_absolute_path(fake_fs):
    """load_manifest() raises IsolationViolationError for a manifest with an absolute path."""
    fake_fs.create_dir(_FEATURE_DIR)
    fake_fs.create_file(
        _MANIFEST_PATH,
        contents=textwrap.dedent("""\
            name: my-feature
            version: "1.0.0"
            schematic: /absolute/my-feature.kicad_sch
            interface: interface.yml
            models:
              libraries:
                - models/component.spice
              required_parameters:
                - V_IN
        """),
    )
    with pytest.raises(IsolationViolationError) as exc_info:
        load_manifest(_MANIFEST_PATH)
    assert_that(str(exc_info.value), contains_string("/absolute/my-feature.kicad_sch"))


def test_load_manifest_raises_for_dotdot_path(fake_fs):
    """load_manifest() raises IsolationViolationError for a manifest with a ../ path."""
    fake_fs.create_dir(_FEATURE_DIR)
    fake_fs.create_file(
        _MANIFEST_PATH,
        contents=textwrap.dedent("""\
            name: my-feature
            version: "1.0.0"
            schematic: ../../shared/my-feature.kicad_sch
            interface: interface.yml
            models:
              libraries:
                - models/component.spice
              required_parameters:
                - V_IN
        """),
    )
    with pytest.raises(IsolationViolationError) as exc_info:
        load_manifest(_MANIFEST_PATH)
    assert_that(str(exc_info.value), contains_string("../../shared/my-feature.kicad_sch"))


def test_list_interface_absolute_path_fails():
    """validate_isolation() raises IsolationViolationError for an absolute path in a list."""
    data = {**VALID_MANIFEST_DATA, "interface": ["/absolute/interface.yml"]}
    with pytest.raises(IsolationViolationError) as exc_info:
        validate_isolation(_FEATURE_DIR, data)
    assert_that(str(exc_info.value), contains_string("/absolute/interface.yml"))


def test_list_interface_dotdot_path_fails():
    """validate_isolation() raises IsolationViolationError for a ../ path in a list interface."""
    data = {**VALID_MANIFEST_DATA, "interface": ["../../shared/interface.yml"]}
    with pytest.raises(IsolationViolationError) as exc_info:
        validate_isolation(_FEATURE_DIR, data)
    assert_that(str(exc_info.value), contains_string("../../shared/interface.yml"))
