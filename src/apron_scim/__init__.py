"""Stateless server-side SCIM 2.0 protocol library.

apron_scim implements the SCIM 2.0 service-provider role (RFC 7643/7644): it receives
user and group provisioning from a customer identity provider and shapes the protocol
layer — schema, filter parsing, PATCH, and request/response — while the consumer owns
persistence and HTTP routing.

The public surface is ratified in docs/adr/0001-public-api-surface.md; behavior lands
per epic. This module re-exports that surface and configures library-silent logging.
"""

from __future__ import annotations

import logging

from apron_scim.errors import (
    InvalidFilter,
    InvalidPath,
    InvalidSyntax,
    InvalidValue,
    Mutability,
    NoTarget,
    PreconditionFailed,
    ResourceNotFound,
    ScimError,
    TooMany,
    Uniqueness,
)
from apron_scim.filter import (
    And,
    CompareOp,
    Comparison,
    FilterNode,
    FilterVisitor,
    Not,
    Or,
    Present,
    ValuePath,
    parse_filter,
)
from apron_scim.models import (
    Address,
    Email,
    EnterpriseUser,
    Group,
    GroupMember,
    ListResponse,
    Meta,
    Name,
    PatchOp,
    PatchOperation,
    PhoneNumber,
    Resource,
    ResourceKind,
    ScimErrorResponse,
    User,
)
from apron_scim.protocols import ListQuery, Page, ResourceStore, SortOrder
from apron_scim.schema import ResourceType, SchemaDefinition, ServiceProviderConfig
from apron_scim.service import ScimResponse, ScimServiceProvider
from apron_scim.stores import MemoryResourceStore

# Keep the library silent until the application opts in; configuring the ``apron_scim``
# logger in any way replaces this handler.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "Address",
    "And",
    "CompareOp",
    "Comparison",
    "Email",
    "EnterpriseUser",
    "FilterNode",
    "FilterVisitor",
    "Group",
    "GroupMember",
    "InvalidFilter",
    "InvalidPath",
    "InvalidSyntax",
    "InvalidValue",
    "ListQuery",
    "ListResponse",
    "MemoryResourceStore",
    "Meta",
    "Mutability",
    "Name",
    "NoTarget",
    "Not",
    "Or",
    "Page",
    "PatchOp",
    "PatchOperation",
    "PhoneNumber",
    "PreconditionFailed",
    "Present",
    "Resource",
    "ResourceKind",
    "ResourceNotFound",
    "ResourceStore",
    "ResourceType",
    "SchemaDefinition",
    "ScimError",
    "ScimErrorResponse",
    "ScimResponse",
    "ScimServiceProvider",
    "ServiceProviderConfig",
    "SortOrder",
    "TooMany",
    "Uniqueness",
    "User",
    "ValuePath",
    "parse_filter",
]
