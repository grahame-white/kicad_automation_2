"""Unit tests for ci.generate_matrix."""

import json
import os
import textwrap

import pytest
from hamcrest import assert_that, contains_string, empty, equal_to, has_length

import ci_feature.interface as interface_module
import ci_feature.manifest as manifest_module
from ci.generate_matrix import generate_matrix

# Resolved absolute paths to the schema files so pyfakefs can expose them.
_SCHEMA_REAL_PATH = os.path.realpath(manifest_module.SCHEMA_PATH)
_INTERFACE_SCHEMA_REAL_PATH = os.path.realpath(interface_module.SCHEMA_PATH)

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


def test_empty_repo_returns_empty_list(fake_fs):
    """generate_matrix() returns an empty list when no feature.yml files exist."""
    fake_fs.create_dir("/repo")
    result = generate_matrix("/repo")
    assert_that(result, empty())


def test_single_feature_returns_single_path(fake_fs):
    """generate_matrix() returns one relative path for a single feature."""
    fake_fs.create_file(
        "/repo/features/voltage-regulator/feature.yml", contents=VALID_MANIFEST_YAML
    )
    fake_fs.create_file(
        "/repo/features/voltage-regulator/interface.yml", contents=VALID_INTERFACE_YAML
    )
    result = generate_matrix("/repo")
    assert_that(result, has_length(1))
    assert_that(result[0], equal_to("features/voltage-regulator"))


def test_multiple_features_return_sorted_paths(fake_fs):
    """generate_matrix() returns all feature dirs as relative paths, sorted."""
    fake_fs.create_file("/repo/features/alpha/feature.yml", contents=VALID_MANIFEST_YAML)
    fake_fs.create_file("/repo/features/alpha/interface.yml", contents=VALID_INTERFACE_YAML)
    fake_fs.create_file("/repo/features/beta/feature.yml", contents=VALID_MANIFEST_YAML_2)
    fake_fs.create_file("/repo/features/beta/interface.yml", contents=VALID_INTERFACE_YAML)
    fake_fs.create_file("/repo/features/gamma/feature.yml", contents=VALID_MANIFEST_YAML_3)
    fake_fs.create_file("/repo/features/gamma/interface.yml", contents=VALID_INTERFACE_YAML)
    result = generate_matrix("/repo")
    assert_that(result, has_length(3))
    assert_that(result, equal_to(["features/alpha", "features/beta", "features/gamma"]))
    assert_that(result, equal_to(sorted(result)))


def test_result_is_json_serialisable(fake_fs):
    """generate_matrix() output can be round-tripped through json.dumps / json.loads."""
    fake_fs.create_file(
        "/repo/features/voltage-regulator/feature.yml", contents=VALID_MANIFEST_YAML
    )
    fake_fs.create_file(
        "/repo/features/voltage-regulator/interface.yml", contents=VALID_INTERFACE_YAML
    )
    result = generate_matrix("/repo")
    serialised = json.dumps(result)
    assert_that(json.loads(serialised), equal_to(result))


def test_paths_are_relative_to_root(fake_fs):
    """generate_matrix() returns paths relative to the given root, not absolute."""
    fake_fs.create_file(
        "/repo/features/voltage-regulator/feature.yml", contents=VALID_MANIFEST_YAML
    )
    fake_fs.create_file(
        "/repo/features/voltage-regulator/interface.yml", contents=VALID_INTERFACE_YAML
    )
    result = generate_matrix("/repo")
    assert_that(result, has_length(1))
    # Must be a relative path, not absolute.
    assert_that(result[0].startswith("/"), equal_to(False))
    assert_that(result[0], contains_string("voltage-regulator"))


def test_paths_use_forward_slashes(fake_fs):
    """generate_matrix() always uses forward-slash separators in returned paths."""
    fake_fs.create_file(
        "/repo/nested/features/voltage-regulator/feature.yml", contents=VALID_MANIFEST_YAML
    )
    fake_fs.create_file(
        "/repo/nested/features/voltage-regulator/interface.yml", contents=VALID_INTERFACE_YAML
    )
    result = generate_matrix("/repo")
    assert_that(result, has_length(1))
    assert_that("\\" in result[0], equal_to(False))


def test_ordering_is_deterministic_across_calls(fake_fs):
    """generate_matrix() returns identical ordering on repeated calls."""
    fake_fs.create_file("/repo/features/charlie/feature.yml", contents=VALID_MANIFEST_YAML_3)
    fake_fs.create_file("/repo/features/charlie/interface.yml", contents=VALID_INTERFACE_YAML)
    fake_fs.create_file("/repo/features/alpha/feature.yml", contents=VALID_MANIFEST_YAML)
    fake_fs.create_file("/repo/features/alpha/interface.yml", contents=VALID_INTERFACE_YAML)
    fake_fs.create_file("/repo/features/bravo/feature.yml", contents=VALID_MANIFEST_YAML_2)
    fake_fs.create_file("/repo/features/bravo/interface.yml", contents=VALID_INTERFACE_YAML)
    result1 = generate_matrix("/repo")
    result2 = generate_matrix("/repo")
    assert_that(result1, equal_to(result2))
