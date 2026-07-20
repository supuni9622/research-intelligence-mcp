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

**Status:** 🔲 Not Started

## Deliverables

- [ ] `search_papers`
- [ ] `search_arxiv`
- [ ] `get_paper`
- [ ] `get_related_papers`
- [ ] `get_paper_citations`
- [ ] `get_paper_references`
- [ ] `resolve_paper_access`
- [ ] Stable tool descriptions
- [ ] Validated input models
- [ ] Structured output models
- [ ] MCP Inspector validation
- [ ] Tool-level tests

## Tool Design Requirements

- Tool names must describe capabilities clearly.
- Inputs must be bounded and validated.
- Outputs must be provider-neutral.
- Errors must be safe and actionable.
- Tools must not perform LLM reasoning or report generation.

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

## Remaining

- [ ] Bounded in-memory caching
- [ ] Request correlation IDs
- [ ] Structured provider metrics
- [ ] Sensitive-data-safe logging review
- [ ] Full application graceful shutdown verification
- [ ] CI security scanning

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

# Phase 8 — Documentation and Portfolio Readiness

**Status:** 🔲 Not Started

## Deliverables

- [ ] Architecture diagram
- [ ] Provider flow diagram
- [ ] Tool catalogue
- [ ] MCP Inspector instructions
- [ ] Claude Desktop configuration
- [ ] ChatGPT-compatible integration guidance where supported
- [ ] Cursor configuration
- [ ] Example tool calls and outputs
- [ ] Development guide
- [ ] Testing guide
- [ ] Security considerations
- [ ] Portfolio case study
- [ ] Screenshots or demo recording
- [ ] Changelog
- [ ] License

---

# Phase 9 — Continuous Integration

**Status:** 🔲 Not Started

## Deliverables

- [ ] GitHub Actions workflow
- [ ] Ruff format check
- [ ] Ruff lint check
- [ ] Mypy strict check
- [ ] Pytest
- [ ] Build verification
- [ ] Dependency vulnerability scanning
- [ ] Secret scanning
- [ ] Dependabot or equivalent dependency updates

---

# Future Provider Expansion

## Phase 10 — OpenAlex and Crossref

**Status:** ⏸️ Deferred

- [ ] OpenAlex
- [ ] Crossref
- [ ] DOI metadata enrichment
- [ ] Broader citation and authorship metadata

## Phase 11 — Domain-Specific Sources

**Status:** ⏸️ Deferred

- [ ] PubMed
- [ ] Europe PMC
- [ ] IEEE
- [ ] ACM
- [ ] Springer Nature

## Phase 12 — ResearchMind Integration

**Status:** ⏸️ Deferred

- [ ] MCP client integration
- [ ] Tool discovery
- [ ] Tool policy
- [ ] Research-runtime invocation
- [ ] Citation provenance
- [ ] Observability integration
- [ ] Evaluation scenarios

---

# Current Progress

```text
Phase 0  ████████████████████ 100%
Phase 1  ████████████████████ 100%
Phase 2  ████████████████████ 100%
Phase 3  ████████████████████ 100%
Phase 4  ████████████████████ 100%
Phase 5  ████████████████████ 100%
Phase 6  ░░░░░░░░░░░░░░░░░░░░   0%