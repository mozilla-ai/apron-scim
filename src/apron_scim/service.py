"""SCIM service-provider request/response orchestration.

Home for :class:`ScimServiceProvider` — the framework-agnostic facade mapping a
parsed request plus a :class:`~apron_scim.protocols.ResourceStore` to a neutral
:class:`ScimResponse` — and the :class:`ScimResponse` type itself. The orchestration
bodies land in Epic 4; this module ratifies the facade signatures and the response
shape callers integrate against. See docs/adr/0001-public-api-surface.md.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apron_scim.models import ResourceKind
    from apron_scim.protocols import ResourceStore
    from apron_scim.schema import ServiceProviderConfig

SCIM_CONTENT_TYPE = "application/scim+json"
"""Media type for SCIM request and response bodies (RFC 7644 section 3.1)."""


@dataclass(frozen=True, slots=True)
class ScimResponse:
    """A framework-neutral SCIM response the caller maps to its HTTP layer.

    Attributes:
        status: The HTTP status code (RFC 7644 section 3.12).
        body: The already-shaped response body as a JSON-serializable ``dict``, or
            ``None`` for a body-less response such as a successful DELETE. It is a
            plain ``dict`` rather than a model so the caller can serialize it directly.
        headers: Response headers to set, such as ``ETag``, ``Location``, and
            ``Content-Type: application/scim+json``.
    """

    status: int
    body: dict[str, Any] | None = None
    headers: Mapping[str, str] = field(default_factory=dict)


class ScimServiceProvider:
    """Framework-agnostic SCIM service-provider facade (RFC 7644).

    Constructed from a :class:`~apron_scim.protocols.ResourceStore`, a ``base_url``,
    and an optional :class:`~apron_scim.schema.ServiceProviderConfig`, it exposes one
    method per SCIM operation. Each accepts request primitives — the resource kind,
    ids, a parsed JSON body ``dict``, and raw query parameters — and returns a
    :class:`ScimResponse`. The facade catches every :class:`~apron_scim.errors.ScimError`
    internally and returns a well-formed error response, so callers never map
    exceptions; only unexpected (non-SCIM) exceptions propagate.
    """

    def __init__(
        self,
        store: ResourceStore,
        *,
        base_url: str,
        config: ServiceProviderConfig | None = None,
    ) -> None:
        """Configure the facade.

        Args:
            store: The persistence backend the facade orchestrates.
            base_url: The service provider's base URL, used to compose
                ``meta.location`` for resources.
            config: The advertised service-provider configuration, or ``None`` to use
                the library's defaults.
        """
        self._store = store
        self._base_url = base_url
        self._config = config

    async def create(self, resource_kind: ResourceKind, body: dict[str, Any]) -> ScimResponse:
        """Create a resource from a parsed request body (RFC 7644 section 3.3).

        Args:
            resource_kind: The kind of resource to create.
            body: The parsed JSON request body.

        Returns:
            A 201 response carrying the created resource, or an error response.
        """
        raise NotImplementedError

    async def get(
        self,
        resource_kind: ResourceKind,
        resource_id: str,
        *,
        attributes: Sequence[str] | None = None,
        excluded_attributes: Sequence[str] | None = None,
    ) -> ScimResponse:
        """Retrieve a single resource by id (RFC 7644 section 3.4.1).

        Args:
            resource_kind: The kind of resource to retrieve.
            resource_id: The id of the resource.
            attributes: Attribute paths to include, projecting the result to just these.
            excluded_attributes: Attribute paths to omit from the result.

        Returns:
            A 200 response carrying the resource, or an error response.
        """
        raise NotImplementedError

    async def replace(self, resource_kind: ResourceKind, resource_id: str, body: dict[str, Any]) -> ScimResponse:
        """Replace a resource with a parsed request body via PUT (RFC 7644 section 3.5.1).

        Args:
            resource_kind: The kind of resource to replace.
            resource_id: The id of the resource to replace.
            body: The parsed JSON request body carrying the full replacement.

        Returns:
            A 200 response carrying the replaced resource, or an error response.
        """
        raise NotImplementedError

    async def patch(self, resource_kind: ResourceKind, resource_id: str, body: dict[str, Any]) -> ScimResponse:
        """Apply a PATCH to a resource (RFC 7644 section 3.5.2).

        The facade applies the operations itself — reading the current resource,
        applying the operations, and replacing it — so the store needs no PATCH support.

        Args:
            resource_kind: The kind of resource to patch.
            resource_id: The id of the resource to patch.
            body: The parsed JSON PatchOp request body.

        Returns:
            A 200 response carrying the patched resource, or an error response.
        """
        raise NotImplementedError

    async def delete(self, resource_kind: ResourceKind, resource_id: str) -> ScimResponse:
        """Delete a resource by id (RFC 7644 section 3.6).

        Args:
            resource_kind: The kind of resource to delete.
            resource_id: The id of the resource to delete.

        Returns:
            A 204 response with no body, or an error response.
        """
        raise NotImplementedError

    async def list(self, resource_kind: ResourceKind, query_params: Mapping[str, str]) -> ScimResponse:
        """Query a resource collection (RFC 7644 section 3.4.2).

        Parses ``filter``, ``sortBy``, ``sortOrder``, ``startIndex``, and ``count``
        from the raw query parameters into a :class:`~apron_scim.protocols.ListQuery`.

        Args:
            resource_kind: The kind of resource to query.
            query_params: The raw request query parameters.

        Returns:
            A 200 ListResponse, or an error response.
        """
        raise NotImplementedError

    async def service_provider_config(self) -> ScimResponse:
        """Return the ``/ServiceProviderConfig`` discovery document (RFC 7644 section 4)."""
        raise NotImplementedError

    async def resource_types(self) -> ScimResponse:
        """Return the ``/ResourceTypes`` discovery document (RFC 7644 section 4)."""
        raise NotImplementedError

    async def schemas(self) -> ScimResponse:
        """Return the ``/Schemas`` discovery document (RFC 7644 section 4)."""
        raise NotImplementedError
