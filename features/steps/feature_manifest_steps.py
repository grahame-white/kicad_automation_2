import json
import os

import jsonschema
from behave import given, then, when

SCHEMA_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "ci",
    "schemas",
    "feature.schema.json",
)

VALID_MANIFEST = {
    "name": "voltage-regulator",
    "version": "1.0.0",
    "schematic": "schematic/voltage-regulator.kicad_sch",
    "interface": "interface.yml",
    "models": {
        "libraries": ["models/ldo.spice"],
        "required_parameters": ["V_IN", "V_OUT"],
    },
    "configuration": {
        "V_IN": 5.0,
    },
}


@given("the feature manifest schema is loaded")
def step_load_schema(context):
    with open(SCHEMA_PATH) as f:
        context.schema = json.load(f)


@when("a valid feature manifest is validated")
def step_validate_valid_manifest(context):
    context.manifest = VALID_MANIFEST.copy()
    context.validation_error = None
    try:
        jsonschema.validate(instance=context.manifest, schema=context.schema)
    except jsonschema.ValidationError as exc:
        context.validation_error = exc


@when("a feature manifest missing the name field is validated")
def step_validate_missing_name(context):
    context.manifest = {k: v for k, v in VALID_MANIFEST.items() if k != "name"}
    context.validation_error = None
    try:
        jsonschema.validate(instance=context.manifest, schema=context.schema)
    except jsonschema.ValidationError as exc:
        context.validation_error = exc


@when("a feature manifest missing the models field is validated")
def step_validate_missing_models(context):
    context.manifest = {k: v for k, v in VALID_MANIFEST.items() if k != "models"}
    context.validation_error = None
    try:
        jsonschema.validate(instance=context.manifest, schema=context.schema)
    except jsonschema.ValidationError as exc:
        context.validation_error = exc


@then("validation succeeds")
def step_validation_succeeds(context):
    assert context.validation_error is None, (
        f"Expected validation to succeed but got: {context.validation_error}"
    )


@then('validation fails with a clear error mentioning "{field}"')
def step_validation_fails_mentioning(context, field):
    assert context.validation_error is not None, (
        "Expected validation to fail but it succeeded"
    )
    assert field in str(context.validation_error.message), (
        f"Expected error message to mention '{field}', "
        f"but got: {context.validation_error.message}"
    )
