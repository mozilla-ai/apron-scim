"""SCIM resource and sub-attribute models (RFC 7643).

Home for the User, Group, and EnterpriseUser resources, their multi-valued
sub-attributes, Meta, the protocol messages (ListResponse, PatchOp, PatchOperation,
ScimErrorResponse), and the ResourceKind discriminator.

The classes here are the ratified public shapes; their fields are specified in
docs/adr/0001-public-api-surface.md and populated by the ``feat(models)`` issues
of Epic 1. Every model shares :class:`_ScimModel`'s serialization contract:
frozen, SCIM camelCase aliases, and construction by either attribute name or alias.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, Self, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from apron_scim.errors import ERROR_SCHEMA

USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
"""Core schema URN for a User resource (RFC 7643 section 4.1)."""

GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"
"""Core schema URN for a Group resource (RFC 7643 section 4.2)."""

ENTERPRISE_USER_SCHEMA = "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
"""Schema URN for the Enterprise User extension (RFC 7643 section 4.3)."""

LIST_RESPONSE_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
"""Schema URN for a SCIM list/query response envelope (RFC 7644 section 3.4.2)."""

PATCH_OP_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
"""Schema URN for a SCIM PATCH request body (RFC 7644 section 3.5.2)."""


class ResourceKind(StrEnum):
    """Closed set of resource kinds that key store and service operations.

    Distinct from :class:`~apron_scim.schema.ResourceType`, the RFC 7643 discovery
    model published at ``/ResourceTypes``. This enum is the internal discriminator
    the facade and store dispatch on; its values double as the ``meta.resourceType``
    string for each kind.
    """

    USER = "User"
    GROUP = "Group"


class _ScimModel(BaseModel):
    """Base model carrying the SCIM serialization contract for every resource.

    Fields are declared in ``snake_case`` and exposed on the wire in SCIM
    ``camelCase`` via an alias generator; construction accepts either form.
    Models are frozen, so PATCH and PUT produce a new instance (functional update)
    rather than mutating in place. Unknown attributes are ignored on input; the
    service applies schema and mutability validation explicitly rather than relying
    on the model to reject them.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
        extra="ignore",
    )


class Name(_ScimModel):
    """Components of a User's real name (RFC 7643 section 4.1.1)."""

    formatted: str | None = None
    family_name: str | None = None
    given_name: str | None = None
    middle_name: str | None = None
    honorific_prefix: str | None = None
    honorific_suffix: str | None = None


class Email(_ScimModel):
    """A single entry in a User's multi-valued ``emails`` attribute (RFC 7643 section 4.1.2)."""

    value: str | None = None
    type: str | None = None
    display: str | None = None
    primary: bool | None = None


class PhoneNumber(_ScimModel):
    """A single entry in a User's multi-valued ``phoneNumbers`` attribute (RFC 7643 section 4.1.2)."""

    value: str | None = None
    type: str | None = None
    display: str | None = None
    primary: bool | None = None


class Address(_ScimModel):
    """A single entry in a User's multi-valued ``addresses`` attribute (RFC 7643 section 4.1.2)."""

    formatted: str | None = None
    street_address: str | None = None
    locality: str | None = None
    region: str | None = None
    postal_code: str | None = None
    country: str | None = None
    type: str | None = None
    primary: bool | None = None


class GroupMember(_ScimModel):
    """A single entry in a Group's multi-valued ``members`` attribute (RFC 7643 section 4.2)."""

    value: str | None = None
    # ``$ref`` cannot be produced by the camelCase generator, so it is aliased explicitly.
    ref: str | None = Field(default=None, alias="$ref")
    type: str | None = None
    display: str | None = None


class Meta(_ScimModel):
    """Common resource metadata (RFC 7643 section 3.1).

    Carries ``resourceType``, ``created``, ``lastModified``, ``location``, and
    ``version``. Identity-bearing fields are owned by the store and the service —
    see the ownership contract in docs/adr/0001-public-api-surface.md.
    """

    resource_type: str | None = None
    created: datetime | None = None
    last_modified: datetime | None = None
    location: str | None = None
    version: str | None = None


class Manager(_ScimModel):
    """A User's manager within the Enterprise User extension (RFC 7643 section 4.3).

    A complex sub-attribute pointing at another User: ``value`` is the manager's id,
    ``$ref`` a URI for that User, and ``displayName`` the manager's display name.
    """

    value: str | None = None
    # ``$ref`` cannot be produced by the camelCase generator, so it is aliased explicitly.
    ref: str | None = Field(default=None, alias="$ref")
    display_name: str | None = None


class EnterpriseUser(_ScimModel):
    """Enterprise User extension attributes (RFC 7643 section 4.3).

    Schema ``urn:ietf:params:scim:schemas:extension:enterprise:2.0:User``. Carried on a
    User under that URN as an attribute key; the URN is listed in the User's ``schemas``.
    """

    employee_number: str | None = None
    cost_center: str | None = None
    organization: str | None = None
    division: str | None = None
    department: str | None = None
    manager: Manager | None = None


class User(_ScimModel):
    """SCIM User resource (RFC 7643 section 4.1), schema ``urn:ietf:params:scim:schemas:core:2.0:User``.

    Models the v1 attribute set. Further optional RFC 7643 User attributes
    (``ims``, ``photos``, ``groups``, ...) may be added later; because they are
    optional, doing so is backward-compatible and leaves this contract intact.
    """

    schemas: list[str] = Field(default_factory=lambda: [USER_SCHEMA])
    id: str | None = None
    external_id: str | None = None
    user_name: str
    name: Name | None = None
    display_name: str | None = None
    emails: list[Email] | None = None
    phone_numbers: list[PhoneNumber] | None = None
    addresses: list[Address] | None = None
    active: bool | None = None
    enterprise_user: EnterpriseUser | None = Field(default=None, alias=ENTERPRISE_USER_SCHEMA)
    meta: Meta | None = None

    @model_validator(mode="after")
    def _list_enterprise_schema(self) -> Self:
        """List the enterprise extension URN in ``schemas`` whenever the extension is carried.

        RFC 7643 requires ``schemas`` to enumerate every schema a resource uses, so the
        URN must accompany the extension however the User was constructed.
        """
        if self.enterprise_user is not None and ENTERPRISE_USER_SCHEMA not in self.schemas:
            # Assign through ``object`` because the model is frozen; a validator that
            # returns a copy instead is silently ignored during ``__init__`` construction.
            object.__setattr__(self, "schemas", [*self.schemas, ENTERPRISE_USER_SCHEMA])
        return self


class Group(_ScimModel):
    """SCIM Group resource (RFC 7643 section 4.2), schema ``urn:ietf:params:scim:schemas:core:2.0:Group``."""

    schemas: list[str] = Field(default_factory=lambda: [GROUP_SCHEMA])
    id: str | None = None
    external_id: str | None = None
    display_name: str
    members: list[GroupMember] | None = None
    meta: Meta | None = None


Resource: TypeAlias = User | Group
"""The set of top-level resources the store and service operate on."""


class PatchOperation(_ScimModel):
    """A single add, remove, or replace operation within a PatchOp (RFC 7644 section 3.5.2).

    ``op`` names the modification.
    ``path`` selects the target attribute, absent for a whole-resource add or replace.
    ``value`` carries the new content, absent for a remove.
    """

    op: Literal["add", "remove", "replace"]
    path: str | None = None
    value: Any | None = None


class PatchOp(_ScimModel):
    """A PATCH request body carrying an ordered list of operations (RFC 7644 section 3.5.2).

    Schema ``urn:ietf:params:scim:api:messages:2.0:PatchOp``.
    """

    schemas: list[str] = Field(default_factory=lambda: [PATCH_OP_SCHEMA])
    # ``Operations`` is capitalized on the wire and the camelCase generator would emit ``operations``, so it is aliased.
    operations: list[PatchOperation] = Field(alias="Operations")


class ListResponse(_ScimModel):
    """A query result envelope wrapping a page of resources (RFC 7644 section 3.4.2).

    Schema ``urn:ietf:params:scim:api:messages:2.0:ListResponse``.
    ``Resources`` holds the page's members as they appear on the wire, which may be full or partial representations,
    so it is left untyped rather than fixed to one resource shape.
    """

    schemas: list[str] = Field(default_factory=lambda: [LIST_RESPONSE_SCHEMA])
    total_results: int
    start_index: int
    items_per_page: int
    # ``Resources`` is capitalized on the wire and the camelCase generator would emit ``resources``, so it is aliased.
    resources: list[Any] = Field(default_factory=list, alias="Resources")


class ScimErrorResponse(_ScimModel):
    """A SCIM error response body (RFC 7644 section 3.12).

    Schema ``urn:ietf:params:scim:api:messages:2.0:Error``.
    It mirrors the error body emitted for a failed SCIM operation,
    giving consumers a typed model to parse those bodies into.
    """

    schemas: list[str] = Field(default_factory=lambda: [ERROR_SCHEMA])
    status: str
    scim_type: str | None = None
    detail: str | None = None
