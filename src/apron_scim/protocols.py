"""Caller-provided protocols for apron_scim.

Home for :class:`ResourceStore` — the persistence seam a consumer implements — and
the :class:`ListQuery`/:class:`Page` types its ``query`` method exchanges with the
service. The store owns identity, timestamps, and version; the service owns protocol
shaping. See docs/adr/0001-public-api-surface.md for the full ownership contract.
The method bodies a consumer supplies land when they implement the store; this module
ratifies the signatures.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from apron_scim.filter import FilterNode
    from apron_scim.models import Resource, ResourceKind


class SortOrder(StrEnum):
    """Direction for a sorted query (RFC 7644 section 3.4.2.3)."""

    ASCENDING = "ascending"
    DESCENDING = "descending"


@dataclass(frozen=True, slots=True)
class ListQuery:
    """A parsed collection query passed to :meth:`ResourceStore.query`.

    The service has already parsed the raw query string into these primitives, so a
    store never sees SCIM query syntax.

    Attributes:
        resource_kind: The kind of resource being queried.
        filter: The parsed filter, or ``None`` when the request carried none.
        start_index: 1-based index of the first result to return (RFC 7644 section 3.4.2.4).
        count: Maximum number of results to return, or ``None`` for the store's default.
        sort_by: Attribute path to sort on, or ``None`` for the store's default order.
        sort_order: Sort direction; ``None`` when unspecified.
    """

    resource_kind: ResourceKind
    filter: FilterNode | None = None
    start_index: int = 1
    count: int | None = None
    sort_by: str | None = None
    sort_order: SortOrder | None = None


@dataclass(frozen=True, slots=True)
class Page:
    """A page of query results returned by :meth:`ResourceStore.query`.

    Attributes:
        resources: The resources on this page, already filtered, sorted, and sliced
            by the store per the :class:`ListQuery`.
        total_results: The total number of resources matching the filter across all
            pages, which the service echoes as ``totalResults``.
    """

    resources: Sequence[Resource]
    total_results: int


@runtime_checkable
class ResourceStore(Protocol):
    """Persistence seam a consumer implements to back the service.

    The store owns resource identity and versioning; the service owns SCIM protocol
    shaping. It exposes only full-resource operations — the library applies PATCH
    itself by reading, applying operations, and replacing — so there is no ``patch``
    method here.
    """

    async def create(self, resource: Resource) -> Resource:
        """Persist a new resource and return it with server-assigned metadata.

        NOTE: the store owns ``id``, ``meta.created``, ``meta.lastModified``, and
        ``meta.version``; it must assign them here and callers must not set them.
        Uniqueness constraints are the store's to enforce.

        Args:
            resource: The resource to create; its identity and metadata fields are
                unset or ignored.

        Returns:
            The stored resource, carrying the assigned id, timestamps, and version.

        Raises:
            Uniqueness: If a uniqueness constraint (e.g. duplicate ``userName``) is violated.
        """
        ...

    async def get(self, resource_kind: ResourceKind, resource_id: str) -> Resource | None:
        """Retrieve a resource by kind and id.

        Args:
            resource_kind: The kind of resource to retrieve.
            resource_id: The server-assigned id of the resource.

        Returns:
            The stored resource, or ``None`` if no resource of that kind has that id.
        """
        ...

    async def replace(self, resource: Resource) -> Resource:
        """Persist a full replacement of an existing resource and return the result.

        NOTE: the store owns ``meta.lastModified`` and ``meta.version`` and must
        refresh them; ``id`` and ``meta.created`` are preserved from the stored resource.

        Args:
            resource: The full replacement, carrying the id of the resource to replace.

        Returns:
            The stored resource, carrying the refreshed timestamps and version.

        Raises:
            ResourceNotFound: If no resource with that id exists.
            Uniqueness: If the replacement violates a uniqueness constraint.
        """
        ...

    async def delete(self, resource_kind: ResourceKind, resource_id: str) -> None:
        """Delete a resource by kind and id.

        Args:
            resource_kind: The kind of resource to delete.
            resource_id: The server-assigned id of the resource.

        Raises:
            ResourceNotFound: If no resource of that kind has that id.
        """
        ...

    async def query(self, query: ListQuery) -> Page:
        """Return the page of resources matching a parsed collection query.

        The store applies the filter, sort, and pagination described by ``query``.

        Args:
            query: The parsed query describing filter, sort, and pagination.

        Returns:
            The matching page, including the total count across all pages.
        """
        ...
