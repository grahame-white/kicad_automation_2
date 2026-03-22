"""Behave environment hooks for feature discovery initialisation."""

import os


def before_scenario(context, scenario):
    """Initialise feature discovery state before each scenario.

    Sets ``context.feature_root`` to the repository root so that step
    definitions can call ``discover_features(context.feature_root)`` without
    needing to know the repository layout themselves.
    """
    context.feature_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
