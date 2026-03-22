Feature: feature.yml schema validation
  @schema
  Scenario: A valid feature.yml passes validation
    Given the feature manifest schema is loaded
    When a valid feature manifest is validated
    Then validation succeeds

  @schema
  Scenario: A feature.yml missing the required name field fails validation
    Given the feature manifest schema is loaded
    When a feature manifest missing the name field is validated
    Then validation fails with a clear error mentioning "name"

  @schema
  Scenario: A feature.yml missing the required models field fails validation
    Given the feature manifest schema is loaded
    When a feature manifest missing the models field is validated
    Then validation fails with a clear error mentioning "models"
