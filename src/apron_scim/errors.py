"""Exception hierarchy for apron_scim SCIM operations.

Each error maps to a (HTTP status, scimType) pair per RFC 7644 section 3.12 and
renders itself as a SCIM error response via :meth:`ScimError.to_response`. The service
raises these internally — and a store may raise :class:`Uniqueness`,
:class:`ResourceNotFound`, or :class:`PreconditionFailed` to signal persistence
conflicts — and the facade converts them to error responses so callers never map
exceptions. See docs/adr/0001-public-api-surface.md for the full table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from apron_scim.service import ScimResponse

ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"
"""Schema URI for a SCIM error response body (RFC 7644 section 3.12)."""


class ScimError(Exception):
    """Base exception for all apron_scim errors.

    Attributes:
        http_status: The HTTP status this error maps to.
        scim_type: The ``scimType`` detail keyword (RFC 7644 section 3.12), or ``None``
            for errors that carry no such keyword.
        detail: A human-readable explanation, stated in domain terms.
    """

    http_status: ClassVar[int] = 500
    scim_type: ClassVar[str | None] = None

    def __init__(self, detail: str = "") -> None:
        """Create the error.

        Args:
            detail: A human-readable explanation of the failure.
        """
        super().__init__(detail)
        self.detail = detail

    def to_response(self) -> ScimResponse:
        """Render this error as a SCIM error response (RFC 7644 section 3.12).

        Returns:
            A response whose body carries the error schema, stringified status, the
            ``scimType`` when defined, and the detail when present.
        """
        # Imported here rather than at module scope so this module does not depend on
        # apron_scim.service at import time (the service depends on this one).
        from apron_scim.service import SCIM_CONTENT_TYPE, ScimResponse

        body: dict[str, object] = {"schemas": [ERROR_SCHEMA], "status": str(self.http_status)}
        if self.scim_type is not None:
            body["scimType"] = self.scim_type
        if self.detail:
            body["detail"] = self.detail
        return ScimResponse(status=self.http_status, body=body, headers={"Content-Type": SCIM_CONTENT_TYPE})


class InvalidFilter(ScimError):
    """A filter expression was syntactically invalid or its comparison is unsupported."""

    http_status = 400
    scim_type = "invalidFilter"


class InvalidValue(ScimError):
    """A required value was missing or incompatible with the operation, attribute, or schema."""

    http_status = 400
    scim_type = "invalidValue"


class InvalidSyntax(ScimError):
    """The request body structure was invalid or did not conform to the schema."""

    http_status = 400
    scim_type = "invalidSyntax"


class InvalidPath(ScimError):
    """A PATCH ``path`` attribute was invalid or malformed."""

    http_status = 400
    scim_type = "invalidPath"


class NoTarget(ScimError):
    """A PATCH ``path`` matched no attribute or value that could be operated on."""

    http_status = 400
    scim_type = "noTarget"


class Mutability(ScimError):
    """A modification conflicted with the target attribute's mutability or current state."""

    http_status = 400
    scim_type = "mutability"


class Uniqueness(ScimError):
    """An attribute value is already in use or reserved (RFC 7644 section 3.3)."""

    http_status = 409
    scim_type = "uniqueness"


class TooMany(ScimError):
    """A filter matched more results than the service is willing to process."""

    http_status = 400
    scim_type = "tooMany"


class ResourceNotFound(ScimError):
    """No resource exists for the requested kind and id."""

    http_status = 404


class PreconditionFailed(ScimError):
    """The resource changed on the server, so a version-conditional request cannot proceed."""

    http_status = 412
