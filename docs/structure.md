# Repository Structure

This document describes the purpose of each top-level directory in this repository.

## `features/`

Contains BDD (Behaviour-Driven Development) feature files written in Gherkin syntax. These files describe the expected behaviour of the KiCad automation in plain language.

### `features/steps/`

Contains the Python step-definition files that implement the Gherkin steps declared in the feature files.

## `schematics/`

Contains KiCad schematic files (`.kicad_sch`) used as inputs for automation, testing, and example workflows.

## `ci/`

Contains continuous-integration helper scripts and configuration files (e.g. shell scripts, Docker configuration) that support the CI pipeline but are not GitHub Actions workflow definitions.

## `docs/`

Contains project documentation, including this structure guide and any additional design notes or user guides.

## `.github/`

Contains GitHub-specific configuration: issue templates, pull-request templates, and GitHub Actions workflow definitions that drive the CI/CD pipeline.
