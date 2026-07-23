# Research Intelligence MCP

A production-structured Model Context Protocol (MCP) server for academic paper discovery, citation exploration, and research intelligence workflows.

Research Intelligence MCP provides a unified interface over multiple scientific knowledge sources while exposing standardized MCP tools that can be consumed by AI systems such as ChatGPT, Claude Desktop, Cursor, ResearchMind, and custom agents.

---

# Motivation

Modern AI systems increasingly require access to external research knowledge.

Academic information is fragmented across multiple providers:

* Semantic Scholar
* arXiv
* OpenAlex
* CrossRef
* PubMed
* IEEE
* Springer
* Nature

Every provider exposes different APIs, schemas, identifiers, and capabilities.

This project solves that problem by providing:

* Unified paper models
* Provider abstraction
* Search federation
* Citation graph exploration
* Open-access paper resolution
* MCP-compatible tooling

---

# Features

## Current Version

### Academic Search

* Search scientific papers
* Search recent arXiv publications
* Retrieve paper metadata
* Discover related papers
* Retrieve citations and references
* Resolve available open-access PDFs

### Architecture

* Official MCP Python SDK
* Async Python architecture
* Provider abstraction layer
* Canonical domain models
* Structured logging
* Retry policies
* Caching support
* Rate limiting support
* Production-quality project structure

---

# Supported Providers

## Phase 1

* Semantic Scholar
* arXiv

## Planned Providers

* CrossRef
* OpenAlex
* Papers With Code
* PubMed
* IEEE
* Springer Nature

---

# Example Use Cases

## Find recent papers

```text
Find recent papers about Agentic RAG.
```

## Discover related work

```text
Find papers related to LangGraph multi-agent systems.
```

## Citation exploration

```text
What papers cite the original RAG paper?
```

## Open-access resolution

```text
Find the PDF for this research paper.
```

## Research agent integration

```text
ResearchMind
        ↓
Research Intelligence MCP
        ↓
Semantic Scholar
arXiv
```

---

# Architecture

```text
┌──────────────────────┐
│      MCP Tools       │
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│      Services        │
└──────────┬───────────┘
           │
┌──────────▼───────────┐
│ Provider Abstraction │
└──────────┬───────────┘
           │
 ┌─────────┴─────────┐
 │                   │
▼                     ▼
Semantic Scholar     arXiv
```

---

# Project Structure

```text
research-intelligence-mcp/
├── src/
│   └── research_intelligence_mcp/
├── tests/
├── scripts/
│   └── generate_dev_token.py
├── deployment/
│   ├── ecs/
│   │   ├── task-definition.json
│   │   ├── service-connect-example.json
│   │   └── README.md
│   └── scripts/
│       ├── smoke_test.py
│       └── wait_for_ready.py
├── Dockerfile
├── .dockerignore
├── pyproject.toml
├── README.md
└── .env.example
```

---

# Requirements

* Python 3.12+
* uv
* Git

---

# Installation

Clone repository:

```bash
git clone <repository-url>
cd research-intelligence-mcp
```

Create virtual environment:

```bash
uv venv
source .venv/bin/activate
```

Install dependencies:

```bash
uv sync
```

Create environment file:

```bash
cp .env.example .env
```

---

# Running

Run the MCP server:

```bash
uv run research-intelligence-mcp
```

or 
```bash
python -m research_intelligence_mcp
```

---

# Quality Checks

Format:

```bash
uv run ruff format .
```

Lint:

```bash
uv run ruff check .
uv run ruff check . --fix
```

Type checking:

```bash
uv run mypy src
```

Tests:

```bash
uv run pytest
```

Package build verification: 
```bash
uv build
```

---

# MCP Configuration Example

```json
{
  "mcpServers": {
    "research-intelligence-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/research-intelligence-mcp",
        "run",
        "research-intelligence-mcp"
      ]
    }
  }
}
```

For full step-by-step instructions covering Claude Desktop, Cursor, MCP
Inspector, and remote `streamable-http` clients (including bearer-JWT
authentication), see
[`docs/research_intelligence_mcp_client_setup.md`](docs/research_intelligence_mcp_client_setup.md).

---

# Test using MCP Inspector

The official MCP Inspector is the recommended interactive tool for viewing registered MCP tools, their schemas, parameters, and execution results. project root, run:

```bash
npx @modelcontextprotocol/inspector \
  uv \
  --directory "$(pwd)" \
  run \
  research-intelligence-mcp
```

The Inspector should open in your browser.

Then:
Connect to MCP Server 
Open the Tools tab.
List tools
Select health_check.
Run the tool.

Expected structured result:
```json
{
  "status": "healthy",
  "service": "Research Intelligence MCP",
  "server_name": "research-intelligence-mcp",
  "version": "0.1.0",
  "environment": "development",
  "transport": "stdio",
  "timestamp": "2026-07-20T..."
}
```

![mcp inspector](image.png)


# Startup flow

```
main()
  │
  ├── load settings
  ├── configure stderr logging
  ├── build dependency container
  ├── create FastMCP server
  ├── register tools
  └── run stdio transport
```

# MCP Tools

## Search Tool
![search mcp tool](image-1.png)
![search-mcp-output](image-2.png)
---

# Remote Deployment and Authentication

For the full deployment guide (Docker, AWS ECS, secrets, smoke tests, and
the remaining manual AWS steps), see
[`docs/research_intelligence_mcp_deployment_guide.md`](docs/research_intelligence_mcp_deployment_guide.md).
The summary below covers the basics.

`stdio` remains the default local transport and requires no authentication.

For remote deployments (for example, integrating with ResearchMind), the
server also supports a `streamable-http` transport with service-to-service
bearer-JWT authentication:

```bash
MCP_TRANSPORT=streamable-http
AUTH_ENABLED=true
AUTH_ISSUER=https://auth.researchmind.ai
AUTH_AUDIENCE=research-intelligence-mcp
AUTH_JWKS_URL=https://auth.researchmind.ai/.well-known/jwks.json
```

See `docs/research_intelligence_mcp_authentication.md` for the full
architecture, `docs/research_intelligence_mcp_authentication_testing.md`
for a verified step-by-step guide to testing it locally, and
`.env.example` for every `AUTH_*` and `MCP_*` setting.

On `streamable-http`, the server also exposes unauthenticated HTTP routes
alongside `/mcp`:

| Route | Purpose |
|---|---|
| `GET /health` | Liveness only. Never calls Semantic Scholar or arXiv. |
| `GET /ready` | Readiness. Returns `503` once graceful shutdown has begun. |
| `GET /metrics` | Prometheus text format (tool, provider, cache, and HTTP metrics). Keep this endpoint network-private. |

## Container

Build and run the production container:

```bash
docker build -t research-intelligence-mcp:local .

docker run --rm -p 8000:8000 --env-file .env research-intelligence-mcp:local
```

The image defaults to `MCP_TRANSPORT=streamable-http`, binds `0.0.0.0:8000`,
runs as a non-root user, and ships a container-level `HEALTHCHECK` against
`/health`. See `Dockerfile` and `.dockerignore`.

## AWS ECS

Reference (unapplied) task-definition and Service Connect templates,
security-group guidance, and a deployment/rollback runbook live in
`deployment/ecs/README.md`.

## Deployment Smoke Tests

```bash
uv run python deployment/scripts/wait_for_ready.py --base-url http://127.0.0.1:8000
uv run python deployment/scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

`smoke_test.py` checks `/health`, `/ready`, `/metrics`, MCP session
initialization, tool discovery, and an authenticated `health_check` +
`search_papers` call. Pass `--auth-token` when `AUTH_ENABLED=true`.

---

# License

MIT
