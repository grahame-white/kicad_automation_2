"""Unit tests for ci_feature.discovery."""

import os
import textwrap

import pytest
from hamcrest import assert_that, contains_string, empty, equal_to, has_length, instance_of

import ci_feature.manifest as manifest_module
from ci_feature.discovery import discover_features
from ci_feature.manifest import FeatureManifest, ManifestValidationError

# Resolved absolute path to the schema file so pyfakefs can expose it.
_SCHEMA_REAL_PATH = os.path.realpath(manifest_module.SCHEMA_PATH)

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
""")

VALID_MANIFEST_YAML_2 = textwrap.dedent("""\
    name: current-sensor
    version: "2.0.0"
    schematic: schematic/current-sensor.kicad_sch
    interface: interface.yml
    models:
      libraries:
        - models/amp.spice
      required_parameters:
        - I_MAX
""")

VALID_MANIFEST_YAML_3 = textwrap.dedent("""\
    name: filter-stage
    version: "1.1.0"
    schematic: schematic/filter-stage.kicad_sch
    interface: interface.yml
    models:
      libraries:
        - models/filter.spice
      required_parameters:
        - F_CUTOFF
""")


@pytest.fixture(autouse=True)
def clear_schema_cache():
    """Clear the schema LRU cache before and after every test for isolation."""
    manifest_module._load_schema.cache_clear()
    yield
    manifest_module._load_schema.cache_clear()


@pytest.fixture
def fake_fs(fs):
    """Fake filesystem pre-loaded with the real JSON Schema so load_manifest() can find it."""
    fs.add_real_file(_SCHEMA_REAL_PATH, read_only=True)
    return fs


def test_empty_repo_returns_empty_list(fake_fs):
    """discover_features() returns an empty list when no feature.yml files exist."""
    fake_fs.create_dir("/repo")
    result = discover_features("/repo")
    assert_that(result, empty())


def test_single_feature_is_discovered(fake_fs):
    """discover_features() discovers a single feature.yml and returns one manifest."""
    fake_fs.create_file(
        "/repo/features/voltage-regulator/feature.yml", contents=VALID_MANIFEST_YAML
    )
    result = discover_features("/repo")
    assert_that(result, has_length(1))
    assert_that(result[0], instance_of(FeatureManifest))
    assert_that(result[0].name, equal_to("voltage-regulator"))


def test_multiple_features_in_different_subdirectories(fake_fs):
    """discover_features() discovers all feature.yml files across subdirectories."""
    fake_fs.create_file("/repo/features/alpha/feature.yml", contents=VALID_MANIFEST_YAML)
    fake_fs.create_file("/repo/features/beta/feature.yml", contents=VALID_MANIFEST_YAML_2)
    fake_fs.create_file("/repo/features/gamma/feature.yml", contents=VALID_MANIFEST_YAML_3)
    result = discover_features("/repo")
    assert_that(result, has_length(3))


def test_discovery_order_is_deterministic(fake_fs):
    """discover_features() returns manifests sorted alphabetically by path."""
    fake_fs.create_file("/repo/features/alpha/feature.yml", contents=VALID_MANIFEST_YAML)
    fake_fs.create_file("/repo/features/beta/feature.yml", contents=VALID_MANIFEST_YAML_2)
    fake_fs.create_file("/repo/features/gamma/feature.yml", contents=VALID_MANIFEST_YAML_3)
    result = discover_features("/repo")
    names = [m.name for m in result]
    assert_that(names, equal_to(["voltage-regulator", "current-sensor", "filter-stage"]))


def test_discovery_order_matches_alpha_sort(fake_fs):
    """discover_features() returns manifests in alphabetical path order on repeated calls."""
    fake_fs.create_file("/repo/features/charlie/feature.yml", contents=VALID_MANIFEST_YAML_3)
    fake_fs.create_file("/repo/features/alpha/feature.yml", contents=VALID_MANIFEST_YAML)
    fake_fs.create_file("/repo/features/bravo/feature.yml", contents=VALID_MANIFEST_YAML_2)
    result1 = discover_features("/repo")
    result2 = discover_features("/repo")
    assert_that([m.name for m in result1], equal_to([m.name for m in result2]))
    assert_that(result1[0].name, equal_to("voltage-regulator"))
    assert_that(result1[1].name, equal_to("current-sensor"))
    assert_that(result1[2].name, equal_to("filter-stage"))


def test_directories_without_feature_yml_are_ignored(fake_fs):
    """discover_features() ignores directories that do not contain feature.yml."""
    fake_fs.create_file("/repo/features/alpha/feature.yml", contents=VALID_MANIFEST_YAML)
    fake_fs.create_file("/repo/features/no-manifest/other.yml", contents="some: data\n")
    fake_fs.create_dir("/repo/features/empty-dir")
    result = discover_features("/repo")
    assert_that(result, has_length(1))
    assert_that(result[0].name, equal_to("voltage-regulator"))


def test_nested_feature_directories_are_discovered(fake_fs):
    """discover_features() discovers feature.yml files nested at any depth."""
    fake_fs.create_file(
        "/repo/subsystems/power/features/vreg/feature.yml", contents=VALID_MANIFEST_YAML
    )
    result = discover_features("/repo")
    assert_that(result, has_length(1))
    assert_that(result[0].name, equal_to("voltage-regulator"))


def test_returns_feature_manifest_instances(fake_fs):
    """discover_features() returns FeatureManifest objects, not raw dicts."""
    fake_fs.create_file("/repo/feat/feature.yml", contents=VALID_MANIFEST_YAML)
    result = discover_features("/repo")
    assert_that(result[0], instance_of(FeatureManifest))


def test_invalid_feature_yml_raises_manifest_validation_error(fake_fs):
    """discover_features() raises ManifestValidationError for an invalid feature.yml."""
    fake_fs.create_file("/repo/bad-feature/feature.yml", contents="not_a_manifest: true\n")
    with pytest.raises(ManifestValidationError) as exc_info:
        discover_features("/repo")
    assert_that(str(exc_info.value), contains_string("Manifest validation failed"))


def test_result_names_match_manifests(fake_fs):
    """discover_features() correctly populates manifest fields from each file."""
    fake_fs.create_file("/repo/a/feature.yml", contents=VALID_MANIFEST_YAML)
    fake_fs.create_file("/repo/b/feature.yml", contents=VALID_MANIFEST_YAML_2)
    result = discover_features("/repo")
    assert_that(result, has_length(2))
    names = {m.name for m in result}
    assert_that("voltage-regulator" in names, equal_to(True))
    assert_that("current-sensor" in names, equal_to(True))
