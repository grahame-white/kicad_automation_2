"""Unit tests for ci_feature.interface."""

import os
import textwrap

import pytest
from hamcrest import assert_that, contains_string, equal_to, has_length, instance_of

import ci_feature.interface as interface_module
from ci_feature.interface import InterfaceContract, InterfaceValidationError, load_interface

# Resolved absolute path to the schema file so pyfakefs can expose it.
_SCHEMA_REAL_PATH = os.path.realpath(interface_module.SCHEMA_PATH)

# A fixed path for the interface file inside the fake filesystem.
_INTERFACE_PATH = "/interface.yml"

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
    """Clear the schema LRU cache before and after every test for isolation."""
    interface_module._load_schema.cache_clear()
    yield
    interface_module._load_schema.cache_clear()


@pytest.fixture
def fake_fs(fs):
    """Fake filesystem pre-loaded with the real JSON Schema so load_interface() can find it."""
    fs.add_real_file(_SCHEMA_REAL_PATH, read_only=True)
    return fs


def test_load_valid_interface(fake_fs):
    """load_interface() returns an InterfaceContract for a valid file."""
    fake_fs.create_file(_INTERFACE_PATH, contents=VALID_INTERFACE_YAML)
    contract = load_interface(_INTERFACE_PATH)
    assert_that(contract, instance_of(InterfaceContract))
    assert_that(contract.name, equal_to("dc-power-supply"))
    assert_that(contract.version, equal_to("1.0.0"))
    assert_that(contract.signals, has_length(2))


def test_missing_interface_file_raises_file_not_found(fake_fs):
    """load_interface() raises FileNotFoundError whose message contains the missing path."""
    missing = "/nonexistent/interface.yml"
    with pytest.raises(FileNotFoundError) as exc_info:
        load_interface(missing)
    assert_that(str(exc_info.value), contains_string(missing))


def test_malformed_yaml_raises_interface_validation_error(fake_fs):
    """Malformed YAML raises InterfaceValidationError whose message mentions YAML."""
    fake_fs.create_file(_INTERFACE_PATH, contents="name: [unclosed bracket\n")
    with pytest.raises(InterfaceValidationError) as exc_info:
        load_interface(_INTERFACE_PATH)
    assert_that(str(exc_info.value), contains_string("YAML"))


def test_missing_signals_raises_interface_validation_error(fake_fs):
    """A valid YAML file missing the 'signals' key raises InterfaceValidationError."""
    fake_fs.create_file(
        _INTERFACE_PATH,
        contents=textwrap.dedent("""\
            name: dc-power-supply
            version: "1.0.0"
        """),
    )
    with pytest.raises(InterfaceValidationError) as exc_info:
        load_interface(_INTERFACE_PATH)
    assert_that(str(exc_info.value), contains_string("signals"))


def test_invalid_schema_raises_interface_validation_error(fake_fs):
    """A file with valid YAML but an invalid interface schema raises InterfaceValidationError."""
    fake_fs.create_file(
        _INTERFACE_PATH,
        contents=textwrap.dedent("""\
            name: dc-power-supply
            version: "1.0.0"
            signals:
              - name: V_OUT
                direction: unknown
                domain: analog
                unit: V
                description: Output voltage
        """),
    )
    with pytest.raises(InterfaceValidationError) as exc_info:
        load_interface(_INTERFACE_PATH)
    assert_that(str(exc_info.value), contains_string("direction"))


def test_empty_yaml_raises_interface_validation_error(fake_fs):
    """An empty YAML file (parses as None) raises InterfaceValidationError."""
    fake_fs.create_file(_INTERFACE_PATH, contents="")
    with pytest.raises(InterfaceValidationError) as exc_info:
        load_interface(_INTERFACE_PATH)
    assert_that(str(exc_info.value), contains_string("NoneType"))


def test_directory_path_raises_file_not_found(fake_fs):
    """A directory path raises FileNotFoundError rather than IsADirectoryError."""
    fake_fs.create_dir("/some-dir")
    with pytest.raises(FileNotFoundError) as exc_info:
        load_interface("/some-dir")
    assert_that(str(exc_info.value), contains_string("/some-dir"))
