from behave import given, then, when

from ci_feature.interface import InterfaceContract, InterfaceValidationError, validate_signal_name


@given('an interface contract named "{name}" with signals "{sig1}" and "{sig2}"')
def step_create_interface_contract(context, name, sig1, sig2):
    context.interface = InterfaceContract(
        name=name,
        version="1.0.0",
        signals=[
            {
                "name": sig1,
                "direction": "output",
                "domain": "analog",
                "unit": "V",
                "description": f"{sig1} signal",
            },
            {
                "name": sig2,
                "direction": "input",
                "domain": "analog",
                "unit": "V",
                "description": f"{sig2} signal",
            },
        ],
    )


@when('the signal name "{signal_name}" is validated against the interface')
def step_validate_signal_name(context, signal_name):
    context.signal_validation_error = None
    try:
        validate_signal_name(signal_name, context.interface)
    except InterfaceValidationError as exc:
        context.signal_validation_error = exc


@then("signal validation succeeds")
def step_signal_validation_succeeds(context):
    assert context.signal_validation_error is None, (
        f"Expected signal validation to succeed but got: {context.signal_validation_error}"
    )


@then('signal validation fails mentioning "{text}"')
def step_signal_validation_fails_mentioning(context, text):
    assert context.signal_validation_error is not None, (
        "Expected signal validation to fail but it succeeded"
    )
    assert text in str(context.signal_validation_error), (
        f"Expected error message to mention '{text}', but got: {context.signal_validation_error}"
    )


@then('the error mentions the interface name "{name}"')
def step_error_mentions_interface_name(context, name):
    assert context.signal_validation_error is not None, (
        "Expected signal validation to fail but it succeeded"
    )
    assert name in str(context.signal_validation_error), (
        f"Expected error message to mention interface name '{name}', "
        f"but got: {context.signal_validation_error}"
    )


@then('the error lists the valid signal names "{sig1}" and "{sig2}"')
def step_error_lists_valid_signals(context, sig1, sig2):
    assert context.signal_validation_error is not None, (
        "Expected signal validation to fail but it succeeded"
    )
    error_msg = str(context.signal_validation_error)
    assert sig1 in error_msg, (
        f"Expected error message to list signal '{sig1}', but got: {error_msg}"
    )
    assert sig2 in error_msg, (
        f"Expected error message to list signal '{sig2}', but got: {error_msg}"
    )
