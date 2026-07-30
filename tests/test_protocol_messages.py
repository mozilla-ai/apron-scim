"""Contract tests for the SCIM protocol messages (issue #11, ADR 0001 section 5).

Covers ListResponse (RFC 7644 section 3.4.2), PatchOp/PatchOperation (section 3.5.2),
and ScimErrorResponse (section 3.12). The headline acceptance criterion is that each
serializes with its correct ``schemas`` URN and SCIM field casing — including the two
capitalized wire keys (``Resources``, ``Operations``) and the ``scimType`` alias — so the
tests centre on parse-then-serialize round-trips against RFC 7644 example bodies.
"""

from typing import Any

import pytest
from pydantic import ValidationError

from apron_scim import ListResponse, PatchOp, PatchOperation, ScimErrorResponse
from apron_scim.models import (
    ERROR_SCHEMA,
    LIST_RESPONSE_SCHEMA,
    PATCH_OP_SCHEMA,
    _ScimModel,
)


def wire(model: _ScimModel) -> dict[str, Any]:
    """Serialize a model exactly as the library emits it on the SCIM wire."""
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


# RFC 7644 section 3.4.2 ListResponse: an envelope wrapping a page of resources. The
# member resources are kept minimal (id only) so the round-trip isolates the envelope's
# own casing rather than re-testing User/Group serialization.
LIST_RESPONSE_JSON = {
    "schemas": ["urn:ietf:params:scim:api:messages:2.0:ListResponse"],
    "totalResults": 2,
    "startIndex": 1,
    "itemsPerPage": 2,
    "Resources": [
        {"id": "2819c223-7f76-453a-919d-413861904646", "userName": "bjensen@example.com"},
        {"id": "902c246b-6245-4190-8e05-00816be7344a", "userName": "jsmith@example.com"},
    ],
}

# RFC 7644 section 3.5.2 PatchOp: an ordered list of add/remove/replace operations.
PATCH_OP_JSON = {
    "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
    "Operations": [
        {"op": "add", "path": "emails", "value": [{"value": "babs@jensen.org", "type": "home"}]},
        {"op": "remove", "path": 'emails[type eq "work"]'},
        {"op": "replace", "path": "displayName", "value": "Babs Jensen"},
    ],
}

# RFC 7644 section 3.12 error response.
ERROR_JSON = {
    "schemas": ["urn:ietf:params:scim:api:messages:2.0:Error"],
    "status": "400",
    "scimType": "mutability",
    "detail": "Attribute 'id' is readOnly",
}


# --- ListResponse ---------------------------------------------------------------------


def test_list_response_round_trips_rfc_example():
    assert wire(ListResponse.model_validate(LIST_RESPONSE_JSON)) == LIST_RESPONSE_JSON


def test_list_response_defaults_schemas_to_message_urn():
    envelope = ListResponse(total_results=0, start_index=1, items_per_page=0)
    assert envelope.schemas == [LIST_RESPONSE_SCHEMA]


def test_list_response_serializes_counts_with_camel_case_keys():
    envelope = ListResponse(total_results=2, start_index=1, items_per_page=2, resources=[{"id": "x"}])
    assert wire(envelope) == {
        "schemas": [LIST_RESPONSE_SCHEMA],
        "totalResults": 2,
        "startIndex": 1,
        "itemsPerPage": 2,
        "Resources": [{"id": "x"}],
    }


def test_list_response_resources_uses_capitalized_wire_key():
    envelope = ListResponse(total_results=1, start_index=1, items_per_page=1, resources=[{"id": "x"}])
    assert "Resources" in wire(envelope)
    assert "resources" not in wire(envelope)


def test_list_response_defaults_to_empty_resources():
    envelope = ListResponse(total_results=0, start_index=1, items_per_page=0)
    assert wire(envelope)["Resources"] == []


def test_list_response_counts_are_required():
    with pytest.raises(ValidationError):
        ListResponse.model_validate({"schemas": [LIST_RESPONSE_SCHEMA]})


# --- PatchOp / PatchOperation ---------------------------------------------------------


def test_patch_op_round_trips_rfc_example():
    assert wire(PatchOp.model_validate(PATCH_OP_JSON)) == PATCH_OP_JSON


def test_patch_op_defaults_schemas_to_message_urn():
    op = PatchOp(operations=[PatchOperation(op="replace", path="active", value=False)])
    assert op.schemas == [PATCH_OP_SCHEMA]


def test_patch_op_operations_use_capitalized_wire_key():
    op = PatchOp(operations=[PatchOperation(op="remove", path="active")])
    serialized = wire(op)
    assert "Operations" in serialized
    assert "operations" not in serialized


def test_patch_op_parses_operations_into_typed_models():
    op = PatchOp.model_validate(PATCH_OP_JSON)
    assert all(isinstance(operation, PatchOperation) for operation in op.operations)


def test_patch_op_operations_are_required():
    with pytest.raises(ValidationError):
        PatchOp.model_validate({"schemas": [PATCH_OP_SCHEMA]})


def test_patch_operation_omits_absent_path_and_value():
    # A remove carries a path but no value; a root-level replace carries a value but no path.
    # Together they show each field is omitted from the wire form when unset, rather than nulled.
    assert wire(PatchOperation(op="remove", path="active")) == {"op": "remove", "path": "active"}
    assert wire(PatchOperation(op="replace", value="Babs Jensen")) == {"op": "replace", "value": "Babs Jensen"}


def test_patch_operation_carries_arbitrary_value():
    operation = PatchOperation(op="add", path="emails", value=[{"value": "x@example.com"}])
    assert operation.value == [{"value": "x@example.com"}]


@pytest.mark.parametrize("op", ["add", "remove", "replace"])
def test_patch_operation_accepts_defined_ops(op):
    assert PatchOperation(op=op).op == op


def test_patch_operation_rejects_unknown_op():
    with pytest.raises(ValidationError):
        PatchOperation(op="delete")


# --- ScimErrorResponse ----------------------------------------------------------------


def test_error_response_round_trips_rfc_example():
    assert wire(ScimErrorResponse.model_validate(ERROR_JSON)) == ERROR_JSON


def test_error_response_defaults_schemas_to_message_urn():
    assert ScimErrorResponse(status="404").schemas == [ERROR_SCHEMA]


def test_error_response_serializes_scim_type_with_camel_case_alias():
    error = ScimErrorResponse(status="400", scim_type="invalidValue", detail="bad value")
    assert wire(error) == {
        "schemas": [ERROR_SCHEMA],
        "status": "400",
        "scimType": "invalidValue",
        "detail": "bad value",
    }


def test_error_response_omits_absent_scim_type_and_detail():
    assert wire(ScimErrorResponse(status="404")) == {
        "schemas": [ERROR_SCHEMA],
        "status": "404",
    }


def test_error_response_status_is_required():
    with pytest.raises(ValidationError):
        ScimErrorResponse.model_validate({"schemas": [ERROR_SCHEMA]})
