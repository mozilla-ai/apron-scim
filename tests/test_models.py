"""Contract tests for the core SCIM resource models (issue #9, ADR 0001 section 5).

Covers User, Group, their multi-valued sub-attributes (Name, Email, PhoneNumber,
Address, GroupMember), and Meta. The headline acceptance criterion is a parse-then-
serialize round-trip against RFC 7643 example User/Group JSON, which exercises the
whole serialization contract at once: snake_case fields, SCIM camelCase aliases, the
``$ref`` explicit alias, datetime handling on Meta, and omission of unset attributes.

EnterpriseUser (#10) and the protocol messages (#11) are out of scope here.
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from apron_scim import (
    Address,
    Email,
    Group,
    GroupMember,
    Meta,
    Name,
    PhoneNumber,
    User,
)
from apron_scim.models import _ScimModel


def wire(model: _ScimModel) -> dict[str, Any]:
    """Serialize a model exactly as the library emits it on the SCIM wire."""
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


# RFC 7643 section 8.2 (Barbara Jensen), reduced to the v1-scoped User attributes:
# the enterprise extension and out-of-v1 attributes (ims, photos, groups, roles, ...)
# are intentionally absent so the round-trip is exact under this issue's scope.
USER_JSON = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
    "id": "2819c223-7f76-453a-919d-413861904646",
    "externalId": "701984",
    "userName": "bjensen@example.com",
    "name": {
        "formatted": "Ms. Barbara J Jensen, III",
        "familyName": "Jensen",
        "givenName": "Barbara",
        "middleName": "Jane",
        "honorificPrefix": "Ms.",
        "honorificSuffix": "III",
    },
    "displayName": "Babs Jensen",
    "emails": [
        {"value": "bjensen@example.com", "type": "work", "primary": True},
        {"value": "babs@jensen.org", "type": "home"},
    ],
    "phoneNumbers": [
        {"value": "555-555-5555", "type": "work"},
    ],
    "addresses": [
        {
            "type": "work",
            "streetAddress": "100 Universal City Plaza",
            "locality": "Hollywood",
            "region": "CA",
            "postalCode": "91608",
            "country": "USA",
            "formatted": "100 Universal City Plaza\nHollywood, CA 91608 USA",
            "primary": True,
        },
    ],
    "active": True,
    "meta": {
        "resourceType": "User",
        "created": "2010-01-23T04:56:22Z",
        "lastModified": "2011-05-13T04:42:34Z",
        "version": 'W/"3694e05e9dff590"',  # pragma: allowlist secret
        "location": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
    },
}

# RFC 7643 section 8.4 Group representation.
GROUP_JSON = {
    "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
    "id": "e9e30dba-f08f-4109-8486-d5c6a331660a",
    "displayName": "Tour Guides",
    "members": [
        {
            "value": "2819c223-7f76-453a-919d-413861904646",
            "$ref": "https://example.com/v2/Users/2819c223-7f76-453a-919d-413861904646",
            "display": "Babs Jensen",
        },
        {
            "value": "902c246b-6245-4190-8e05-00816be7344a",
            "$ref": "https://example.com/v2/Users/902c246b-6245-4190-8e05-00816be7344a",
            "display": "Mandy Pepperidge",
        },
    ],
    "meta": {
        "resourceType": "Group",
        "created": "2010-01-23T04:56:22Z",
        "lastModified": "2011-05-13T04:42:34Z",
        "version": 'W/"3694e05e9dff592"',  # pragma: allowlist secret
        "location": "https://example.com/v2/Groups/e9e30dba-f08f-4109-8486-d5c6a331660a",
    },
}


def test_user_round_trips_rfc_example():
    assert wire(User.model_validate(USER_JSON)) == USER_JSON


def test_group_round_trips_rfc_example():
    assert wire(Group.model_validate(GROUP_JSON)) == GROUP_JSON


def test_user_parses_nested_sub_attributes_into_models():
    user = User.model_validate(USER_JSON)
    assert isinstance(user.name, Name)
    assert isinstance(user.emails[0], Email)
    assert isinstance(user.phone_numbers[0], PhoneNumber)
    assert isinstance(user.addresses[0], Address)
    assert isinstance(user.meta, Meta)


def test_group_parses_members_into_models():
    group = Group.model_validate(GROUP_JSON)
    assert all(isinstance(member, GroupMember) for member in group.members)


def test_user_name_is_required():
    with pytest.raises(ValidationError):
        User.model_validate({"schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"]})


def test_group_display_name_is_required():
    with pytest.raises(ValidationError):
        Group.model_validate({"schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"]})


def test_user_accepts_snake_case_field_names():
    user = User(user_name="bjensen", external_id="701984")
    assert user.user_name == "bjensen"
    assert user.external_id == "701984"


def test_user_defaults_schemas_to_core_urn():
    assert User(user_name="bjensen").schemas == ["urn:ietf:params:scim:schemas:core:2.0:User"]


def test_group_defaults_schemas_to_core_urn():
    assert Group(display_name="Tour Guides").schemas == ["urn:ietf:params:scim:schemas:core:2.0:Group"]


def test_minimal_user_omits_unset_attributes():
    assert wire(User(user_name="bjensen")) == {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "userName": "bjensen",
    }


def test_group_member_ref_uses_dollar_ref_alias_on_the_wire():
    member = GroupMember(value="2819c223", ref="https://example.com/v2/Users/2819c223")
    assert wire(member) == {"value": "2819c223", "$ref": "https://example.com/v2/Users/2819c223"}


def test_group_member_accepts_dollar_ref_on_input():
    member = GroupMember.model_validate({"value": "2819c223", "$ref": "https://example.com/x"})
    assert member.ref == "https://example.com/x"


def test_name_maps_camel_case_aliases_to_snake_case_fields():
    name = Name.model_validate(USER_JSON["name"])
    assert name.family_name == "Jensen"
    assert name.given_name == "Barbara"
    assert name.honorific_prefix == "Ms."
    assert name.honorific_suffix == "III"


def test_address_maps_camel_case_aliases_to_snake_case_fields():
    address = Address.model_validate(USER_JSON["addresses"][0])
    assert address.street_address == "100 Universal City Plaza"
    assert address.postal_code == "91608"
    assert address.type == "work"
    assert address.primary is True


def test_email_carries_value_type_display_and_primary():
    email = Email(value="babs@jensen.org", type="home", display="Babs", primary=False)
    assert (email.value, email.type, email.display, email.primary) == ("babs@jensen.org", "home", "Babs", False)


def test_meta_parses_timestamps_as_datetimes():
    meta = Meta.model_validate(USER_JSON["meta"])
    assert meta.created == datetime(2010, 1, 23, 4, 56, 22, tzinfo=UTC)
    assert meta.last_modified == datetime(2011, 5, 13, 4, 42, 34, tzinfo=UTC)
    assert meta.resource_type == "User"


def test_user_is_frozen():
    user = User(user_name="bjensen")
    with pytest.raises(ValidationError):
        user.user_name = "someone-else"


def test_unknown_attributes_are_ignored_on_input():
    user = User.model_validate({"userName": "bjensen", "unknownField": "dropped"})
    assert not hasattr(user, "unknownField")
    assert "unknownField" not in wire(user)
