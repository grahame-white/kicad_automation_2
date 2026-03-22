"""Unit tests for validate_signal_name in ci_feature.interface."""

import pytest
from hamcrest import assert_that, contains_string

from ci_feature.interface import InterfaceContract, InterfaceValidationError, validate_signal_name

_SAMPLE_INTERFACE = InterfaceContract(
    name="dc-power-supply",
    version="1.0.0",
    signals=[
        {
            "name": "V_OUT",
            "direction": "output",
            "domain": "analog",
            "unit": "V",
            "description": "Output voltage",
        },
        {
            "name": "GND",
            "direction": "input",
            "domain": "analog",
            "unit": "V",
            "description": "Ground reference",
        },
    ],
)


def test_declared_signal_passes_validation():
    """validate_signal_name() does not raise for a declared signal."""
    validate_signal_name("V_OUT", _SAMPLE_INTERFACE)  # should not raise


def test_another_declared_signal_passes_validation():
    """validate_signal_name() does not raise for any declared signal."""
    validate_signal_name("GND", _SAMPLE_INTERFACE)  # should not raise


def test_undeclared_signal_raises_interface_validation_error():
    """validate_signal_name() raises InterfaceValidationError for an undeclared signal."""
    with pytest.raises(InterfaceValidationError):
        validate_signal_name("NET001", _SAMPLE_INTERFACE)


def test_error_message_includes_invalid_signal_name():
    """Error message includes the invalid signal name."""
    with pytest.raises(InterfaceValidationError) as exc_info:
        validate_signal_name("NET001", _SAMPLE_INTERFACE)
    assert_that(str(exc_info.value), contains_string("NET001"))


def test_error_message_includes_feature_name():
    """Error message includes the interface/feature name."""
    with pytest.raises(InterfaceValidationError) as exc_info:
        validate_signal_name("NET001", _SAMPLE_INTERFACE)
    assert_that(str(exc_info.value), contains_string("dc-power-supply"))


def test_error_message_lists_valid_signal_names():
    """Error message lists all valid signal names."""
    with pytest.raises(InterfaceValidationError) as exc_info:
        validate_signal_name("NET001", _SAMPLE_INTERFACE)
    assert_that(str(exc_info.value), contains_string("V_OUT"))
    assert_that(str(exc_info.value), contains_string("GND"))
