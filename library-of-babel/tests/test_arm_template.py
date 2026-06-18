"""
Tests for the ARM template building blocks.

This module verifies that the ARM template dataclasses serialise correctly
and that ``build_library_template()`` produces a complete, valid deployment
template.
"""

import json

import pytest

from src.deployment.arm_template import (
    ArmParameter,
    ArmResource,
    AppServicePlanResource,
    WebAppResource,
    ContainerRegistryResource,
    ArmTemplate,
    build_library_template,
)


# ---------------------------------------------------------------------------
# ArmParameter
# ---------------------------------------------------------------------------

class TestArmParameter:
    """Tests for ArmParameter serialisation."""

    def test_minimal_parameter(self):
        """A parameter with only a type serialises correctly."""
        param = ArmParameter(type="string")
        d = param.to_dict()
        assert d == {"type": "string"}

    def test_parameter_with_default(self):
        param = ArmParameter(type="int", default_value=3)
        d = param.to_dict()
        assert d["defaultValue"] == 3

    def test_parameter_with_allowed_values(self):
        param = ArmParameter(type="string", allowed_values=["B1", "B2", "S1"])
        d = param.to_dict()
        assert d["allowedValues"] == ["B1", "B2", "S1"]

    def test_parameter_with_description(self):
        param = ArmParameter(type="string", description="App name")
        d = param.to_dict()
        assert d["metadata"]["description"] == "App name"

    def test_parameter_secure_string(self):
        param = ArmParameter(type="securestring", default_value="")
        d = param.to_dict()
        assert d["type"] == "securestring"
        assert d["defaultValue"] == ""

    def test_none_defaults_omitted(self):
        """Fields that are None must not appear in the output dict."""
        param = ArmParameter(type="bool")
        d = param.to_dict()
        assert "defaultValue" not in d
        assert "allowedValues" not in d
        assert "metadata" not in d


# ---------------------------------------------------------------------------
# ArmResource
# ---------------------------------------------------------------------------

class TestArmResource:
    """Tests for ArmResource serialisation."""

    def test_minimal_resource(self):
        res = ArmResource(
            resource_type="Microsoft.Web/serverfarms",
            api_version="2022-03-01",
            name="myPlan",
        )
        d = res.to_dict()
        assert d["type"] == "Microsoft.Web/serverfarms"
        assert d["apiVersion"] == "2022-03-01"
        assert d["name"] == "myPlan"
        assert d["location"] == "[parameters('location')]"
        assert d["properties"] == {}

    def test_resource_with_depends_on(self):
        res = ArmResource(
            resource_type="Microsoft.Web/sites",
            api_version="2022-03-01",
            name="myApp",
            depends_on=["[resourceId('Microsoft.Web/serverfarms', 'myPlan')]"],
        )
        d = res.to_dict()
        assert "dependsOn" in d
        assert len(d["dependsOn"]) == 1

    def test_resource_with_tags(self):
        res = ArmResource(
            resource_type="Microsoft.Web/sites",
            api_version="2022-03-01",
            name="myApp",
            tags={"env": "prod"},
        )
        d = res.to_dict()
        assert d["tags"] == {"env": "prod"}

    def test_resource_empty_depends_on_omitted(self):
        res = ArmResource(
            resource_type="Microsoft.Web/sites",
            api_version="2022-03-01",
            name="myApp",
        )
        d = res.to_dict()
        assert "dependsOn" not in d

    def test_resource_empty_tags_omitted(self):
        res = ArmResource(
            resource_type="Microsoft.Web/sites",
            api_version="2022-03-01",
            name="myApp",
        )
        d = res.to_dict()
        assert "tags" not in d


# ---------------------------------------------------------------------------
# AppServicePlanResource
# ---------------------------------------------------------------------------

class TestAppServicePlanResource:
    """Tests for AppServicePlanResource."""

    def test_default_sku_and_kind(self):
        plan = AppServicePlanResource(
            resource_type="Microsoft.Web/serverfarms",
            api_version="2022-03-01",
            name="myPlan",
        )
        d = plan.to_dict()
        assert d["kind"] == "linux"
        assert "name" in d["sku"]
        assert d["properties"]["reserved"] is True

    def test_custom_sku(self):
        plan = AppServicePlanResource(
            resource_type="Microsoft.Web/serverfarms",
            api_version="2022-03-01",
            name="myPlan",
            sku={"name": "S2"},
        )
        d = plan.to_dict()
        assert d["sku"]["name"] == "S2"

    def test_reserved_always_set(self):
        plan = AppServicePlanResource(
            resource_type="Microsoft.Web/serverfarms",
            api_version="2022-03-01",
            name="myPlan",
        )
        assert plan.to_dict()["properties"]["reserved"] is True


# ---------------------------------------------------------------------------
# WebAppResource
# ---------------------------------------------------------------------------

class TestWebAppResource:
    """Tests for WebAppResource."""

    def test_default_kind(self):
        app = WebAppResource(
            resource_type="Microsoft.Web/sites",
            api_version="2022-03-01",
            name="myApp",
        )
        d = app.to_dict()
        assert d["kind"] == "app,linux,container"

    def test_custom_properties(self):
        app = WebAppResource(
            resource_type="Microsoft.Web/sites",
            api_version="2022-03-01",
            name="myApp",
            properties={"httpsOnly": True},
        )
        assert app.to_dict()["properties"]["httpsOnly"] is True


# ---------------------------------------------------------------------------
# ContainerRegistryResource
# ---------------------------------------------------------------------------

class TestContainerRegistryResource:
    """Tests for ContainerRegistryResource."""

    def test_default_sku(self):
        acr = ContainerRegistryResource(
            resource_type="Microsoft.ContainerRegistry/registries",
            api_version="2023-07-01",
            name="myRegistry",
        )
        d = acr.to_dict()
        assert d["sku"]["name"] == "Basic"

    def test_admin_user_enabled_in_properties(self):
        acr = ContainerRegistryResource(
            resource_type="Microsoft.ContainerRegistry/registries",
            api_version="2023-07-01",
            name="myRegistry",
        )
        assert acr.to_dict()["properties"]["adminUserEnabled"] is True

    def test_admin_user_disabled(self):
        acr = ContainerRegistryResource(
            resource_type="Microsoft.ContainerRegistry/registries",
            api_version="2023-07-01",
            name="myRegistry",
            admin_user_enabled=False,
        )
        assert acr.to_dict()["properties"]["adminUserEnabled"] is False


# ---------------------------------------------------------------------------
# ArmTemplate
# ---------------------------------------------------------------------------

class TestArmTemplate:
    """Tests for ArmTemplate composition and serialisation."""

    def test_empty_template_valid_json(self):
        t = ArmTemplate()
        output = json.loads(t.to_json())
        assert output["$schema"].startswith("https://schema.management.azure.com")
        assert output["contentVersion"] == "1.0.0.0"

    def test_add_parameter_chaining(self):
        t = ArmTemplate()
        result = t.add_parameter("appName", ArmParameter(type="string"))
        assert result is t  # returns self
        assert t.has_parameter("appName")

    def test_add_variable_chaining(self):
        t = ArmTemplate()
        result = t.add_variable("planName", "[concat(parameters('appName'), '-plan')]")
        assert result is t
        assert "planName" in t.to_dict()["variables"]

    def test_add_resource_chaining(self):
        t = ArmTemplate()
        res = ArmResource(
            resource_type="Microsoft.Web/serverfarms",
            api_version="2022-03-01",
            name="myPlan",
        )
        result = t.add_resource(res)
        assert result is t
        assert t.has_resource_type("Microsoft.Web/serverfarms")

    def test_add_output_chaining(self):
        t = ArmTemplate()
        result = t.add_output("webUrl", "string", "https://example.azurewebsites.net")
        assert result is t
        assert "webUrl" in t.to_dict()["outputs"]

    def test_has_resource_type_false(self):
        t = ArmTemplate()
        assert not t.has_resource_type("Microsoft.Sql/servers")

    def test_get_resources_by_type(self):
        t = ArmTemplate()
        t.add_resource(ArmResource(
            resource_type="Microsoft.Web/serverfarms",
            api_version="2022-03-01",
            name="plan1",
        ))
        t.add_resource(ArmResource(
            resource_type="Microsoft.Web/sites",
            api_version="2022-03-01",
            name="app1",
        ))
        plans = t.get_resources_by_type("Microsoft.Web/serverfarms")
        assert len(plans) == 1
        assert plans[0].name == "plan1"

    def test_to_json_is_valid_json(self):
        t = build_library_template()
        parsed = json.loads(t.to_json())
        assert isinstance(parsed, dict)

    def test_to_json_indent(self):
        t = ArmTemplate()
        output = t.to_json(indent=4)
        # Four-space indented JSON has "    " in it
        assert "    " in output


# ---------------------------------------------------------------------------
# build_library_template
# ---------------------------------------------------------------------------

class TestBuildLibraryTemplate:
    """Tests for the factory function that builds the complete template."""

    @pytest.fixture(scope="class")
    @classmethod
    def template(cls):
        return build_library_template()

    def test_schema_present(self, template):
        d = template.to_dict()
        assert "$schema" in d
        assert "deploymentTemplate" in d["$schema"]

    def test_required_parameters_present(self, template):
        for name in (
            "appName",
            "location",
            "appServicePlanSku",
            "dockerImage",
            "dockerRegistryServer",
            "dockerRegistryUsername",
            "dockerRegistryPassword",
        ):
            assert template.has_parameter(name), f"Missing parameter: {name}"

    def test_docker_registry_password_is_secure(self, template):
        pwd_param = template.parameters["dockerRegistryPassword"]
        assert pwd_param.type == "securestring"

    def test_sku_has_allowed_values(self, template):
        sku_param = template.parameters["appServicePlanSku"]
        assert sku_param.allowed_values is not None
        assert "B1" in sku_param.allowed_values

    def test_app_service_plan_resource_present(self, template):
        assert template.has_resource_type("Microsoft.Web/serverfarms")

    def test_web_app_resource_present(self, template):
        assert template.has_resource_type("Microsoft.Web/sites")

    def test_web_app_depends_on_plan(self, template):
        apps = template.get_resources_by_type("Microsoft.Web/sites")
        assert len(apps) == 1
        assert len(apps[0].depends_on) > 0

    def test_webapp_https_only(self, template):
        apps = template.get_resources_by_type("Microsoft.Web/sites")
        assert apps[0].properties.get("httpsOnly") is True

    def test_outputs_include_web_app_url(self, template):
        d = template.to_dict()
        assert "webAppUrl" in d["outputs"]

    def test_outputs_include_web_app_name(self, template):
        d = template.to_dict()
        assert "webAppName" in d["outputs"]

    def test_variables_define_app_service_plan_name(self, template):
        d = template.to_dict()
        assert "appServicePlanName" in d["variables"]

    def test_variables_define_web_app_name(self, template):
        d = template.to_dict()
        assert "webAppName" in d["variables"]

    def test_full_template_round_trips_json(self, template):
        """Serialise to JSON and back; the result must equal the original dict."""
        original = template.to_dict()
        from_json = json.loads(template.to_json())
        assert original == from_json
