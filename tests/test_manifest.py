"""Unit tests for ci_feature.manifest."""

import os
import textwrap

import pytest
from hamcrest import assert_that, contains_string, equal_to, instance_of, is_, none

import ci_feature.interface as interface_module
import ci_feature.manifest as manifest_module
from ci_feature.manifest import FeatureManifest, ManifestValidationError, load_manifest

# Resolved absolute path to the schema files so pyfakefs can expose them.
_SCHEMA_REAL_PATH = os.path.realpath(manifest_module.SCHEMA_PATH)
_INTERFACE_SCHEMA_REAL_PATH = os.path.realpath(interface_module.SCHEMA_PATH)

# A fixed path for the manifest inside the fake filesystem.
_MANIFEST_PATH = "/feature.yml"
_INTERFACE_PATH = "/interface.yml"

VALID_MANIFEST_YAML = textwrap.dedent("""\
    name: voltage-regulator
    version: "1.0.0"
    schematic: schematic/voltage-regulator.kicad_sch
    interface: interface.yml
    models:
      libraries:
        - models/ldo.spice
      required_parameters:
        - V_IN
        - V_OUT
    configuration:
      V_IN: 5.0
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


def test_load_valid_manifest(fake_fs):
    """load_manifest() returns a FeatureManifest for a valid file."""
    fake_fs.create_file(_MANIFEST_PATH, contents=VALID_MANIFEST_YAML)
    fake_fs.create_file(_INTERFACE_PATH, contents=VALID_INTERFACE_YAML)
    manifest = load_manifest(_MANIFEST_PATH)
    assert_that(manifest, instance_of(FeatureManifest))
    assert_that(manifest.name, equal_to("voltage-regulator"))
    assert_that(manifest.version, equal_to("1.0.0"))
    assert_that(manifest.schematic, equal_to("schematic/voltage-regulator.kicad_sch"))
    assert_that(manifest.interface, equal_to("interface.yml"))
    assert_that(manifest.models["libraries"], equal_to(["models/ldo.spice"]))
    assert_that(manifest.models["required_parameters"], equal_to(["V_IN", "V_OUT"]))
    assert_that(manifest.configuration, equal_to({"V_IN": 5.0}))


def test_missing_required_field_name(fake_fs):
    """Missing 'name' raises ManifestValidationError whose message contains 'name'."""
    fake_fs.create_file(
        _MANIFEST_PATH,
        contents=textwrap.dedent("""\
            version: "1.0.0"
            schematic: schematic/voltage-regulator.kicad_sch
            interface: interface.yml
            models:
              libraries:
                - models/ldo.spice
              required_parameters:
                - V_IN
        """),
    )
    with pytest.raises(ManifestValidationError) as exc_info:
        load_manifest(_MANIFEST_PATH)
    assert_that(str(exc_info.value), contains_string("name"))


def test_missing_required_field_models(fake_fs):
    """Missing 'models' raises ManifestValidationError whose message contains 'models'."""
    fake_fs.create_file(
        _MANIFEST_PATH,
        contents=textwrap.dedent("""\
            name: voltage-regulator
            version: "1.0.0"
            schematic: schematic/voltage-regulator.kicad_sch
            interface: interface.yml
        """),
    )
    with pytest.raises(ManifestValidationError) as exc_info:
        load_manifest(_MANIFEST_PATH)
    assert_that(str(exc_info.value), contains_string("models"))


def test_nonexistent_file_raises_file_not_found(fake_fs):
    """load_manifest() raises FileNotFoundError whose message contains the missing path."""
    missing = "/nonexistent/feature.yml"
    with pytest.raises(FileNotFoundError) as exc_info:
        load_manifest(missing)
    assert_that(str(exc_info.value), contains_string(missing))


def test_directory_path_raises_file_not_found(fake_fs):
    """A directory path raises FileNotFoundError rather than IsADirectoryError."""
    fake_fs.create_dir("/some-dir")
    with pytest.raises(FileNotFoundError) as exc_info:
        load_manifest("/some-dir")
    assert_that(str(exc_info.value), contains_string("/some-dir"))


def test_empty_yaml_raises_manifest_validation_error(fake_fs):
    """An empty YAML file (parses as None) raises ManifestValidationError."""
    fake_fs.create_file(_MANIFEST_PATH, contents="")
    with pytest.raises(ManifestValidationError) as exc_info:
        load_manifest(_MANIFEST_PATH)
    assert_that(str(exc_info.value), contains_string("NoneType"))


def test_malformed_yaml_raises_manifest_validation_error(fake_fs):
    """Malformed YAML raises ManifestValidationError whose message mentions YAML."""
    fake_fs.create_file(_MANIFEST_PATH, contents="name: [unclosed bracket\n")
    with pytest.raises(ManifestValidationError) as exc_info:
        load_manifest(_MANIFEST_PATH)
    assert_that(str(exc_info.value), contains_string("YAML"))


def test_optional_configuration_defaults_to_none(fake_fs):
    """A manifest without a 'configuration' block has configuration equal to None."""
    fake_fs.create_file(
        _MANIFEST_PATH,
        contents=textwrap.dedent("""\
            name: voltage-regulator
            version: "1.0.0"
            schematic: schematic/voltage-regulator.kicad_sch
            interface: interface.yml
            models:
              libraries:
                - models/ldo.spice
              required_parameters:
                - V_IN
        """),
    )
    fake_fs.create_file(_INTERFACE_PATH, contents=VALID_INTERFACE_YAML)
    manifest = load_manifest(_MANIFEST_PATH)
    assert_that(manifest.configuration, is_(none()))


def test_missing_interface_file_raises_manifest_validation_error(fake_fs):
    """A manifest referencing a missing interface.yml raises ManifestValidationError.

    The error message must include the feature name and the path to the missing file.
    """
    fake_fs.create_file(_MANIFEST_PATH, contents=VALID_MANIFEST_YAML)
    # Intentionally do NOT create interface.yml
    with pytest.raises(ManifestValidationError) as exc_info:
        load_manifest(_MANIFEST_PATH)
    message = str(exc_info.value)
    assert_that(message, contains_string("voltage-regulator"))
    assert_that(message, contains_string("interface.yml"))


def test_invalid_interface_file_raises_manifest_validation_error(fake_fs):
    """A manifest referencing an invalid interface.yml raises ManifestValidationError.

    The error message must include the feature name and the path to the invalid file.
    """
    fake_fs.create_file(_MANIFEST_PATH, contents=VALID_MANIFEST_YAML)
    fake_fs.create_file(
        _INTERFACE_PATH,
        contents=textwrap.dedent("""\
            name: dc-power-supply
            version: "1.0.0"
        """),
    )
    with pytest.raises(ManifestValidationError) as exc_info:
        load_manifest(_MANIFEST_PATH)
    message = str(exc_info.value)
    assert_that(message, contains_string("voltage-regulator"))
    assert_that(message, contains_string("interface.yml"))
