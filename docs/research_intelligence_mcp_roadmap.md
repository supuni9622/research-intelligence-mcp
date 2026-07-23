# Research Intelligence MCP

## Implementation Roadmap

**Current version:** 0.1.0  
**Current milestone:** Phase 6 — Research MCP Tools  
**Primary providers:** Semantic Scholar and arXiv

---

# Status Legend

| Symbol | Meaning |
|---|---|
| ✅ | Completed |
| 🟡 | In progress |
| 🔲 | Not started |
| ⏸️ | Deferred |

---

# Phase 0 — Project Foundation

**Status:** ✅ Completed

## Deliverables

- [x] Git-ready repository structure
- [x] Python 3.12 project
- [x] `uv` package and dependency management
- [x] `src/` package layout
- [x] Unique `research_intelligence_mcp` namespace
- [x] `pyproject.toml`
- [x] Runtime dependency configuration
- [x] Development dependency configuration
- [x] Pydantic environment settings
- [x] Immutable cached configuration
- [x] Structured logging
- [x] Logging to stderr for MCP stdio safety
- [x] Ruff formatting and linting
- [x] Mypy strict type checking
- [x] Pytest setup
- [x] Environment template
- [x] Git ignore rules
- [x] README
- [x] Product requirements document
- [x] Implementation roadmap

## Completion evidence

- Project installs successfully with `uv sync`
- Ruff passes
- Mypy passes
- Unit tests pass
- Package entry point is executable

---

# Phase 1 — Core MCP Server

**Status:** ✅ Completed

## Deliverables

- [x] Official MCP Python SDK
- [x] FastMCP server
- [x] Server factory
- [x] Server instructions
- [x] stdio transport startup
- [x] CLI entry point
- [x] Python module entry point
- [x] Structured `health_check` tool
- [x] Application dependency container
- [x] Explicit dependency injection
- [x] Dependency-container tests
- [x] MCP Inspector validation
- [x] Tool discovery through `tools/list`
- [x] Tool execution through `tools/call`
- [x] Structured output-schema validation
- [x] Ruff, Mypy, Pytest, and package-build quality gates

## Exit criteria

Phase 1 is complete when:

- server dependencies are created outside the tool layer;
- tools receive dependencies explicitly;
- no infrastructure is initialized at module import time;
- the server connects through MCP Inspector;
- `health_check` returns valid structured output;
- Ruff, Mypy, and Pytest pass.

---

# Phase 2 — Canonical Domain Models

**Status:** ✅ Completed

## Deliverables

- [x] Shared canonical domain base model
- [x] Provider enumeration
- [x] Identifier type enumeration
- [x] Access status enumeration
- [x] Paper relationship enumeration
- [x] Search sort enumeration
- [x] DOI normalization and validation
- [x] arXiv identifier normalization and validation
- [x] `Author`
- [x] `PaperIdentifiers`
- [x] Preferred identifier policy
- [x] `PaperAccess`
- [x] `Paper`
- [x] `PaperReference`
- [x] `SearchRequest`
- [x] `PaginationMetadata`
- [x] `ProviderFailure`
- [x] `SearchResult`
- [x] Partial provider-failure contract
- [x] Domain validation rules
- [x] Immutable canonical models
- [x] Unknown-field rejection
- [x] JSON serialization contracts
- [x] JSON round-trip validation
- [x] JSON Schema generation
- [x] Domain-model unit tests
- [x] Ruff, Mypy, Pytest, and package build quality gates

## Architecture requirements

- Provider response schemas must not leak into services or MCP tools.
- Canonical models must remain provider-neutral.
- Models must use strict validation.
- Models returned by MCP tools must have stable JSON schemas.

```
Provider response
      │
      ▼
Provider-specific model
      │
      ▼
Provider mapper
      │
      ▼
Canonical domain model
      │
      ├── Paper
      ├── Author
      ├── PaperIdentifiers
      ├── PaperAccess
      └── PaperReference
      │
      ▼
Service layer
      │
      ▼
MCP structured output
```

---

# Phase 3 — Semantic Scholar Provider

**Status:** ✅ Completed

## 3.1 Configuration and Infrastructure

### Deliverables

- [x] Semantic Scholar settings
- [x] Environment variables
- [x] Optional API-key support
- [x] Shared async HTTP infrastructure
- [x] HTTP client lifecycle management
- [x] Connection pooling
- [x] Timeouts
- [x] Provider-specific retry handling
- [x] Exponential backoff with jitter
- [x] `Retry-After` support
- [x] Provider-aware rate limiting

## 3.2 Provider Response Models

### Deliverables

- [x] Author response models
- [x] Paper response models
- [x] Search response models
- [x] Citation response models
- [x] Reference response models
- [x] Recommendation response models
- [x] Error response models
- [x] Forward-compatible response handling
- [x] Unknown-field ignoring

## 3.3 Provider Client

### Deliverables

- [x] Search endpoint client
- [x] Paper retrieval client
- [x] Citation retrieval client
- [x] Reference retrieval client
- [x] Recommendations API client
- [x] API-key header handling
- [x] Retry handling
- [x] Transport error handling
- [x] Response validation
- [x] Error normalization

## 3.4 Canonical Mapping Layer

### Deliverables

- [x] Author mapping
- [x] Paper mapping
- [x] Identifier normalization
- [x] `CorpusId` normalization
- [x] URL normalization
- [x] Open-access mapping
- [x] Citation mapping
- [x] Reference mapping
- [x] Search-result mapping
- [x] Provider-neutral outputs

## 3.5 Provider Implementation

### Deliverables

- [x] Provider interface
- [x] Search papers
- [x] Get paper
- [x] Get citations
- [x] Get references
- [x] Get recommendations
- [x] Dependency wiring
- [x] Composition root

## 3.6 Error Handling

### Deliverables

- [x] `ProviderError`
- [x] `ProviderAuthenticationError`
- [x] `ProviderNotFoundError`
- [x] `ProviderRateLimitError`
- [x] `ProviderTransportError`
- [x] `ProviderUpstreamError`
- [x] `ProviderResponseError`
- [x] Retry metadata support

## 3.7 Testing

### Deliverables

- [x] Mapper tests
- [x] Mock transport tests
- [x] Search tests
- [x] Authentication tests
- [x] Rate-limit tests
- [x] Mypy validation
- [x] Ruff validation
- [x] Pytest validation

## Capabilities

- [x] Search papers
- [x] Retrieve paper details
- [x] Retrieve citations
- [x] Retrieve references
- [x] Retrieve related papers
- [x] Resolve open-access metadata

## Exit Criteria

Phase 3 is complete when:

- The provider layer is fully isolated.
- Canonical models are returned everywhere.
- Semantic Scholar API keys remain optional.
- The full quality gate passes.
- The provider works entirely through dependency injection.
- No provider schemas leak outside provider boundaries.

---

# Phase 4 — arXiv Provider

**Status:** ✅ Completed

## Deliverables

### Infrastructure

- [x] arXiv settings
- [x] Async Atom client
- [x] Safe XML parsing
- [x] Provider-aware rate limiting
- [x] Retry handling

### Response Models

- [x] Atom feed models
- [x] Entry models
- [x] Author models
- [x] Category models
- [x] Link models

### Mapping Layer

- [x] arXiv-to-canonical mapping
- [x] Version normalization
- [x] PDF URL mapping
- [x] Identifier normalization

### Provider Layer

- [x] Search papers
- [x] Get paper
- [ ] Search by author
- [ ] Search by category
- [x] Resolve PDF URLs
- [x] Resolve abstract pages

### Testing

- [x] XML fixture tests
- [x] Mapper tests
- [x] Provider tests
- [ ] Optional live-provider smoke tests

## Exit Criteria

Phase 4 is complete when:

- Atom responses are parsed safely.
- arXiv versions are normalized consistently.
- Provider responses map only to canonical models.
- Search and paper retrieval work through the provider abstraction.
- Mocked tests cover success and failure paths.
- Ruff, Mypy, Pytest, and package build pass.

---

# Phase 5 — Federated Search Service

**Status:** ✅ Completed

## Deliverables

- [x] Provider registry
- [x] Provider selection
- [x] Concurrent provider execution
- [x] Partial-failure handling
- [x] Search-result aggregation
- [x] Identifier-based deduplication
- [x] Metadata-based deduplication fallback
- [x] Deterministic ranking
- [x] Provider attribution
- [x] Search-service tests

## Exit Criteria

- A single request can query one or both providers.
- Failure from one provider does not discard successful results from another.
- Duplicate papers are merged without losing provenance.
- Result ordering is deterministic.

---

# Phase 6 — Research MCP Tools

**Status:** 🟡 In Progress

## Deliverables

- [x] `search_papers`
- [x] `search_arxiv`
- [x] `get_paper`
- [x] `get_related_papers` - but need to fix some issues
- [x] `get_paper_citations` - but need to fix some issues
- [x] `get_paper_references` - but need to fix some issues
- [x] `resolve_paper_access`
- [x] Stable tool description for `search_papers`
- [x] Validated input model for `search_papers`
- [x] Structured provider-neutral output for `search_papers`
- [x] MCP Inspector validation for `search_papers`
- [x] Tool-level tests for `search_papers`
- [x] Server registration and tool discovery validation
- [x] Federated partial-failure output exposed through MCP
- [ ] Provider-aware field-of-study translation
- [ ] Unsupported field-filter warnings
- [x] Remaining tool descriptions
- [x] Remaining validated input models
- [x] Remaining structured output models
- [x] Remaining MCP Inspector validation
- [x] Remaining tool-level tests

## Tool Design Requirements

- Tool names must describe capabilities clearly.
- Inputs must be bounded and validated.
- Outputs must be provider-neutral.
- Errors must be safe and actionable.
- Tools must not perform LLM reasoning or report generation.
- Canonical field filters must be translated into provider-specific query formats.
- Unsupported provider filters must be ignored safely and returned as actionable warnings.

---

# Phase 7 — Reliability and Infrastructure

**Status:** 🟡 Partially Completed

## Completed

- [x] Shared async HTTP infrastructure
- [x] Connection pooling
- [x] Timeouts
- [x] Retry policies
- [x] Backoff with jitter
- [x] Provider-aware rate limiting
- [x] Graceful provider shutdown
- [x] Failure normalization
- [x] Bounded in-memory caching
- [x] Separate search and paper caches
- [x] TTL-based expiration
- [x] LRU eviction
- [x] Async-safe cache access
- [x] Deterministic cache keys
- [x] Cache hit, miss, write, eviction, and expiration statistics
- [x] Successful-response-only caching
- [x] Cache dependency injection and shutdown cleanup
- [x] Cache unit and integration tests

## Remaining

- [ ] Structured provider metrics
- [ ] Sensitive-data-safe logging review
- [ ] Full application graceful shutdown verification
- [ ] CI security scanning

Request correlation IDs are implemented — see Phase 7A.

## Security Requirements

- Use maintained libraries with a clear need.
- Keep the dependency surface minimal.
- Never log API keys or authorization headers.
- Bound all user-controlled limits.
- Parse untrusted XML safely.
- Do not expose raw provider exceptions to MCP clients.
- Commit and review `uv.lock`.
- Run dependency and source scanning in CI.

---

# Phase 7A — Authentication (Stage 2: Service-to-Service JWT)

**Status:** ✅ Completed

See `docs/research_intelligence_mcp_authentication.md` for the full
architecture and the "Stage 2 Configuration Reference" section for settings.

## Deliverables

- [x] `streamable-http` transport option (`MCP_TRANSPORT`, `MCP_HOST`, `MCP_PORT`)
- [x] `AUTH_*` settings with fail-fast validation (issuer/audience/signing-key consistency)
- [x] `JWTBearerTokenVerifier` (`infrastructure/auth/jwt_verifier.py`) implementing the official MCP SDK `TokenVerifier` protocol
- [x] RS256/ES256/PS256 verification via JWKS endpoint (`PyJWKClient`, bounded key cache)
- [x] HS256 verification via shared secret (local/test only)
- [x] Signature, expiry (with leeway), issuer, and audience validation
- [x] Required-scope enforcement wired through `AuthSettings` + the SDK's `RequireAuthMiddleware`
- [x] `stdio` transport unaffected — `AUTH_*` settings have no effect when `MCP_TRANSPORT=stdio`
- [x] No token, secret, or key material logged
- [x] Request correlation (`X-Request-ID` / `X-Correlation-ID`) bound to every tool call's structured logs, with a generated fallback ID under `stdio` (`mcp/observability.py`)
- [x] Bounded, validated `X-Request-Context` (user/tenant/session) passthrough as log-only observability metadata — never the raw user token, never returned in tool output
- [x] All 7 registered MCP tools wrapped in the correlation scope via an MCP SDK `Context` parameter (verified not to leak into any tool's public input schema)
- [x] Settings, verifier, observability, and server-wiring unit tests
- [x] `.env.example` updated
- [x] Ruff, Mypy, Pytest, and package build quality gates

## Deferred to a later milestone

- [ ] Structured provider metrics and a broader sensitive-data logging review (Phase 7)
- [ ] Stage 3 public OAuth (authorization-server provider, dynamic client registration)

---

# Phase 8 — Documentation and Portfolio Readiness

**Status:** 🔲 Not Started

## Deliverables

- [x] Architecture diagram
- [x] Provider flow diagram
- [x] Tool catalogue
- [x] MCP Inspector instructions
- [x] Claude Desktop configuration
- [x] ChatGPT-compatible integration guidance where supported
- [x] Cursor configuration
- [x] Example tool calls and outputs
- [x] Development guide
- [x] Testing guide
- [x] Security considerations
- [x] Portfolio case study
- [ ] Screenshots or demo recording
- [ ] Changelog
- [ ] License

---

# Phase 9 — Continuous Integration

**Status:** ✅ Completed

## Deliverables

- [x] GitHub Actions workflow
- [x] Ruff format check
- [x] Ruff lint check
- [x] Mypy strict check
- [x] Pytest
- [x] Build verification
- [x] Dependency vulnerability scanning
- [x] Secret scanning
- [x] Dependabot dependency updates

---

## Phase 10 — ResearchMind Integration

**Status:** ⏸️ Deferred

- [ ] MCP client integration
- [ ] Tool discovery
- [ ] Tool policy
- [ ] Research-runtime invocation
- [ ] Citation provenance
- [ ] Observability integration
- [ ] Evaluation scenarios

# Future Provider Expansion

## Phase 11 — OpenAlex and Crossref

**Status:** ⏸️ Deferred

- [ ] OpenAlex
- [ ] Crossref
- [ ] DOI metadata enrichment
- [ ] Broader citation and authorship metadata

## Phase 12 — Domain-Specific Sources

**Status:** ⏸️ Deferred

- [ ] PubMed
- [ ] Europe PMC
- [ ] IEEE
- [ ] ACM
- [ ] Springer Nature

---

# Current Progress

```text
Phase 0  ████████████████████ 100%
Phase 1  ████████████████████ 100%
Phase 2  ████████████████████ 100%
Phase 3  ████████████████████ 100%
Phase 4  ████████████████████ 100%
Phase 5  ████████████████████ 100%
Phase 6  ████████████████░░░░  75%
Phase 7  ██████░░░░░░░░░░░░░░  30%
Phase 7A ████████████████████ 100%
Phase 8  ░░░░░░░░░░░░░░░░░░░░   0%
Phase 9  ░░░░░░░░░░░░░░░░░░░░   0%
```
---

# Latest Validation

- `search_papers` is registered and discoverable through MCP Inspector.
- Structured input validation is working.
- Structured provider-neutral output is working.
- arXiv search returns canonical paper records successfully.
- Semantic Scholar rate-limit failures are normalized as retryable partial failures.
- A successful provider result is preserved when another provider fails.

- `get_paper` is implemented and validated through MCP Inspector.
- `resolve_paper_access` is implemented and validated.

- `get_paper_citations` is implemented.
- `get_paper_references` is implemented.
- `get_related_papers` is implemented.

- Bounded in-memory caching is implemented and validated.
- Search and paper caches use independent TTL and capacity settings.
- Cache access is async-safe.
- Deterministic cache keys are implemented.
- Cache statistics track hits, misses, writes, evictions, and expirations.
- Provider failures and exceptions are not cached.
- Cache dependencies are wired through the application dependency container.
- Cache cleanup is included in application shutdown handling.
- Ruff and Mypy validation pass for the caching implementation.

- The `streamable-http` transport and Stage 2 service-to-service JWT
  authentication (`AUTH_*` settings) are implemented; `stdio` remains the
  default local transport and is unaffected. See
  `docs/research_intelligence_mcp_authentication.md`.

Current limitations:

- Citation/reference/recommendation tools are only supported by Semantic Scholar.
- arXiv correctly returns normalized unsupported-operation errors.
- Semantic Scholar graph endpoints require additional response-model validation and payload normalization.
- Provider-aware field-of-study translation remains deferred.

The next implementation milestone is:

1. Reliability and Infrastructure
   - request correlation IDs
   - structured metrics
   - logging review
   - full application graceful shutdown verification

2. Continuous Integration
   - GitHub Actions
   - dependency scanning
   - secret scanning
   - automated quality gates

# Immediate Next Milestone

Phase 7 — Reliability and Infrastructure

Priority order:

1. Request correlation IDs
2. Structured provider metrics
3. Logging review
4. Full application graceful shutdown verification
5. CI and security scanning

Deferred items:

- Provider-aware field translation
- Citation/reference payload normalization improvements
- Additional provider integrations