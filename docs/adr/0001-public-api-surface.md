# ADR 0001: Public API surface & `ResourceStore` contract

- **Status:** Accepted
- **Date:** 2026-07-29
- **Issue:** [#8](https://github.com/mozilla-ai/apron-scim/issues/8) — Epic 1 ([#2](https://github.com/mozilla-ai/apron-scim/issues/2))
- **Supersedes/companions:** `plan.md`, `design.md` (public API surface section), bring-up runbook §4

## Context

`apron-scim` is a stateless, server-side SCIM 2.0 protocol library in the `apron-*`
family. It owns the SCIM protocol layer (schema, filter parsing, PATCH, request/response
shaping) for the RFC 7644 **service-provider** role; the consumer (onoma) owns HTTP
routing, persistence, and filter-AST→database translation.

Every downstream `feat(...)` issue in Epics 1–4 codes against one public contract. This
ADR ratifies that contract so those issues conform rather than each re-deciding a facet
of it. The contract is also encoded as typed skeletons under `src/apron_scim/` (Protocols,
enums, dataclasses, method signatures) so it is machine-checked by `ty` before the
behavioral bodies exist.

Decisions carried in from `plan.md`/`design.md` and **not reopened here**: the
service-provider (not client) role; own SCIM-shaped models rather than a shared identity
library; pure-Python with `pydantic` as the sole runtime dependency; async throughout.

## Decision

### 1. Package surface (`from apron_scim import …`)

The public surface is exactly the alphabetized `__init__.__all__` below (46 names).
Everything else — the filter tokenizer/parser internals, the PATCH applier, the
service's shaping helpers, and the `_ScimModel` base — is module-private and may change
without notice.

```
Address, And, CompareOp, Comparison, Email, EnterpriseUser, FilterNode, FilterVisitor,
Group, GroupMember, InvalidFilter, InvalidPath, InvalidSyntax, InvalidValue, ListQuery,
ListResponse, MemoryResourceStore, Meta, Mutability, Name, NoTarget, Not, Or, Page,
PatchOp, PatchOperation, PhoneNumber, PreconditionFailed, Present, Resource, ResourceKind,
ResourceNotFound, ResourceStore, ResourceType, SchemaDefinition, ScimError,
ScimErrorResponse, ScimResponse, ScimServiceProvider, ServiceProviderConfig, SortOrder,
TooMany, Uniqueness, User, ValuePath, parse_filter
```

**Additions beyond the runbook §4c sketch, with rationale** (the runbook flagged the
exact `__all__` as an ADR item to settle):

- `ListQuery`, `Page`, `SortOrder` — a consumer cannot implement `ResourceStore` without
  them; they are the store's query-side contract.
- `Resource` — the `User | Group` alias the store methods are typed in terms of.
- `Comparison`, `Present`, `And`, `Or`, `Not`, `ValuePath` — a `FilterVisitor` receives
  these node types; they must be importable to be matched.
- `PatchOperation`, `ScimErrorResponse` — enumerated in `design.md`'s model list;
  exported for consumers that construct or parse those structures. They are primarily
  produced/consumed internally, but exporting them costs nothing and completes the
  documented model set.

**Module layout** (`src/apron_scim/`): `models.py` · `schema.py` · `filter.py` ·
`patch.py` · `protocols.py` · `service.py` · `stores.py` · `errors.py` · `__init__.py`
· `py.typed`. `ScimResponse` lives in `service.py`; `ListQuery`/`Page`/`SortOrder` in
`protocols.py`; `ResourceKind` in `models.py`.

### 2. `ScimServiceProvider` — the facade

Framework-agnostic. Constructed once, then one method per SCIM operation. Every method
returns a `ScimResponse`; the facade catches every `ScimError` internally and returns a
well-formed error response, so **callers never map exceptions**. Non-SCIM exceptions
(bugs) propagate.

```python
class ScimServiceProvider:
    def __init__(self, store: ResourceStore, *, base_url: str,
                 config: ServiceProviderConfig | None = None) -> None: ...

    async def create(self, resource_kind: ResourceKind, body: dict[str, Any]) -> ScimResponse: ...
    async def get(self, resource_kind: ResourceKind, resource_id: str, *,
                  attributes: Sequence[str] | None = None,
                  excluded_attributes: Sequence[str] | None = None) -> ScimResponse: ...
    async def replace(self, resource_kind: ResourceKind, resource_id: str, body: dict[str, Any]) -> ScimResponse: ...
    async def patch(self, resource_kind: ResourceKind, resource_id: str, body: dict[str, Any]) -> ScimResponse: ...
    async def delete(self, resource_kind: ResourceKind, resource_id: str) -> ScimResponse: ...
    async def list(self, resource_kind: ResourceKind, query_params: Mapping[str, str]) -> ScimResponse: ...
    async def service_provider_config(self) -> ScimResponse: ...
    async def resource_types(self) -> ScimResponse: ...
    async def schemas(self) -> ScimResponse: ...
```

- **Inputs are primitives.** `resource_kind`, ids, a **parsed JSON `dict`** body, and a
  raw `query_params` mapping. JSON parsing is not SCIM-specific — the HTTP layer already
  did it — so the library stays free of stream/HTTP concerns and is testable with plain
  dicts.
- `get` takes already-split `attributes`/`excluded_attributes`; `list` takes the raw
  query mapping because it must parse `filter`/`sortBy`/`sortOrder`/`startIndex`/`count`
  itself.
- `patch` is applied library-side (get → apply → replace); the store has no `patch`.
- `list` is the ratified method name (maps to `GET` on a collection); it deliberately
  shadows the builtin only as an attribute name.

### 3. `ScimResponse` — the response shape

```python
@dataclass(frozen=True, slots=True)
class ScimResponse:
    status: int
    body: dict[str, Any] | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
```

- A **frozen dataclass**, not a Pydantic model: it is a transport envelope, not a SCIM
  wire object, and carries no validation.
- `status` is the **HTTP** status (`int`). `body` is the already-shaped, JSON-serializable
  `dict` (or `None` for a body-less response such as a 204 DELETE) — a `dict` rather than
  a model so the caller serializes it directly with no re-modeling and no double
  validation.
- `headers` carries `ETag`, `Location`, and `Content-Type: application/scim+json`.

### 4. `ResourceStore` — the persistence seam

```python
@runtime_checkable
class ResourceStore(Protocol):
    async def create(self, resource: Resource) -> Resource: ...
    async def get(self, resource_kind: ResourceKind, resource_id: str) -> Resource | None: ...
    async def replace(self, resource: Resource) -> Resource: ...
    async def delete(self, resource_kind: ResourceKind, resource_id: str) -> None: ...
    async def query(self, query: ListQuery) -> Page: ...
```

```python
class SortOrder(StrEnum):        # "ascending" | "descending"

@dataclass(frozen=True, slots=True)
class ListQuery:
    resource_kind: ResourceKind
    filter: FilterNode | None = None
    start_index: int = 1
    count: int | None = None
    sort_by: str | None = None
    sort_order: SortOrder | None = None

@dataclass(frozen=True, slots=True)
class Page:
    resources: Sequence[Resource]
    total_results: int
```

- **No `patch` method** — the library applies PATCH. The store exposes only
  full-resource operations.
- The service parses the raw query into a `ListQuery`, so a store never sees SCIM query
  syntax; it applies the filter (via a `FilterVisitor` it writes), the sort, and the
  page slice, and returns the page plus the total match count.
- **A store may raise `ScimError` subclasses** to signal persistence conflicts —
  `Uniqueness` (duplicate `userName`/`externalId`), `ResourceNotFound` (missing target
  of `replace`/`delete`), `PreconditionFailed` (version conflict). The facade converts
  them to responses. This is why the error hierarchy is public.

#### Ownership: who assigns `id` / `meta` / `version` (resolved open question)

| Field | Owner | When |
|---|---|---|
| `id` | **Store** | assigned on `create`; preserved on `replace` |
| `meta.created` | **Store** | assigned on `create`; preserved on `replace` |
| `meta.lastModified` | **Store** | set on `create`; refreshed on `replace` |
| `meta.version` (ETag) | **Store** | set on `create`; refreshed on `replace` |
| `meta.resourceType` | **Service** | derived from `ResourceKind` |
| `meta.location` | **Service** | composed from `base_url` + endpoint + `id` |

Rationale: identity and versioning are persistence-coupled (DB sequence, row version,
`updated_at`), so the store owns them and is the single source of truth for optimistic
concurrency. `location` and `resourceType` are protocol/URL facts the store should not
know, so the service overlays them (a functional update on the frozen model) before
shaping the response. Concurrency control is the caller's, via `meta.version`.

### 5. Models

All models subclass a private `_ScimModel` base fixing the **serialization contract**:

```python
class _ScimModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True,
                              frozen=True, extra="ignore")
```

- **`frozen=True`** — PATCH/PUT produce a new instance (functional update), matching
  apron-auth and making immutability compatible with mutation semantics.
- **`alias_generator=to_camel` + `populate_by_name=True`** — fields are declared
  `snake_case` and cross the wire as SCIM `camelCase` (`user_name` ↔ `userName`);
  construction accepts either form. **Three attributes need an explicit `Field(alias=…)`
  overriding the generator:** `Resources` (ListResponse), `Operations` (PatchOp), and
  `$ref` (reference sub-attributes).
- **`extra="ignore"`** — unknown attributes are dropped on input; strict schema and
  mutability validation is applied explicitly by the service/schema layer, not by
  rejecting extras at the model. Extensions are modeled as explicit fields keyed by their
  URN, not by opening the model.
- **Wire serialization** is `model_dump(mode="json", by_alias=True, exclude_none=True)`
  so absent attributes are omitted (SCIM omits, not nulls, unset attributes).

`ResourceKind` (`StrEnum`: `USER="User"`, `GROUP="Group"`) is the closed discriminator
keying store/service operations. It is **distinct from** `ResourceType`, the RFC 7643
discovery model at `/ResourceTypes`; the enum's values double as `meta.resourceType`.

Field tables below are the ratified contract; `feat(models)`/`feat(schema)` transcribe
them. **Adding a further optional RFC 7643 attribute later is backward-compatible and
does not require a new ADR;** removing or renaming one, or changing the surface in §1–4,
does.

**Common attributes** (RFC 7643 §3.1; on `User`, `Group`):

| SCIM attr | Type | Notes |
|---|---|---|
| `schemas` | `list[str]` | required; core schema URN + any extension URNs |
| `id` | `str \| None` | server-assigned; `None` before create |
| `externalId` | `str \| None` | client-supplied correlation id |
| `meta` | `Meta \| None` | see below |

**`User`** (RFC 7643 §4.1, `urn:ietf:params:scim:schemas:core:2.0:User`) — v1 scope:
`userName` (`str`, required), `name` (`Name | None`), `displayName` (`str | None`),
`emails` (`list[Email]`), `phoneNumbers` (`list[PhoneNumber]`), `addresses`
(`list[Address]`), `active` (`bool | None`), plus common attributes and the enterprise
extension field (below). Other RFC 7643 User attributes (`ims`, `photos`, `entitlements`,
`roles`, `x509Certificates`, `groups`, `password`) are out of v1 scope and may be added
later as optional fields.

**`Group`** (RFC 7643 §4.2, `urn:ietf:params:scim:schemas:core:2.0:Group`):
`displayName` (`str`, required), `members` (`list[GroupMember]`), plus common attributes.

**`EnterpriseUser`** (RFC 7643 §4.3,
`urn:ietf:params:scim:schemas:extension:enterprise:2.0:User`): `employeeNumber`,
`costCenter`, `organization`, `division`, `department` (all `str | None`), `manager`
(complex: `value`, `$ref`, `displayName`). Carried on `User` as an optional field aliased
to the extension URN, with the URN added to `schemas`.

**Sub-attributes:**

| Model | Fields |
|---|---|
| `Name` | `formatted`, `familyName`, `givenName`, `middleName`, `honorificPrefix`, `honorificSuffix` (all `str \| None`) |
| `Email` | `value`, `type`, `display` (`str \| None`), `primary` (`bool \| None`) |
| `PhoneNumber` | `value`, `type`, `display` (`str \| None`), `primary` (`bool \| None`) |
| `Address` | `formatted`, `streetAddress`, `locality`, `region`, `postalCode`, `country`, `type` (`str \| None`), `primary` (`bool \| None`) |
| `GroupMember` | `value` (member id), `$ref`, `type`, `display` (`str \| None`) |
| `Meta` | `resourceType`, `location`, `version` (`str \| None`); `created`, `lastModified` (`datetime \| None`) |

**Protocol messages** (RFC 7644):

| Model | Schema URN / fields |
|---|---|
| `ListResponse` | `urn:…:messages:2.0:ListResponse`; `schemas`, `totalResults` (`int`), `startIndex` (`int`), `itemsPerPage` (`int`), `Resources` (`list`, explicit alias) |
| `PatchOp` | `urn:…:messages:2.0:PatchOp`; `schemas`, `Operations` (`list[PatchOperation]`, explicit alias) |
| `PatchOperation` | `op` (`"add"`/`"remove"`/`"replace"`), `path` (`str \| None`), `value` (`Any \| None`) |
| `ScimErrorResponse` | `urn:…:messages:2.0:Error`; `schemas`, `status` (`str`), `scimType` (`str \| None`), `detail` (`str \| None`) |

**Discovery models** (`schema.py`, RFC 7643 §5–7): `ServiceProviderConfig` (advertised
`patch`/`bulk`/`filter`/`changePassword`/`sort`/`etag` capabilities + `authenticationSchemes`),
`ResourceType` (`name`, `endpoint`, `schema`, `schemaExtensions`), `SchemaDefinition`
(`id`, `name`, `attributes` — the attribute-definition models: `mutability`, `returned`,
`uniqueness`, `caseExact`, …). Field detail is `feat(schema)`'s to fill per RFC 7643.

### 6. Filter AST + visitor (`filter.py`)

```python
def parse_filter(expr: str) -> FilterNode: ...   # raises InvalidFilter on malformed input

class CompareOp(StrEnum):   # eq ne co sw ew gt ge lt le   (presence "pr" is the Present node)

FilterNode = Comparison | Present | And | Or | Not | ValuePath
```

| Node | Fields |
|---|---|
| `Comparison` | `attribute_path: str`, `op: CompareOp`, `value: str \| int \| float \| bool \| None` |
| `Present` | `attribute_path: str` (the `attr pr` presence test) |
| `And` | `left: FilterNode`, `right: FilterNode` |
| `Or` | `left: FilterNode`, `right: FilterNode` |
| `Not` | `operand: FilterNode` |
| `ValuePath` | `attribute_path: str`, `predicate: FilterNode` (e.g. `emails[type eq "work"]`) |

All nodes are frozen slotted dataclasses. **Comparison values are carried as parsed
data, never interpolated into a query string**, so a `FilterVisitor` cannot be coerced
into query injection.

`FilterVisitor[T]` is an **abstract base class** (not a Protocol) consumers subclass to
emit their query language:

```python
class FilterVisitor(ABC, Generic[T]):
    def visit(self, node: FilterNode) -> T: ...        # concrete: dispatches on node type
    @abstractmethod
    def visit_comparison(self, node: Comparison) -> T: ...
    @abstractmethod
    def visit_present(self, node: Present) -> T: ...
    @abstractmethod
    def visit_and(self, node: And) -> T: ...
    @abstractmethod
    def visit_or(self, node: Or) -> T: ...
    @abstractmethod
    def visit_not(self, node: Not) -> T: ...
    @abstractmethod
    def visit_value_path(self, node: ValuePath) -> T: ...
```

`visit` is the public dispatch entry point (implemented, exhaustively matched so adding a
node type is a type error at the match). Recursion into children is the subclass's
responsibility — `visit_and` typically calls `self.visit(node.left)` /
`self.visit(node.right)` and combines the results.

### 7. Errors → (HTTP status, `scimType`) (`errors.py`, RFC 7644 §3.12)

`ScimError(Exception)` carries `http_status` and `scim_type` (`ClassVar`) plus a
human-readable `detail`, and renders itself with
`to_response() -> ScimResponse`. The error body is
`{"schemas": ["urn:…:messages:2.0:Error"], "status": str(http_status), "scimType": …,
"detail": …}` (`scimType`/`detail` omitted when absent); the response sets
`Content-Type: application/scim+json`. Error **messages describe conditions in domain
terms** — no library or internal identifiers.

| Exception | HTTP | `scimType` | Raised when |
|---|---|---|---|
| `ScimError` (base) | 500 | — | generic/unexpected failure |
| `InvalidFilter` | 400 | `invalidFilter` | malformed or unsupported filter |
| `InvalidValue` | 400 | `invalidValue` | missing/incompatible value |
| `InvalidSyntax` | 400 | `invalidSyntax` | malformed request body structure |
| `InvalidPath` | 400 | `invalidPath` | malformed PATCH `path` |
| `NoTarget` | 400 | `noTarget` | PATCH `path` matched nothing operable |
| `Mutability` | 400 | `mutability` | modification violates attribute mutability |
| `Uniqueness` | 409 | `uniqueness` | duplicate/reserved value (RFC 7644 §3.3) |
| `TooMany` | 400 | `tooMany` | filter matches more than the service will process |
| `ResourceNotFound` | 404 | — | no resource for the kind + id |
| `PreconditionFailed` | 412 | — | resource changed on the server (ETag mismatch) |

`uniqueness` is `409` per RFC 7644 §3.3; `ResourceNotFound`/`PreconditionFailed` carry no
`scimType` (none is defined for `404`/`412`).

## Consequences

- **Downstream issues are pure implementation.** `feat(models)` transcribes §5 field
  tables; `feat(filter)` fills `parse_filter`/tokenizer against the §6 AST; `feat(patch)`
  writes the applier the facade calls; `feat(service)` wires the §2 handlers and §4
  ownership; `feat(errors)` adds tests/message polish to the §7 hierarchy;
  `feat(schema)` details discovery models. None re-decides a signature.
- **The contract is machine-checked now.** The encoded skeletons pass `ty` and a smoke
  suite that locks the export list, the error mapping, the store protocol conformance,
  and the model serialization contract before any body exists.
- **Scoped lint deviation:** `errors.py` is exempt from `N818` (Error-suffix rule)
  because the subclasses are named for their RFC 7644 `scimType` keywords.
- **What is deliberately encoded ahead of its feat issue** (because it *is* the ratified
  contract, not behavior): the error status/`scimType` table + `to_response` body shape,
  the `FilterVisitor.visit` dispatch, and the model serialization base. Behavioral bodies
  (parsing, orchestration, persistence, PATCH application, model fields) remain stubs
  raising `NotImplementedError`.
