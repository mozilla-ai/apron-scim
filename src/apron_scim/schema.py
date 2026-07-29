"""SCIM schema and discovery models (RFC 7643).

Home for the discovery response models the service publishes: :class:`ServiceProviderConfig`
(the advertised capabilities passed to the facade), :class:`ResourceType`, and
:class:`SchemaDefinition`. Their fields — and the RFC 7643 attribute-definition models
that back :class:`SchemaDefinition` — are specified in docs/adr/0001-public-api-surface.md
and populated by ``feat(schema)`` in Epic 1.
"""

from __future__ import annotations

from apron_scim.models import _ScimModel


class ServiceProviderConfig(_ScimModel):
    """Advertised service-provider capabilities (RFC 7643 section 5).

    Published at ``/ServiceProviderConfig`` and accepted by
    :class:`~apron_scim.service.ScimServiceProvider` to describe supported features
    (patch, filtering, sort, etag, bulk, authentication schemes).
    """


class ResourceType(_ScimModel):
    """A resource type discovery entry (RFC 7643 section 6).

    Published at ``/ResourceTypes``, one per resource kind, naming its endpoint,
    core schema, and any schema extensions. Distinct from
    :class:`~apron_scim.models.ResourceKind`, the internal store/service discriminator.
    """


class SchemaDefinition(_ScimModel):
    """A schema discovery entry (RFC 7643 section 7).

    Published at ``/Schemas``, describing a schema's attributes and their
    characteristics (mutability, returned, uniqueness, caseExact).
    """
