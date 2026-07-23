# Research Intelligence MCP

## Product Requirements Document

Version: 1.0

> **Implementation status legend:** ✅ done · 🟡 partial · 🔲 not built.
> Annotations below reflect the codebase as of this writing. See
> "Implementation Status Summary" at the end for the consolidated list of
> what remains, and `docs/research_intelligence_mcp_roadmap.md` for the
> full phase-by-phase build record.

---

# 1. Vision

Build a reusable MCP server that provides unified access to scientific research knowledge.

The server should expose standardized tools that can be consumed by AI systems and agent platforms.

---

# 2. Goals

## Primary Goals

* ✅ Search research papers
* ✅ Explore citation graphs
* ✅ Retrieve paper metadata
* ✅ Resolve open-access papers
* ✅ Expose capabilities through MCP

All five primary goals are implemented and covered by tests.

---

# 3. Non Goals

Version 1 will NOT:

* Perform deep research reasoning
* Generate reports
* Execute autonomous workflows
* Store embeddings
* Build a vector database
* Replace ResearchMind

Research reasoning belongs to external orchestrators.

---

# 4. Target Users

### AI Engineers

Need research tools for agents.

### Researchers

Need unified access to academic information.

### Agent Platforms

Need MCP tools.

### ResearchMind

Will consume this MCP.

---

# 5. Functional Requirements

## Search Papers — ✅ Done (`search_papers` tool)

User can search papers by:

* ✅ title
* ✅ abstract
* ✅ keywords

All three are satisfied through a single free-text `query` input (not
separate per-field parameters); `search_papers` also adds filters beyond
this PRD's original scope — `year_from`/`year_to`, `fields_of_study`,
`open_access_only`, and `sort`.

Output:

* ✅ title
* ✅ authors
* ✅ abstract
* ✅ identifiers
* ✅ citation counts
* ✅ urls
* ✅ pdf urls

---

## Paper Details — ✅ Done (`get_paper` tool)

Retrieve full metadata.

---

## Citations — ✅ Done (`get_paper_citations` tool)

Retrieve papers citing a paper. Semantic Scholar only — arXiv has no
citation-graph API and correctly returns a normalized unsupported-operation
error rather than failing silently.

---

## References — ✅ Done (`get_paper_references` tool)

Retrieve papers referenced by a paper. Same Semantic-Scholar-only caveat as
Citations.

---

## Related Papers — ✅ Done (`get_related_papers` tool)

Retrieve semantically related papers. Semantic Scholar only (arXiv has no
recommendations API).

---

## Open Access Resolution — ✅ Done (`resolve_paper_access` tool)

Find available PDFs.

---

# 6. Supported Providers — ✅ Done

## Phase 1

### Semantic Scholar

Capabilities:

* ✅ search
* ✅ metadata
* ✅ citations
* ✅ references
* ✅ related papers

### arXiv

Capabilities:

* ✅ recent papers
* ✅ metadata
* ✅ pdf resolution

---

# 7. MCP Tools

### ✅ search_papers

### ✅ get_paper

### ✅ get_paper_citations

### ✅ get_paper_references

### ✅ get_related_papers

### 🔲 search_arxiv

Not built as a separate tool. arXiv-only search is instead reached through
`search_papers(providers=["arxiv"])`. Revisit whether this PRD's original
per-provider tool is still wanted, or whether the provider-filtered
`search_papers` design should be adopted as the permanent decision.

### ✅ resolve_paper_access

### ✅ health_check *(not in original PRD scope, added for operability)*

---

# 8. Architecture Principles

## Provider Isolation — ✅ Done

External schemas must never leak outside providers.

---

## Canonical Models — ✅ Done

All providers map into common models.

---

## Async First — ✅ Done

All integrations must be async.

---

## Extensible — ✅ Done

New providers should require minimal code changes. Provider abstraction
(`providers/base.py`), a provider registry, and the caching/executor layers
are all provider-agnostic; adding a provider means implementing the
`PaperProvider` protocol plus a mapper, not touching services or MCP tools.

---

# 9. Non Functional Requirements

## Reliability — ✅ Done

Retries and graceful failures. Tenacity-based retry with backoff on both
providers; provider failures are normalized and isolated (one provider
failing doesn't discard another's results).

## Performance — ✅ Done

Parallel provider execution via `asyncio.gather` in `ProviderExecutor`.

## Observability — ✅ Done, exceeds original scope

Structured logs (`structlog`), plus request correlation IDs and Prometheus
metrics (tool/provider/cache/HTTP) added during the remote-deployment work
— see `docs/research_intelligence_mcp_roadmap.md` Phase 7B.

## Testability — ✅ Done

High provider test coverage (278 tests across domain, providers, services,
infrastructure, and MCP layers as of this writing).

---

# 10. Future Scope

* 🔲 OpenAlex
* 🔲 CrossRef
* 🔲 PubMed
* 🔲 IEEE
* 🔲 Springer
* 🔲 Papers With Code
* 🔲 Research datasets
* 🔲 Offline snapshots
* 🟡 Ranking improvements — a deterministic baseline ranker
  (`services/search/ranker.py`) exists; no ranking work beyond that
  baseline has been done

None of this section has been started; all of it remains future scope, as
originally intended.

---

# 11. Implementation Status Summary

## Fully done

Every Primary Goal, every Functional Requirement, both Phase 1 providers,
6 of 7 originally-specified MCP tools, all four Architecture Principles,
and all four Non-Functional Requirements.

## Main functionalities still to build

1. **Additional providers** (all of Future Scope: OpenAlex, CrossRef,
   PubMed, IEEE, Springer, Papers With Code) — nothing started.
2. **`search_arxiv` as a standalone tool** — currently folded into
   `search_papers(providers=["arxiv"])`; needs an explicit product
   decision on whether the original per-provider tool is still wanted.
3. **Provider-aware field-of-study translation and unsupported-filter
   warnings** — canonical field filters aren't yet translated into each
   provider's native query format, and unsupported filters aren't
   surfaced as warnings (tracked in the roadmap's Phase 6).
4. **Ranking improvements beyond the deterministic baseline** — no
   relevance/quality-scoring work has been done past initial sorting.
5. **Research datasets and offline snapshots** — not started.
6. **Sensitive-data-safe logging review** — the one remaining item in the
   roadmap's Phase 7 (Reliability and Infrastructure).

## Beyond this PRD's original scope (already done)

Streamable-HTTP remote transport, service-to-service JWT authentication,
request correlation IDs, Prometheus metrics, a production Docker image,
and AWS ECS deployment templates — see
`docs/research_intelligence_mcp_deployment_guide.md` and
`docs/research_intelligence_mcp_roadmap.md` (Phases 7A/7B). Live AWS
deployment itself has not been performed.
