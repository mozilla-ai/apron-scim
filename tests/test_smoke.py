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
    MemoryResourceStore,
    Mutability,
    PreconditionFailed,
    ResourceKind,
    ResourceNotFound,
    ResourceStore,
    ScimError,
    SortOrder,
    Uniqueness,
    parse_filter,
)
from apron_scim.models import _ScimModel


class _Probe(_ScimModel):
    given_name: str | None = None


def test_package_imports():
    assert apron_scim.__name__ == "apron_scim"


def test_all_is_sorted_and_exported():
    assert apron_scim.__all__ == sorted(apron_scim.__all__)
    for name in apron_scim.__all__:
        assert hasattr(apron_scim, name), name


def test_scim_error_is_exported():
    assert issubclass(apron_scim.ScimError, Exception)


def test_error_status_and_scim_type_mapping():
    assert (ScimError.http_status, ScimError.scim_type) == (500, None)
    assert (InvalidFilter.http_status, InvalidFilter.scim_type) == (400, "invalidFilter")
    assert (Mutability.http_status, Mutability.scim_type) == (400, "mutability")
    assert (Uniqueness.http_status, Uniqueness.scim_type) == (409, "uniqueness")
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
