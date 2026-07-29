"""Reference ResourceStore implementations.

Home for :class:`MemoryResourceStore`, an in-memory :class:`~apron_scim.protocols.ResourceStore`
that powers unit tests and the documentation's worked example. Its method bodies land
in Epic 4; this module ratifies that it structurally satisfies the store contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apron_scim.models import Resource, ResourceKind
    from apron_scim.protocols import ListQuery, Page, ResourceStore


class MemoryResourceStore:
    """In-memory :class:`~apron_scim.protocols.ResourceStore` for tests and documentation.

    Suitable for development, CLIs, and single-process use; not for production
    multi-process deployments. Owns resource identity, timestamps, and version like any
    conforming store.
    """

    def __init__(self) -> None:
        """Create an empty store."""
        self._resources: dict[tuple[ResourceKind, str], Resource] = {}

    async def create(self, resource: Resource) -> Resource:
        """Persist a new resource, assigning id, timestamps, and version."""
        raise NotImplementedError

    async def get(self, resource_kind: ResourceKind, resource_id: str) -> Resource | None:
        """Retrieve a resource by kind and id, or ``None`` if absent."""
        raise NotImplementedError

    async def replace(self, resource: Resource) -> Resource:
        """Persist a full replacement of an existing resource."""
        raise NotImplementedError

    async def delete(self, resource_kind: ResourceKind, resource_id: str) -> None:
        """Delete a resource by kind and id."""
        raise NotImplementedError

    async def query(self, query: ListQuery) -> Page:
        """Return the page of resources matching a parsed query."""
        raise NotImplementedError


if TYPE_CHECKING:
    # Assert at type-check time that MemoryResourceStore structurally satisfies the
    # ResourceStore protocol; ty verifies the method signatures match.
    _conforms: ResourceStore = MemoryResourceStore()
