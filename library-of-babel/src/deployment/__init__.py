"""
Azure deployment building blocks for the Library of Babel.

This package provides Python dataclasses and helpers that generate Azure
Resource Manager (ARM) templates for one-click deployment to Azure.
"""

from .arm_template import (
    ArmParameter,
    ArmResource,
    AppServicePlanResource,
    WebAppResource,
    ContainerRegistryResource,
    ArmTemplate,
    build_library_template,
)

__all__ = [
    "ArmParameter",
    "ArmResource",
    "AppServicePlanResource",
    "WebAppResource",
    "ContainerRegistryResource",
    "ArmTemplate",
    "build_library_template",
]
