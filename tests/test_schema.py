"""Contract tests for the SCIM schema and discovery models (issue #12, ADR 0001 section 5).

Covers the RFC 7643 attribute-definition model and its characteristics, plus the three
discovery response models ServiceProviderConfig (section 5), ResourceType (section 6),
and SchemaDefinition (section 7). The headline acceptance criterion is that each model
serializes to a valid ``/ServiceProviderConfig``, ``/ResourceTypes``, or ``/Schemas``
payload, so the tests centre on parse-then-serialize round-trips against RFC 7643 example
shapes plus the closed-set characteristics and camelCase wire casing.

The concrete canonical schema/config *data* (the RFC User/Group attribute definitions,
the advertised default config) is assembled by the discovery builders (issue #24); this
issue provides only the model shapes.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from apron_scim import ResourceType, SchemaDefinition, ServiceProviderConfig
from apron_scim.models import _ScimModel
from apron_scim.schema import (
    RESOURCE_TYPE_SCHEMA,
    SCHEMA_DEFINITION_SCHEMA,
    SERVICE_PROVIDER_CONFIG_SCHEMA,
    AttributeDefinition,
    AuthenticationScheme,
    BulkConfig,
    FilterConfig,
    SchemaExtension,
    Supported,
)


def wire(model: _ScimModel) -> dict[str, Any]:
    """Serialize a model exactly as the library emits it on the SCIM wire."""
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


# RFC 7643 section 8.5 ServiceProviderConfig representation.
SERVICE_PROVIDER_CONFIG_JSON = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"],
    "documentationUri": "http://example.com/help/scim.html",
    "patch": {"supported": True},
    "bulk": {"supported": True, "maxOperations": 1000, "maxPayloadSize": 1048576},
    "filter": {"supported": True, "maxResults": 200},
    "changePassword": {"supported": True},
    "sort": {"supported": True},
    "etag": {"supported": True},
    "authenticationSchemes": [
        {
            "type": "oauthbearertoken",
            "name": "OAuth Bearer Token",
            "description": "Authentication scheme using the OAuth Bearer Token Standard",
            "specUri": "http://www.rfc-editor.org/info/rfc6750",
            "documentationUri": "http://example.com/help/oauth.html",
            "primary": True,
        },
    ],
}

# RFC 7643 section 8.6 ResourceType representation (the User resource type).
RESOURCE_TYPE_JSON = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:ResourceType"],
    "id": "User",
    "name": "User",
    "endpoint": "/Users",
    "description": "User Account",
    "schema": "urn:ietf:params:scim:schemas:core:2.0:User",
    "schemaExtensions": [
        {"schema": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User", "required": True},
    ],
    "meta": {"resourceType": "ResourceType", "location": "https://example.com/v2/ResourceTypes/User"},
}

# A focused SchemaDefinition exercising the three attribute shapes: a simple string, a
# complex attribute with sub-attributes, and a multi-valued reference. Reduced from the
# RFC 7643 section 8.7 User schema — the full attribute set is the discovery builder's job.
SCHEMA_DEFINITION_JSON = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Schema"],
    "id": "urn:ietf:params:scim:schemas:core:2.0:User",
    "name": "User",
    "description": "User Account",
    "attributes": [
        {
            "name": "userName",
            "type": "string",
            "multiValued": False,
            "description": "Unique identifier for the User.",
            "required": True,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "server",
        },
        {
            "name": "name",
            "type": "complex",
            "multiValued": False,
            "description": "The components of the user's real name.",
            "required": False,
            "caseExact": False,
            "mutability": "readWrite",
            "returned": "default",
            "uniqueness": "none",
            "subAttributes": [
                {
                    "name": "familyName",
                    "type": "string",
                    "multiValued": False,
                    "description": "The family name of the User.",
                    "required": False,
                    "caseExact": False,
                    "mutability": "readWrite",
                    "returned": "default",
                    "uniqueness": "none",
                },
            ],
        },
        {
            "name": "groups",
            "type": "reference",
            "referenceTypes": ["User", "Group"],
            "multiValued": True,
            "description": "A list of groups to which the user belongs.",
            "required": False,
            "caseExact": False,
            "mutability": "readOnly",
            "returned": "default",
            "uniqueness": "none",
        },
    ],
    "meta": {
        "resourceType": "Schema",
        "location": "https://example.com/v2/Schemas/urn:ietf:params:scim:schemas:core:2.0:User",
    },
}


# --- ServiceProviderConfig (RFC 7643 section 5) ---------------------------------------


def test_service_provider_config_round_trips_rfc_example():
    assert wire(ServiceProviderConfig.model_validate(SERVICE_PROVIDER_CONFIG_JSON)) == SERVICE_PROVIDER_CONFIG_JSON


def test_service_provider_config_defaults_schemas_to_config_urn():
    config = ServiceProviderConfig(
        patch=Supported(supported=False),
        bulk=BulkConfig(supported=False, max_operations=0, max_payload_size=0),
        filter=FilterConfig(supported=False, max_results=0),
        change_password=Supported(supported=False),
        sort=Supported(supported=False),
        etag=Supported(supported=False),
        authentication_schemes=[],
    )
    assert config.schemas == [SERVICE_PROVIDER_CONFIG_SCHEMA]


def test_service_provider_config_requires_authentication_schemes():
    with pytest.raises(ValidationError):
        ServiceProviderConfig.model_validate(
            {
                "schemas": [SERVICE_PROVIDER_CONFIG_SCHEMA],
                "patch": {"supported": True},
                "bulk": {"supported": True, "maxOperations": 1, "maxPayloadSize": 1},
                "filter": {"supported": True, "maxResults": 1},
                "changePassword": {"supported": True},
                "sort": {"supported": True},
                "etag": {"supported": True},
            }
        )


def test_service_provider_config_parses_nested_capabilities_into_models():
    config = ServiceProviderConfig.model_validate(SERVICE_PROVIDER_CONFIG_JSON)
    assert isinstance(config.bulk, BulkConfig)
    assert isinstance(config.filter, FilterConfig)
    assert isinstance(config.patch, Supported)
    assert all(isinstance(scheme, AuthenticationScheme) for scheme in config.authentication_schemes)


def test_service_provider_config_maps_camel_case_capability_keys():
    config = ServiceProviderConfig.model_validate(SERVICE_PROVIDER_CONFIG_JSON)
    assert config.change_password.supported is True
    assert config.bulk.max_operations == 1000
    assert config.bulk.max_payload_size == 1048576
    assert config.filter.max_results == 200
    assert config.documentation_uri == "http://example.com/help/scim.html"
    assert config.authentication_schemes[0].spec_uri == "http://www.rfc-editor.org/info/rfc6750"


def test_service_provider_config_capabilities_are_required():
    with pytest.raises(ValidationError):
        ServiceProviderConfig.model_validate({"schemas": [SERVICE_PROVIDER_CONFIG_SCHEMA]})


# --- ResourceType (RFC 7643 section 6) ------------------------------------------------


def test_resource_type_round_trips_rfc_example():
    assert wire(ResourceType.model_validate(RESOURCE_TYPE_JSON)) == RESOURCE_TYPE_JSON


def test_resource_type_defaults_schemas_to_resource_type_urn():
    resource_type = ResourceType(name="Group", endpoint="/Groups", schema="urn:ietf:params:scim:schemas:core:2.0:Group")
    assert resource_type.schemas == [RESOURCE_TYPE_SCHEMA]


def test_resource_type_parses_schema_extensions_into_models():
    resource_type = ResourceType.model_validate(RESOURCE_TYPE_JSON)
    assert all(isinstance(extension, SchemaExtension) for extension in resource_type.schema_extensions)
    assert resource_type.schema_extensions[0].required is True


def test_resource_type_schema_extensions_uses_camel_case_wire_key():
    resource_type = ResourceType.model_validate(RESOURCE_TYPE_JSON)
    serialized = wire(resource_type)
    assert "schemaExtensions" in serialized
    assert "schema_extensions" not in serialized


def test_resource_type_id_is_optional():
    # RFC 7643 section 6 makes ``id`` optional ("often the same value as the name").
    resource_type = ResourceType(name="Group", endpoint="/Groups", schema="urn:ietf:params:scim:schemas:core:2.0:Group")
    assert resource_type.id is None


def test_schema_extension_requires_the_required_member():
    # RFC 7643 section 6 makes the ``required`` sub-attribute of a schema extension mandatory.
    with pytest.raises(ValidationError):
        SchemaExtension.model_validate({"schema": "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"})


# --- SchemaDefinition + AttributeDefinition (RFC 7643 section 7) -----------------------


def test_schema_definition_round_trips_rfc_example():
    assert wire(SchemaDefinition.model_validate(SCHEMA_DEFINITION_JSON)) == SCHEMA_DEFINITION_JSON


def test_schema_definition_defaults_schemas_to_schema_urn():
    schema = SchemaDefinition(id="urn:ietf:params:scim:schemas:core:2.0:User", name="User", attributes=[])
    assert schema.schemas == [SCHEMA_DEFINITION_SCHEMA]


def test_schema_definition_name_is_optional():
    # RFC 7643 section 7 designates the Schema resource's ``name`` as OPTIONAL.
    schema = SchemaDefinition(id="urn:ietf:params:scim:schemas:core:2.0:User", attributes=[])
    assert schema.name is None


def test_schema_definition_requires_attributes():
    # RFC 7643 section 7 makes ``attributes`` a required member of a Schema resource.
    with pytest.raises(ValidationError):
        SchemaDefinition.model_validate({"id": "urn:ietf:params:scim:schemas:core:2.0:User"})


def test_attribute_definition_rejects_sub_attributes_on_a_non_complex_attribute():
    # RFC 7643 section 2.3.8: only a complex attribute may carry sub-attributes.
    with pytest.raises(ValidationError):
        AttributeDefinition(name="userName", type="string", sub_attributes=[AttributeDefinition(name="part")])


def test_attribute_definition_rejects_a_complex_sub_attribute():
    # RFC 7643 section 2.3.8: a sub-attribute may not itself be complex.
    with pytest.raises(ValidationError):
        AttributeDefinition(
            name="name",
            type="complex",
            sub_attributes=[AttributeDefinition(name="nested", type="complex")],
        )


def test_schema_definition_parses_attributes_recursively():
    schema = SchemaDefinition.model_validate(SCHEMA_DEFINITION_JSON)
    assert all(isinstance(attribute, AttributeDefinition) for attribute in schema.attributes)
    complex_attribute = next(attribute for attribute in schema.attributes if attribute.name == "name")
    assert isinstance(complex_attribute.sub_attributes[0], AttributeDefinition)


def test_attribute_definition_defaults_to_a_simple_read_write_string():
    assert wire(AttributeDefinition(name="userName")) == {
        "name": "userName",
        "type": "string",
        "multiValued": False,
        "required": False,
        "caseExact": False,
        "mutability": "readWrite",
        "returned": "default",
        "uniqueness": "none",
    }


def test_attribute_definition_maps_camel_case_aliases_to_snake_case_fields():
    attribute = SchemaDefinition.model_validate(SCHEMA_DEFINITION_JSON).attributes[2]
    assert attribute.multi_valued is True
    assert attribute.case_exact is False
    assert attribute.reference_types == ["User", "Group"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("type", "unknownType"),
        ("mutability", "readWriteOnly"),
        ("returned", "sometimes"),
        ("uniqueness", "unique"),
    ],
)
def test_attribute_definition_rejects_values_outside_the_closed_sets(field, value):
    with pytest.raises(ValidationError):
        AttributeDefinition(name="userName", **{field: value})


def test_attribute_definition_accepts_every_defined_characteristic_value():
    for mutability in ("readOnly", "readWrite", "immutable", "writeOnly"):
        assert AttributeDefinition(name="x", mutability=mutability).mutability == mutability
    for returned in ("always", "never", "default", "request"):
        assert AttributeDefinition(name="x", returned=returned).returned == returned
    for uniqueness in ("none", "server", "global"):
        assert AttributeDefinition(name="x", uniqueness=uniqueness).uniqueness == uniqueness
    for attribute_type in ("string", "complex", "boolean", "decimal", "integer", "dateTime", "reference", "binary"):
        assert AttributeDefinition(name="x", type=attribute_type).type == attribute_type


def test_schema_definition_omits_absent_optional_attribute_fields():
    # A simple string attribute carries no sub-attributes, reference types, or canonical
    # values, so those wire keys must be absent rather than serialized as null.
    serialized = wire(AttributeDefinition(name="userName"))
    assert "subAttributes" not in serialized
    assert "referenceTypes" not in serialized
    assert "canonicalValues" not in serialized
    assert "description" not in serialized
