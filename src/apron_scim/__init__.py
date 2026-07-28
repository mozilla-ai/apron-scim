"""Stateless server-side SCIM 2.0 protocol library.

apron_scim implements the SCIM 2.0 service-provider role (RFC 7643/7644): it receives
user and group provisioning from a customer identity provider and shapes the protocol
layer — schema, filter parsing, PATCH, and request/response — while the consumer owns
persistence and HTTP routing.

The public surface is ratified in Epic 1 and lands per epic. This scaffold exposes only
the base error type.
"""

import logging

from apron_scim.errors import ScimError

# Keep the library silent until the application opts in; configuring the ``apron_scim``
# logger in any way replaces this handler.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "ScimError",
]
