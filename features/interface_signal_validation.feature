Feature: Interface-only observability

  Scenarios may only reference signals that are declared in the feature's
  interface contract.  Referencing an internal net that is not declared in
  the interface must fail fast with a clear, actionable error message.

  @schema
  Scenario: A signal declared in the interface passes validation
    Given an interface contract named "dc-power-supply" with signals "V_OUT" and "GND"
    When the signal name "V_OUT" is validated against the interface
    Then signal validation succeeds

  @schema
  Scenario: An undeclared signal fails validation with a clear error
    Given an interface contract named "dc-power-supply" with signals "V_OUT" and "GND"
    When the signal name "NET001" is validated against the interface
    Then signal validation fails mentioning "NET001"
    And the error mentions the interface name "dc-power-supply"
    And the error lists the valid signal names "V_OUT" and "GND"
