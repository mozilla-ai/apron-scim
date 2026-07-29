"""Smoke tests for the apron_scim public surface.

These lock the ratified contract (docs/adr/0001-public-api-surface.md) at the seams a
consumer touches — the export list, the error mapping, the store protocol, and the
model serialization contract — before the behavioral bodies land.
"""

import apron_scim
from apron_scim import (
    CompareOp,
    Comparison,
    InvalidFilter,
    InvalidPath,
    InvalidSyntax,
    InvalidValue,
    MemoryResourceStore,
    Mutability,
    NoTarget,
    PreconditionFailed,
    ResourceKind,
    ResourceNotFound,
    ResourceStore,
    ScimError,
    SortOrder,
    TooMany,
    Uniqueness,
    parse_filter,
)
from apron_scim.models import _ScimModel

# The exact public surface ratified in docs/adr/0001-public-api-surface.md. Kept here
# independently of __init__.__all__ so a change to either must be made deliberately.
RATIFIED_ALL = [
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


class _Probe(_ScimModel):
    given_name: str | None = None


def test_package_imports():
    assert apron_scim.__name__ == "apron_scim"


def test_all_matches_ratified_surface_and_is_sorted():
    assert apron_scim.__all__ == RATIFIED_ALL
    assert apron_scim.__all__ == sorted(apron_scim.__all__)
    for name in apron_scim.__all__:
        assert hasattr(apron_scim, name), name


def test_scim_error_is_exported():
    assert issubclass(apron_scim.ScimError, Exception)


def test_error_status_and_scim_type_mapping():
    assert (ScimError.http_status, ScimError.scim_type) == (500, None)
    assert (InvalidFilter.http_status, InvalidFilter.scim_type) == (400, "invalidFilter")
    assert (InvalidValue.http_status, InvalidValue.scim_type) == (400, "invalidValue")
    assert (InvalidSyntax.http_status, InvalidSyntax.scim_type) == (400, "invalidSyntax")
    assert (InvalidPath.http_status, InvalidPath.scim_type) == (400, "invalidPath")
    assert (NoTarget.http_status, NoTarget.scim_type) == (400, "noTarget")
    assert (Mutability.http_status, Mutability.scim_type) == (400, "mutability")
    assert (Uniqueness.http_status, Uniqueness.scim_type) == (409, "uniqueness")
    assert (TooMany.http_status, TooMany.scim_type) == (400, "tooMany")
    assert (ResourceNotFound.http_status, ResourceNotFound.scim_type) == (404, None)
    assert (PreconditionFailed.http_status, PreconditionFailed.scim_type) == (412, None)


def test_to_response_renders_scim_error_body():
    response = Uniqueness("userName already in use").to_response()
    assert response.status == 409
    assert response.headers["Content-Type"] == "application/scim+json"
    assert response.body == {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
        "status": "409",
        "scimType": "uniqueness",
        "detail": "userName already in use",
    }


def test_to_response_omits_absent_scim_type_and_detail():
    assert ResourceNotFound().to_response().body == {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
        "status": "404",
    }


def test_memory_store_satisfies_resource_store_protocol():
    assert isinstance(MemoryResourceStore(), ResourceStore)


def test_resource_kind_and_sort_order_values():
    assert (ResourceKind.USER, ResourceKind.GROUP) == ("User", "Group")
    assert (SortOrder.ASCENDING, SortOrder.DESCENDING) == ("ascending", "descending")


def test_compare_op_covers_the_binary_operators():
    assert {op.value for op in CompareOp} == {"eq", "ne", "co", "sw", "ew", "gt", "ge", "lt", "le"}


def test_model_serializes_camel_case_and_accepts_either_name():
    assert _Probe(givenName="x").model_dump(by_alias=True) == {"givenName": "x"}
    assert _Probe(given_name="x").given_name == "x"


def test_parse_filter_is_not_yet_implemented():
    try:
        parse_filter('userName eq "x"')
    except NotImplementedError:
        return
    raise AssertionError("parse_filter should raise NotImplementedError until Epic 2")


def test_filter_nodes_are_frozen():
    node = Comparison(attribute_path="userName", op=CompareOp.EQ, value="x")
    try:
        node.value = "y"  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("filter AST nodes must be immutable")
