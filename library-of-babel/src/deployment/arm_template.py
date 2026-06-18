"""
ARM template building blocks for deploying the Library of Babel on Azure.

This module provides Python dataclasses that model the core components of an
Azure Resource Manager (ARM) deployment template.  Call
``build_library_template()`` to get a ready-to-use template, or compose
individual resource classes to build a custom one.

One-click deployment
--------------------
Once the ARM template has been pushed to a public URL (e.g. the repository's
``main`` branch on GitHub), point the Azure Portal quick-deploy button at it:

    https://portal.azure.com/#create/Microsoft.Template/uri/<url-encoded-raw-url>

See ``arm/azuredeploy.json`` for the pre-generated template.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Parameter
# ---------------------------------------------------------------------------

@dataclass
class ArmParameter:
    """
    Represents a single ARM template parameter declaration.

    Attributes:
        type: ARM type string (``string``, ``int``, ``bool``, ``securestring``,
              ``object``, ``array``).
        default_value: Optional default value for the parameter.
        allowed_values: Optional list of permitted values.
        description: Human-readable description surfaced in the portal.
    """

    type: str
    default_value: Any = None
    allowed_values: Optional[List[Any]] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to the ARM JSON parameter object."""
        result: Dict[str, Any] = {"type": self.type}
        if self.default_value is not None:
            result["defaultValue"] = self.default_value
        if self.allowed_values:
            result["allowedValues"] = self.allowed_values
        if self.description:
            result["metadata"] = {"description": self.description}
        return result


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@dataclass
class ArmResource:
    """
    Base representation of an ARM resource.

    Attributes:
        resource_type: Full ARM resource type, e.g. ``Microsoft.Web/sites``.
        api_version: ARM API version string, e.g. ``2022-03-01``.
        name: Resource name expression (may contain ARM functions).
        location: Azure region expression (defaults to the resource-group
                  location parameter).
        properties: Resource-specific properties dictionary.
        depends_on: List of resource ID expressions that must exist first.
        tags: Key/value tags applied to the resource.
    """

    resource_type: str
    api_version: str
    name: str
    location: str = "[parameters('location')]"
    properties: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to the ARM JSON resource object."""
        result: Dict[str, Any] = {
            "type": self.resource_type,
            "apiVersion": self.api_version,
            "name": self.name,
            "location": self.location,
        }
        if self.tags:
            result["tags"] = self.tags
        if self.depends_on:
            result["dependsOn"] = self.depends_on
        result["properties"] = self.properties
        return result


@dataclass
class AppServicePlanResource(ArmResource):
    """
    ARM resource for an Azure App Service Plan (Linux).

    Attributes:
        sku: SKU object, e.g. ``{"name": "B1"}``.
        kind: Resource kind — defaults to ``"linux"``.
    """

    sku: Dict[str, Any] = field(default_factory=dict)
    kind: str = "linux"

    def __post_init__(self) -> None:
        if not self.sku:
            self.sku = {"name": "[parameters('appServicePlanSku')]"}
        # Linux plans require reserved=True
        if "reserved" not in self.properties:
            self.properties["reserved"] = True

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["sku"] = self.sku
        result["kind"] = self.kind
        return result


@dataclass
class WebAppResource(ArmResource):
    """
    ARM resource for an Azure Web App (App Service) running a container.

    Attributes:
        kind: Resource kind — defaults to ``"app,linux,container"``.
    """

    kind: str = "app,linux,container"

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["kind"] = self.kind
        return result


@dataclass
class ContainerRegistryResource(ArmResource):
    """
    ARM resource for an Azure Container Registry.

    Attributes:
        sku: SKU object, e.g. ``{"name": "Basic"}``.
        admin_user_enabled: Whether the admin user credential is enabled.
    """

    sku: Dict[str, Any] = field(default_factory=dict)
    admin_user_enabled: bool = True

    def __post_init__(self) -> None:
        if not self.sku:
            self.sku = {"name": "Basic"}
        self.properties.setdefault("adminUserEnabled", self.admin_user_enabled)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result["sku"] = self.sku
        return result


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

@dataclass
class ArmTemplate:
    """
    A complete Azure Resource Manager deployment template.

    Compose a template by calling the ``add_*`` helpers, then serialise it
    with :meth:`to_dict` or :meth:`to_json`.

    Attributes:
        parameters: Mapping of parameter name → :class:`ArmParameter`.
        variables: Mapping of variable name → ARM expression/value.
        resources: Ordered list of :class:`ArmResource` objects.
        outputs: Mapping of output name → ARM output object.
        content_version: Template version string (default ``"1.0.0.0"``).
        schema: ``$schema`` URL for the ARM deployment template.
    """

    parameters: Dict[str, ArmParameter] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    resources: List[ArmResource] = field(default_factory=list)
    outputs: Dict[str, Any] = field(default_factory=dict)
    content_version: str = "1.0.0.0"
    schema: str = (
        "https://schema.management.azure.com/schemas/"
        "2019-04-01/deploymentTemplate.json#"
    )

    # ------------------------------------------------------------------
    # Builder helpers
    # ------------------------------------------------------------------

    def add_parameter(self, name: str, param: ArmParameter) -> "ArmTemplate":
        """Add a parameter declaration and return *self* for chaining."""
        self.parameters[name] = param
        return self

    def add_variable(self, name: str, value: Any) -> "ArmTemplate":
        """Add a variable and return *self* for chaining."""
        self.variables[name] = value
        return self

    def add_resource(self, resource: ArmResource) -> "ArmTemplate":
        """Append a resource and return *self* for chaining."""
        self.resources.append(resource)
        return self

    def add_output(
        self, name: str, output_type: str, value: Any
    ) -> "ArmTemplate":
        """Add an output declaration and return *self* for chaining."""
        self.outputs[name] = {"type": output_type, "value": value}
        return self

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return the template as a plain Python dictionary."""
        return {
            "$schema": self.schema,
            "contentVersion": self.content_version,
            "parameters": {
                name: param.to_dict()
                for name, param in self.parameters.items()
            },
            "variables": self.variables,
            "resources": [r.to_dict() for r in self.resources],
            "outputs": self.outputs,
        }

    def to_json(self, indent: int = 2) -> str:
        """Return the template as a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------

    def has_parameter(self, name: str) -> bool:
        """Return ``True`` if a parameter with *name* is declared."""
        return name in self.parameters

    def has_resource_type(self, resource_type: str) -> bool:
        """Return ``True`` if at least one resource of *resource_type* exists."""
        return any(r.resource_type == resource_type for r in self.resources)

    def get_resources_by_type(self, resource_type: str) -> List[ArmResource]:
        """Return all resources whose ``resource_type`` matches."""
        return [r for r in self.resources if r.resource_type == resource_type]


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def build_library_template() -> ArmTemplate:
    """
    Build a complete ARM template for the Library of Babel application.

    The template deploys:

    * An **App Service Plan** (Linux, configurable SKU)
    * A **Web App for Containers** referencing the configured Docker image

    Parameters exposed in the template allow the caller to supply:

    * ``appName`` — base name for all resources
    * ``location`` — Azure region
    * ``appServicePlanSku`` — App Service Plan tier (default ``B1``)
    * ``dockerImage`` — Docker image to run (default ``nginx:latest``)
    * ``dockerRegistryServer`` — registry URL
    * ``dockerRegistryUsername`` / ``dockerRegistryPassword`` — credentials

    Returns:
        A fully configured :class:`ArmTemplate` instance.
    """
    template = ArmTemplate()

    # ------------------------------------------------------------------
    # Parameters
    # ------------------------------------------------------------------
    (
        template
        .add_parameter("appName", ArmParameter(
            type="string",
            default_value="library-of-babel",
            description="Base name used for all Azure resources.",
        ))
        .add_parameter("location", ArmParameter(
            type="string",
            default_value="[resourceGroup().location]",
            description="Azure region for all resources.",
        ))
        .add_parameter("appServicePlanSku", ArmParameter(
            type="string",
            default_value="B1",
            allowed_values=["F1", "B1", "B2", "B3", "S1", "S2", "S3"],
            description="App Service Plan pricing tier.",
        ))
        .add_parameter("dockerImage", ArmParameter(
            type="string",
            default_value="nginx:latest",
            description=(
                "Docker image to deploy, e.g. "
                "myregistry.azurecr.io/library-of-babel:latest"
            ),
        ))
        .add_parameter("dockerRegistryServer", ArmParameter(
            type="string",
            default_value="https://index.docker.io",
            description="Docker registry server URL.",
        ))
        .add_parameter("dockerRegistryUsername", ArmParameter(
            type="string",
            default_value="",
            description="Docker registry username (leave empty for public images).",
        ))
        .add_parameter("dockerRegistryPassword", ArmParameter(
            type="securestring",
            default_value="",
            description="Docker registry password (leave empty for public images).",
        ))
    )

    # ------------------------------------------------------------------
    # Variables
    # ------------------------------------------------------------------
    (
        template
        .add_variable(
            "appServicePlanName",
            "[concat(parameters('appName'), '-plan')]",
        )
        .add_variable(
            "webAppName",
            "[concat(parameters('appName'), '-app')]",
        )
    )

    # ------------------------------------------------------------------
    # Resources
    # ------------------------------------------------------------------
    plan = AppServicePlanResource(
        resource_type="Microsoft.Web/serverfarms",
        api_version="2022-03-01",
        name="[variables('appServicePlanName')]",
        sku={"name": "[parameters('appServicePlanSku')]"},
        kind="linux",
        properties={"reserved": True},
        tags={"application": "library-of-babel"},
    )
    template.add_resource(plan)

    webapp = WebAppResource(
        resource_type="Microsoft.Web/sites",
        api_version="2022-03-01",
        name="[variables('webAppName')]",
        kind="app,linux,container",
        depends_on=[
            "[resourceId('Microsoft.Web/serverfarms',"
            " variables('appServicePlanName'))]"
        ],
        properties={
            "serverFarmId": (
                "[resourceId('Microsoft.Web/serverfarms',"
                " variables('appServicePlanName'))]"
            ),
            "siteConfig": {
                "linuxFxVersion": (
                    "[concat('DOCKER|', parameters('dockerImage'))]"
                ),
                "appSettings": [
                    {
                        "name": "WEBSITES_PORT",
                        "value": "8000",
                    },
                    {
                        "name": "DOCKER_REGISTRY_SERVER_URL",
                        "value": "[parameters('dockerRegistryServer')]",
                    },
                    {
                        "name": "DOCKER_REGISTRY_SERVER_USERNAME",
                        "value": "[parameters('dockerRegistryUsername')]",
                    },
                    {
                        "name": "DOCKER_REGISTRY_SERVER_PASSWORD",
                        "value": "[parameters('dockerRegistryPassword')]",
                    },
                    {
                        "name": "ENVIRONMENT",
                        "value": "production",
                    },
                    {
                        "name": "DEBUG",
                        "value": "false",
                    },
                    {
                        "name": "CACHE_BACKEND",
                        "value": "memory",
                    },
                ],
            },
            "httpsOnly": True,
        },
        tags={"application": "library-of-babel"},
    )
    template.add_resource(webapp)

    # ------------------------------------------------------------------
    # Outputs
    # ------------------------------------------------------------------
    (
        template
        .add_output(
            "webAppUrl",
            "string",
            "[concat('https://', variables('webAppName'), '.azurewebsites.net')]",
        )
        .add_output(
            "webAppName",
            "string",
            "[variables('webAppName')]",
        )
        .add_output(
            "appServicePlanName",
            "string",
            "[variables('appServicePlanName')]",
        )
    )

    return template
