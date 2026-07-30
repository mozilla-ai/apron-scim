"""Contract tests for the SCIM Enterprise User extension (issue #10, ADR 0001 section 5).

Covers the EnterpriseUser extension model, its ``manager`` complex sub-attribute, and its
carriage on User under the extension URN key
``urn:ietf:params:scim:schemas:extension:enterprise:2.0:User``.

The headline acceptance criteria are a parse-then-serialize round-trip of the RFC 7643
section 8.3 full enterprise User, that the extension attributes parse and serialize under
the extension URN, and that the URN lands in the resource's ``schemas`` list whenever the
extension is present.
"""

from typing import Any

from apron_scim import EnterpriseUser, User
from apron_scim.models import ENTERPRISE_USER_SCHEMA, Manager, _ScimModel

CORE_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"


def wire(model: _ScimModel) -> dict[str, Any]:
    """Serialize a model exactly as the library emits it on the SCIM wire."""
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


# RFC 7643 section 8.3 (enterprise User) reduced to the v1-scoped core User attributes plus
# the full enterprise extension. Out-of-v1 core attributes (nickName, ims, photos, groups,
# ...) are intentionally absent so the round-trip is exact under this issue's scope; the
# enterprise extension block itself is carried in full, including the complex ``manager``.
ENTERPRISE_USER_JSON = {
    "schemas": [
        "urn:ietf:params:scim:schemas:core:2.0:User",
        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User",
    ],
    "id": "2819c223-7f76-453a-919d-413861904646",
    "externalId": "701984",
    "userName": "bjensen@example.com",
    "name": {
        "formatted": "Ms. Barbara J Jensen, III",
        "familyName": "Jensen",
        "givenName": "Barbara",
    },
    "displayName": "Babs Jensen",
    "emails": [
        {"value": "bjensen@example.com", "type": "work", "primary": True},
    ],
    "active": True,
    "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
        "employeeNumber": "701984",
        "costCenter": "4130",
        "organization": "Universal Studios",
        "division": "Theme Park",
        "department": "Tour Operations",
        "manager": {
            "value": "26118915-6090-4610-87e4-49d8ca9f808d",
            "$ref": "https://example.com/v2/Users/26118915-6090-4610-87e4-49d8ca9f808d",
            "displayName": "John Smith",
        },
    },
    "meta": {
        "resourceType": "User",
        "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
    },
}


def test_enterprise_user_round_trips_rfc_example():
    assert wire(User.model_validate(ENTERPRISE_USER_JSON)) == ENTERPRISE_USER_JSON


def test_enterprise_extension_parses_into_typed_models():
    user = User.model_validate(ENTERPRISE_USER_JSON)
    assert isinstance(user.enterprise_user, EnterpriseUser)
    assert isinstance(user.enterprise_user.manager, Manager)


def test_enterprise_extension_maps_camel_case_aliases_to_snake_case_fields():
    enterprise = User.model_validate(ENTERPRISE_USER_JSON).enterprise_user
    assert enterprise.employee_number == "701984"
    assert enterprise.cost_center == "4130"
    assert enterprise.manager.display_name == "John Smith"


def test_enterprise_urn_lands_in_schemas_when_set_without_explicit_schemas():
    user = User(user_name="bjensen", enterprise_user=EnterpriseUser(department="Tour Operations"))
    assert user.schemas == [CORE_USER_SCHEMA, ENTERPRISE_USER_SCHEMA]


def test_enterprise_extension_serializes_under_the_urn_key():
    user = User(user_name="bjensen", enterprise_user=EnterpriseUser(department="Tour Operations"))
    assert wire(user)[ENTERPRISE_USER_SCHEMA] == {"department": "Tour Operations"}


def test_manager_ref_uses_dollar_ref_alias_on_the_wire():
    manager = Manager(
        value="26118915",
        ref="https://example.com/v2/Users/26118915",
        display_name="John Smith",
    )
    assert wire(manager) == {
        "value": "26118915",
        "$ref": "https://example.com/v2/Users/26118915",
        "displayName": "John Smith",
    }


def test_enterprise_urn_is_not_duplicated_when_already_in_schemas():
    user = User.model_validate(ENTERPRISE_USER_JSON)
    assert user.schemas.count(ENTERPRISE_USER_SCHEMA) == 1


def test_user_without_extension_omits_enterprise_urn_and_key():
    user = User(user_name="bjensen")
    assert ENTERPRISE_USER_SCHEMA not in user.schemas
    assert ENTERPRISE_USER_SCHEMA not in wire(user)


def test_enterprise_user_accepts_snake_case_and_serializes_camel_case():
    enterprise = EnterpriseUser(employee_number="701984", cost_center="4130")
    assert enterprise.employee_number == "701984"
    assert wire(enterprise) == {"employeeNumber": "701984", "costCenter": "4130"}
