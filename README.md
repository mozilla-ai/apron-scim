# apron-scim

Stateless **server-side** SCIM 2.0 protocol library — the service-provider role of
[RFC 7643](https://www.rfc-editor.org/rfc/rfc7643)/[RFC 7644](https://www.rfc-editor.org/rfc/rfc7644).
It receives user and group provisioning from a customer identity provider and owns the
protocol layer (schema, filter parsing, PATCH, request/response shaping), while the
consumer supplies persistence and HTTP routing.

Part of the `apron-*` family of stateless protocol primitives.

> **Status: early scaffolding.** The public API surface is being ratified (Epic 1) and
> features land per epic — see the issue backlog. Not yet published to PyPI.

## Installation

```bash
uv add apron-scim
# or
pip install apron-scim
```

## Scope

- **In:** SCIM service-provider protocol — resource/schema models, filter parsing
  (→ AST + visitor), PATCH application, discovery documents, and framework-agnostic
  request/response handlers.
- **Out (by design):** persistence, HTTP routing, and the outbound SCIM *client*. The
  consumer implements a `ResourceStore` and wires its own routes.

## Development

```bash
make setup   # bootstrap uv, venv, and pre-commit hooks
make test    # run the unit suite
make lint    # run pre-commit (ruff, ruff-format, detect-secrets, ty, uv-lock)
```

## License

Apache-2.0.
