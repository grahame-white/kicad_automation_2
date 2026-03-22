"""Unit tests for ci_feature.manifest."""

import textwrap

import pytest

from ci_feature.manifest import FeatureManifest, ManifestValidationError, load_manifest

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


@pytest.fixture
def valid_manifest_file(tmp_path):
    """Write a valid feature.yml to a temporary directory and return its path."""
    p = tmp_path / "feature.yml"
    p.write_text(VALID_MANIFEST_YAML)
    return str(p)


def test_load_valid_manifest(valid_manifest_file):
    """load_manifest() returns a FeatureManifest for a valid file."""
    manifest = load_manifest(valid_manifest_file)
    assert isinstance(manifest, FeatureManifest)
    assert manifest.name == "voltage-regulator"
    assert manifest.version == "1.0.0"
    assert manifest.schematic == "schematic/voltage-regulator.kicad_sch"
    assert manifest.interface == "interface.yml"
    assert manifest.models["libraries"] == ["models/ldo.spice"]
    assert manifest.models["required_parameters"] == ["V_IN", "V_OUT"]
    assert manifest.configuration == {"V_IN": 5.0}


def test_missing_required_field_name(tmp_path):
    """Missing required field 'name' raises ManifestValidationError mentioning 'name'."""
    p = tmp_path / "feature.yml"
    p.write_text(
        textwrap.dedent("""\
            version: "1.0.0"
            schematic: schematic/voltage-regulator.kicad_sch
            interface: interface.yml
            models:
              libraries:
                - models/ldo.spice
              required_parameters:
                - V_IN
        """)
    )
    with pytest.raises(ManifestValidationError) as exc_info:
        load_manifest(str(p))
    assert "name" in str(exc_info.value)


def test_missing_required_field_models(tmp_path):
    """Missing required field 'models' raises ManifestValidationError mentioning 'models'."""
    p = tmp_path / "feature.yml"
    p.write_text(
        textwrap.dedent("""\
            name: voltage-regulator
            version: "1.0.0"
            schematic: schematic/voltage-regulator.kicad_sch
            interface: interface.yml
        """)
    )
    with pytest.raises(ManifestValidationError) as exc_info:
        load_manifest(str(p))
    assert "models" in str(exc_info.value)


def test_nonexistent_file_raises_file_not_found(tmp_path):
    """load_manifest() raises FileNotFoundError with the path when file is missing."""
    missing = str(tmp_path / "nonexistent" / "feature.yml")
    with pytest.raises(FileNotFoundError) as exc_info:
        load_manifest(missing)
    assert missing in str(exc_info.value)


def test_directory_path_raises_file_not_found(tmp_path):
    """Passing a directory path raises FileNotFoundError, not IsADirectoryError."""
    with pytest.raises(FileNotFoundError) as exc_info:
        load_manifest(str(tmp_path))
    assert str(tmp_path) in str(exc_info.value)


def test_empty_yaml_raises_manifest_validation_error(tmp_path):
    """An empty YAML file (parses as None) raises ManifestValidationError."""
    p = tmp_path / "feature.yml"
    p.write_text("")
    with pytest.raises(ManifestValidationError) as exc_info:
        load_manifest(str(p))
    assert "NoneType" in str(exc_info.value)


def test_malformed_yaml_raises_manifest_validation_error(tmp_path):
    """Malformed YAML raises ManifestValidationError with a clear parse error."""
    p = tmp_path / "feature.yml"
    p.write_text("name: [unclosed bracket\n")
    with pytest.raises(ManifestValidationError) as exc_info:
        load_manifest(str(p))
    assert "YAML" in str(exc_info.value) or "parse" in str(exc_info.value).lower()


def test_optional_configuration_defaults_to_none(tmp_path):
    """A manifest without a 'configuration' block has configuration=None."""
    p = tmp_path / "feature.yml"
    p.write_text(
        textwrap.dedent("""\
            name: voltage-regulator
            version: "1.0.0"
            schematic: schematic/voltage-regulator.kicad_sch
            interface: interface.yml
            models:
              libraries:
                - models/ldo.spice
              required_parameters:
                - V_IN
        """)
    )
    manifest = load_manifest(str(p))
    assert manifest.configuration is None
