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

from enum import StrEnum
from typing import TypeAlias

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


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


class Email(_ScimModel):
    """A single entry in a User's multi-valued ``emails`` attribute (RFC 7643 section 4.1.2)."""


class PhoneNumber(_ScimModel):
    """A single entry in a User's multi-valued ``phoneNumbers`` attribute (RFC 7643 section 4.1.2)."""


class Address(_ScimModel):
    """A single entry in a User's multi-valued ``addresses`` attribute (RFC 7643 section 4.1.2)."""


class GroupMember(_ScimModel):
    """A single entry in a Group's multi-valued ``members`` attribute (RFC 7643 section 4.2)."""


class Meta(_ScimModel):
    """Common resource metadata (RFC 7643 section 3.1).

    Carries ``resourceType``, ``created``, ``lastModified``, ``location``, and
    ``version``. Identity-bearing fields are owned by the store and the service —
    see the ownership contract in docs/adr/0001-public-api-surface.md.
    """


class User(_ScimModel):
    """SCIM User resource (RFC 7643 section 4.1), schema ``urn:ietf:params:scim:schemas:core:2.0:User``."""


class Group(_ScimModel):
    """SCIM Group resource (RFC 7643 section 4.2), schema ``urn:ietf:params:scim:schemas:core:2.0:Group``."""


class EnterpriseUser(_ScimModel):
    """Enterprise User extension (RFC 7643 section 4.3).

    Schema ``urn:ietf:params:scim:schemas:extension:enterprise:2.0:User``, carried
    on a User under its extension URN key.
    """


Resource: TypeAlias = User | Group
"""The set of top-level resources the store and service operate on."""


class PatchOperation(_ScimModel):
    """A single ``add``/``remove``/``replace`` operation within a PatchOp (RFC 7644 section 3.5.2)."""


class PatchOp(_ScimModel):
    """A PATCH request body: an ordered list of operations (RFC 7644 section 3.5.2).

    Schema ``urn:ietf:params:scim:api:messages:2.0:PatchOp``.
    """


class ListResponse(_ScimModel):
    """A query result envelope (RFC 7644 section 3.4.2).

    Schema ``urn:ietf:params:scim:api:messages:2.0:ListResponse``.
    """


class ScimErrorResponse(_ScimModel):
    """A SCIM error response body (RFC 7644 section 3.12).

    Schema ``urn:ietf:params:scim:api:messages:2.0:Error``. The wire body is emitted
    as a plain ``dict`` by :meth:`~apron_scim.errors.ScimError.to_response`; this
    model documents that shape for consumers that parse error bodies.
    """
