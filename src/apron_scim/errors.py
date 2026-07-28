"""Exception hierarchy for apron_scim SCIM operations."""


class ScimError(Exception):
    """Base exception for all apron_scim errors.

    The concrete subclasses and their (HTTP status, scimType) mapping per RFC 7644
    section 3.12 are defined in Epic 1.
    """
