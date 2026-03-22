"""Unit tests for the interface.yml JSON Schema."""

import json
import os
import textwrap

import jsonschema
import pytest
import yaml
from hamcrest import assert_that, contains_string, equal_to

# Resolved absolute path to the schema file.
_SCHEMA_PATH = os.path.realpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "ci",
        "schemas",
        "interface.schema.json",
    )
)

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


@pytest.fixture(scope="module")
def schema():
    """Load the interface JSON Schema once per test module."""
    with open(_SCHEMA_PATH) as f:
        return json.load(f)


def _validate(schema, yaml_text):
    """Parse *yaml_text* and validate against *schema*. Returns the parsed data."""
    data = yaml.safe_load(yaml_text)
    jsonschema.validate(instance=data, schema=schema)
    return data


def test_valid_interface_passes(schema):
    """A fully-populated valid interface.yml passes validation without error."""
    data = _validate(schema, VALID_INTERFACE_YAML)
    assert_that(data["name"], equal_to("dc-power-supply"))
    assert len(data["signals"]) == 2


def test_missing_signals_fails(schema):
    """An interface.yml with no 'signals' key fails validation."""
    yaml_text = textwrap.dedent("""\
        name: dc-power-supply
        version: "1.0.0"
    """)
    data = yaml.safe_load(yaml_text)
    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(instance=data, schema=schema)
    assert_that(str(exc_info.value), contains_string("signals"))


def test_missing_name_fails(schema):
    """An interface.yml missing 'name' fails validation."""
    yaml_text = textwrap.dedent("""\
        version: "1.0.0"
        signals:
          - name: V_OUT
            direction: output
            domain: analog
            unit: V
            description: Output voltage
    """)
    data = yaml.safe_load(yaml_text)
    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(instance=data, schema=schema)
    assert_that(str(exc_info.value), contains_string("name"))


def test_invalid_direction_fails(schema):
    """A signal with an invalid 'direction' value fails validation."""
    yaml_text = textwrap.dedent("""\
        name: dc-power-supply
        version: "1.0.0"
        signals:
          - name: V_OUT
            direction: unknown
            domain: analog
            unit: V
            description: Output voltage
    """)
    data = yaml.safe_load(yaml_text)
    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(instance=data, schema=schema)
    assert_that(str(exc_info.value), contains_string("direction"))


def test_invalid_domain_fails(schema):
    """A signal with an invalid 'domain' value fails validation."""
    yaml_text = textwrap.dedent("""\
        name: dc-power-supply
        version: "1.0.0"
        signals:
          - name: V_OUT
            direction: output
            domain: optical
            unit: V
            description: Output voltage
    """)
    data = yaml.safe_load(yaml_text)
    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(instance=data, schema=schema)
    assert_that(str(exc_info.value), contains_string("domain"))


def test_empty_signals_list_fails(schema):
    """An interface.yml with an empty 'signals' list fails validation."""
    yaml_text = textwrap.dedent("""\
        name: dc-power-supply
        version: "1.0.0"
        signals: []
    """)
    data = yaml.safe_load(yaml_text)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=schema)


def test_signal_missing_required_field_fails(schema):
    """A signal entry missing 'unit' fails validation."""
    yaml_text = textwrap.dedent("""\
        name: dc-power-supply
        version: "1.0.0"
        signals:
          - name: V_OUT
            direction: output
            domain: analog
            description: Output voltage
    """)
    data = yaml.safe_load(yaml_text)
    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(instance=data, schema=schema)
    assert_that(str(exc_info.value), contains_string("unit"))


def test_invalid_version_format_fails(schema):
    """An interface.yml with a non-semver version string fails validation."""
    yaml_text = textwrap.dedent("""\
        name: dc-power-supply
        version: "not-a-version"
        signals:
          - name: V_OUT
            direction: output
            domain: analog
            unit: V
            description: Output voltage
    """)
    data = yaml.safe_load(yaml_text)
    with pytest.raises(jsonschema.ValidationError) as exc_info:
        jsonschema.validate(instance=data, schema=schema)
    assert_that(str(exc_info.value), contains_string("version"))
