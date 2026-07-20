# Research Intelligence MCP

## Implementation Roadmap

**Current version:** 0.1.0  
**Current milestone:** Phase 1 — Core MCP Server  
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

**Status:** 🔲 Not Started

## Deliverables

- [ ] Semantic Scholar configuration
- [ ] Async HTTP client
- [ ] Provider response models
- [ ] Response-to-domain mapper
- [ ] Provider implementation
- [ ] API error normalization
- [ ] Retry policy
- [ ] Rate-limit handling
- [ ] Mocked integration tests
- [ ] Optional live-provider smoke tests

## Capabilities

- [ ] Search papers
- [ ] Retrieve paper details
- [ ] Retrieve citations
- [ ] Retrieve references
- [ ] Retrieve related/recommended papers
- [ ] Resolve available open-access metadata

---

# Phase 4 — arXiv Provider

**Status:** 🔲 Not Started

## Deliverables

- [ ] arXiv configuration
- [ ] Async Atom API client
- [ ] Safe XML parsing
- [ ] Atom response parser
- [ ] Response-to-domain mapper
- [ ] Provider implementation
- [ ] API error normalization
- [ ] Retry policy
- [ ] Rate-limit handling
- [ ] Mocked integration tests
- [ ] Optional live-provider smoke tests

## Capabilities

- [ ] Search papers
- [ ] Retrieve arXiv metadata
- [ ] Resolve abstract pages
- [ ] Resolve PDF URLs
- [ ] Normalize arXiv identifiers and versions

---

# Phase 5 — Federated Search Service

**Status:** 🔲 Not Started

## Deliverables

- [ ] Provider registry
- [ ] Provider selection
- [ ] Concurrent provider execution
- [ ] Partial-failure handling
- [ ] Search-result aggregation
- [ ] Identifier-based deduplication
- [ ] Metadata-based deduplication fallback
- [ ] Deterministic ranking
- [ ] Provider attribution
- [ ] Search-service tests

## Exit criteria

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

## Tool design requirements

- Tool names must describe capabilities clearly.
- Inputs must be bounded and validated.
- Outputs must be provider-neutral.
- Errors must be safe and actionable.
- Tools must not perform LLM reasoning or report generation.

---

# Phase 7 — Reliability and Infrastructure

**Status:** 🔲 Not Started

## Deliverables

- [ ] Shared async HTTP-client lifecycle
- [ ] Connection pooling
- [ ] Timeouts
- [ ] Retry policies
- [ ] Backoff with jitter
- [ ] Provider-aware rate limiting
- [ ] Bounded in-memory caching
- [ ] Request correlation IDs
- [ ] Structured provider metrics
- [ ] Sensitive-data-safe logging
- [ ] Graceful shutdown
- [ ] Failure classification

## Security requirements

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

# Current Next Action

Complete the remaining Phase 1 work:

1. Create the application dependency container.
2. Pass dependencies explicitly into the server and tool registrations.
3. Add dependency-container tests.
4. Run the full quality gate.
5. Mark Phase 1 complete.