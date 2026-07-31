"""SCIM schema and discovery models (RFC 7643).

Home for the discovery response models the service publishes — :class:`ServiceProviderConfig`
(section 5), :class:`ResourceType` (section 6), and :class:`SchemaDefinition` (section 7) —
together with :class:`AttributeDefinition`, the recursive attribute model that backs a
schema's ``attributes``. Their field shapes are specified in
docs/adr/0001-public-api-surface.md; the concrete discovery documents are assembled by the
service's discovery builders. Every model shares :class:`_ScimModel`'s serialization
contract: frozen, SCIM camelCase aliases, and construction by either attribute name or alias.
"""

from __future__ import annotations

from typing import Literal, Self

from pydantic import Field, model_validator

from apron_scim.models import Meta, _ScimModel

SERVICE_PROVIDER_CONFIG_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig"
"""Core schema URN for the service-provider configuration (RFC 7643 section 5)."""

RESOURCE_TYPE_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:ResourceType"
"""Core schema URN for a resource-type discovery entry (RFC 7643 section 6)."""

SCHEMA_DEFINITION_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Schema"
"""Core schema URN for a schema-definition discovery entry (RFC 7643 section 7)."""


class AttributeDefinition(_ScimModel):
    """The definition of one attribute within a schema (RFC 7643 section 7).

    Names the attribute and its data type and declares the characteristics a provider enforces:
    cardinality, requiredness, case sensitivity, mutability, return behavior, and uniqueness scope.
    ``sub_attributes`` nests the same definition for a ``complex`` attribute's members,
    and ``reference_types`` lists the resource types a ``reference`` attribute may point at.
    """

    name: str
    type: Literal["string", "complex", "boolean", "decimal", "integer", "dateTime", "reference", "binary"] = "string"
    sub_attributes: list[AttributeDefinition] | None = None
    multi_valued: bool = False
    description: str | None = None
    required: bool = False
    canonical_values: list[str] | None = None
    case_exact: bool = False
    mutability: Literal["readOnly", "readWrite", "immutable", "writeOnly"] = "readWrite"
    returned: Literal["always", "never", "default", "request"] = "default"
    uniqueness: Literal["none", "server", "global"] = "none"
    reference_types: list[str] | None = None

    @model_validator(mode="after")
    def _reject_illegal_sub_attribute_nesting(self) -> Self:
        """Reject sub-attribute structures RFC 7643 section 2.3.8 forbids.

        Only a complex attribute may carry sub-attributes, and a sub-attribute may not itself
        be complex, so a schema's attribute tree is at most two levels deep.
        """
        if self.sub_attributes is None:
            return self
        if self.type != "complex":
            raise ValueError("only a complex attribute may define sub-attributes")
        if any(sub.type == "complex" for sub in self.sub_attributes):
            raise ValueError("a sub-attribute may not itself be complex")
        return self


class Supported(_ScimModel):
    """A capability advertised solely by whether the service provider supports it (RFC 7643 section 5)."""

    supported: bool


class BulkConfig(_ScimModel):
    """The service provider's bulk-operation capability (RFC 7643 section 5).

    Advertises support plus the ceilings a client must observe: the maximum number of
    operations and the maximum payload size, in bytes, of a single bulk request.
    """

    supported: bool
    max_operations: int
    max_payload_size: int


class FilterConfig(_ScimModel):
    """The service provider's filtering capability (RFC 7643 section 5).

    Advertises support plus ``max_results``, the largest number of matches the provider
    returns for a filtered query.
    """

    supported: bool
    max_results: int


class AuthenticationScheme(_ScimModel):
    """An authentication scheme the service provider supports (RFC 7643 section 5).

    Names and describes the scheme, optionally links to its specification and documentation,
    and may flag itself as the primary scheme.
    """

    type: str
    name: str
    description: str
    spec_uri: str | None = None
    documentation_uri: str | None = None
    primary: bool | None = None


class SchemaExtension(_ScimModel):
    """A schema extension a resource type carries (RFC 7643 section 6).

    Pairs the extension schema's URN with whether the service provider requires it.
    """

    # ``schema`` is the RFC 7643 wire key; a field named ``schema`` shadows pydantic's
    # deprecated ``BaseModel.schema``, so it is named distinctly and aliased back to it.
    schema_urn: str = Field(alias="schema")
    required: bool


class ServiceProviderConfig(_ScimModel):
    """Advertised service-provider capabilities (RFC 7643 section 5).

    Published at ``/ServiceProviderConfig`` to declare which SCIM protocol features the
    service provider supports: PATCH, filtering, sort, ETag, bulk, and the accepted
    authentication schemes.
    """

    schemas: list[str] = Field(default_factory=lambda: [SERVICE_PROVIDER_CONFIG_SCHEMA])
    documentation_uri: str | None = None
    patch: Supported
    bulk: BulkConfig
    filter: FilterConfig
    change_password: Supported
    sort: Supported
    etag: Supported
    authentication_schemes: list[AuthenticationScheme]
    meta: Meta | None = None


class ResourceType(_ScimModel):
    """A resource-type discovery entry (RFC 7643 section 6).

    Published at ``/ResourceTypes``, one per resource kind, naming the kind's endpoint, its
    base schema URN, and any schema extensions it carries.
    """

    schemas: list[str] = Field(default_factory=lambda: [RESOURCE_TYPE_SCHEMA])
    id: str | None = None
    name: str
    endpoint: str
    description: str | None = None
    # ``schema`` is the RFC 7643 wire key; a field named ``schema`` shadows pydantic's
    # deprecated ``BaseModel.schema``, so it is named distinctly and aliased back to it.
    schema_urn: str = Field(alias="schema")
    schema_extensions: list[SchemaExtension] = Field(default_factory=list)
    meta: Meta | None = None


class SchemaDefinition(_ScimModel):
    """A schema discovery entry (RFC 7643 section 7).

    Published at ``/Schemas`` to describe a schema by its URN, name, and the ordered set of
    attribute definitions that compose it.
    """

    schemas: list[str] = Field(default_factory=lambda: [SCHEMA_DEFINITION_SCHEMA])
    id: str
    name: str | None = None
    description: str | None = None
    attributes: list[AttributeDefinition]
    meta: Meta | None = None
