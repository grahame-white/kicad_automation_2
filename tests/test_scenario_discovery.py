"""Unit tests for ci_feature.scenario_discovery."""

import os
import textwrap

import pytest
from hamcrest import assert_that, empty, equal_to, has_length, instance_of

import ci_feature.interface as interface_module
import ci_feature.manifest as manifest_module
from ci_feature.manifest import FeatureManifest
from ci_feature.scenario_discovery import discover_scenarios

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
    """discover_scenarios() returns an empty list when no feature.yml files exist."""
    fake_fs.create_dir("/repo")
    result = discover_scenarios("/repo")
    assert_that(result, empty())


def test_feature_with_no_scenario_files_returns_empty_list(fake_fs):
    """discover_scenarios() returns an empty list when a feature has no .feature files."""
    fake_fs.create_file(
        "/repo/features/voltage-regulator/feature.yml", contents=VALID_MANIFEST_YAML
    )
    fake_fs.create_file(
        "/repo/features/voltage-regulator/interface.yml", contents=VALID_INTERFACE_YAML
    )
    result = discover_scenarios("/repo")
    assert_that(result, empty())


def test_single_feature_with_one_scenario_file_returns_one_pair(fake_fs):
    """discover_scenarios() returns one pair when a single feature has one .feature file."""
    fake_fs.create_file(
        "/repo/features/voltage-regulator/feature.yml", contents=VALID_MANIFEST_YAML
    )
    fake_fs.create_file(
        "/repo/features/voltage-regulator/interface.yml", contents=VALID_INTERFACE_YAML
    )
    fake_fs.create_file(
        "/repo/features/voltage-regulator/regulation.feature", contents="Feature: Regulation\n"
    )
    result = discover_scenarios("/repo")
    assert_that(result, has_length(1))
    manifest, scenario_path = result[0]
    assert_that(manifest, instance_of(FeatureManifest))
    assert_that(manifest.name, equal_to("voltage-regulator"))
    assert_that(scenario_path.name, equal_to("regulation.feature"))


def test_single_feature_with_multiple_scenario_files(fake_fs):
    """discover_scenarios() returns one pair per .feature file for a single feature."""
    fake_fs.create_file(
        "/repo/features/voltage-regulator/feature.yml", contents=VALID_MANIFEST_YAML
    )
    fake_fs.create_file(
        "/repo/features/voltage-regulator/interface.yml", contents=VALID_INTERFACE_YAML
    )
    fake_fs.create_file(
        "/repo/features/voltage-regulator/regulation.feature", contents="Feature: Regulation\n"
    )
    fake_fs.create_file(
        "/repo/features/voltage-regulator/startup.feature", contents="Feature: Startup\n"
    )
    result = discover_scenarios("/repo")
    assert_that(result, has_length(2))
    scenario_names = [pair[1].name for pair in result]
    assert_that(scenario_names, equal_to(["regulation.feature", "startup.feature"]))


def test_multiple_features_with_scenario_files_return_sorted_list(fake_fs):
    """discover_scenarios() returns all pairs sorted by (feature directory, scenario file path)."""
    fake_fs.create_file("/repo/features/alpha/feature.yml", contents=VALID_MANIFEST_YAML)
    fake_fs.create_file("/repo/features/alpha/interface.yml", contents=VALID_INTERFACE_YAML)
    fake_fs.create_file("/repo/features/alpha/scenario_b.feature", contents="Feature: Scenario B\n")
    fake_fs.create_file("/repo/features/alpha/scenario_a.feature", contents="Feature: Scenario A\n")
    fake_fs.create_file("/repo/features/beta/feature.yml", contents=VALID_MANIFEST_YAML_2)
    fake_fs.create_file("/repo/features/beta/interface.yml", contents=VALID_INTERFACE_YAML)
    fake_fs.create_file("/repo/features/beta/measure.feature", contents="Feature: Measure\n")
    result = discover_scenarios("/repo")
    assert_that(result, has_length(3))
    feature_names = [pair[0].name for pair in result]
    scenario_names = [pair[1].name for pair in result]
    assert_that(
        feature_names,
        equal_to(["voltage-regulator", "voltage-regulator", "current-sensor"]),
    )
    assert_that(
        scenario_names,
        equal_to(["scenario_a.feature", "scenario_b.feature", "measure.feature"]),
    )


def test_ordering_is_invariant_across_repeated_calls(fake_fs):
    """discover_scenarios() returns identical ordering on repeated calls (snapshot test)."""
    fake_fs.create_file("/repo/features/charlie/feature.yml", contents=VALID_MANIFEST_YAML_3)
    fake_fs.create_file("/repo/features/charlie/interface.yml", contents=VALID_INTERFACE_YAML)
    fake_fs.create_file("/repo/features/charlie/zz_last.feature", contents="Feature: ZZ Last\n")
    fake_fs.create_file("/repo/features/charlie/aa_first.feature", contents="Feature: AA First\n")
    fake_fs.create_file("/repo/features/alpha/feature.yml", contents=VALID_MANIFEST_YAML)
    fake_fs.create_file("/repo/features/alpha/interface.yml", contents=VALID_INTERFACE_YAML)
    fake_fs.create_file("/repo/features/alpha/regulation.feature", contents="Feature: Regulation\n")
    fake_fs.create_file("/repo/features/bravo/feature.yml", contents=VALID_MANIFEST_YAML_2)
    fake_fs.create_file("/repo/features/bravo/interface.yml", contents=VALID_INTERFACE_YAML)
    fake_fs.create_file("/repo/features/bravo/measure.feature", contents="Feature: Measure\n")
    result1 = discover_scenarios("/repo")
    result2 = discover_scenarios("/repo")
    assert_that(
        [(p[0].name, p[1].name) for p in result1],
        equal_to([(p[0].name, p[1].name) for p in result2]),
    )
    # Snapshot: explicit expected ordering (alpha < bravo < charlie, then by scenario name)
    expected = [
        ("voltage-regulator", "regulation.feature"),
        ("current-sensor", "measure.feature"),
        ("filter-stage", "aa_first.feature"),
        ("filter-stage", "zz_last.feature"),
    ]
    assert_that(
        [(p[0].name, p[1].name) for p in result1],
        equal_to(expected),
    )


def test_nested_feature_directory_scenarios_are_not_attributed_to_parent(fake_fs):
    """Scenarios in nested feature directories are attributed to their own manifest.

    When a feature directory contains a subdirectory that is itself a feature
    (i.e. it has its own ``feature.yml``), scenario discovery must not walk
    into that subdirectory while processing the parent feature.  Each set of
    scenarios should be paired only with the manifest that owns them.
    """
    # Parent feature.
    fake_fs.create_file("/repo/features/parent/feature.yml", contents=VALID_MANIFEST_YAML)
    fake_fs.create_file("/repo/features/parent/interface.yml", contents=VALID_INTERFACE_YAML)
    fake_fs.create_file(
        "/repo/features/parent/parent.feature",
        contents="Feature: Parent Scenario\n",
    )

    # Nested feature inside the parent feature directory.
    fake_fs.create_file("/repo/features/parent/nested/feature.yml", contents=VALID_MANIFEST_YAML_2)
    fake_fs.create_file("/repo/features/parent/nested/interface.yml", contents=VALID_INTERFACE_YAML)
    fake_fs.create_file(
        "/repo/features/parent/nested/child.feature",
        contents="Feature: Child Scenario\n",
    )

    result = discover_scenarios("/repo")

    # Ensure that the scenarios are associated with the correct manifests.
    name_pairs = sorted((manifest.name, path.name) for manifest, path in result)
    expected = sorted(
        [
            ("voltage-regulator", "parent.feature"),
            ("current-sensor", "child.feature"),
        ]
    )
    assert_that(name_pairs, equal_to(expected))


def test_each_pair_contains_feature_manifest_and_path(fake_fs):
    """discover_scenarios() returns (FeatureManifest, Path) tuples."""
    from pathlib import Path

    fake_fs.create_file(
        "/repo/features/voltage-regulator/feature.yml", contents=VALID_MANIFEST_YAML
    )
    fake_fs.create_file(
        "/repo/features/voltage-regulator/interface.yml", contents=VALID_INTERFACE_YAML
    )
    fake_fs.create_file(
        "/repo/features/voltage-regulator/regulation.feature", contents="Feature: Regulation\n"
    )
    result = discover_scenarios("/repo")
    assert_that(result, has_length(1))
    manifest, scenario_path = result[0]
    assert_that(manifest, instance_of(FeatureManifest))
    assert_that(scenario_path, instance_of(Path))
