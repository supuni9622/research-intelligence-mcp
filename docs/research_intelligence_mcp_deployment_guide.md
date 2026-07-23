# Deployment Guide

A practical, current-state guide to deploying Research Intelligence MCP.
Where `docs/remote_mcp_deployment_prd.md` describes what was *specified* and
`docs/research_intelligence_mcp_roadmap.md` (Phase 7B) records what was
*implemented and verified*, this document is "how do I actually stand this
up," end to end, including the steps that still require a human with AWS
access.

---

## 1. Deployment stages

| Stage | Transport | Auth | Status |
|---|---|---|---|
| Local development | `stdio` | none | ✅ Default, always available |
| Local / CI HTTP testing | `streamable-http` | optional (`AUTH_ENABLED`) | ✅ Implemented, verified |
| Containerized (Docker) | `streamable-http` | optional | ✅ Implemented, verified locally |
| Private AWS ECS (ResearchMind integration) | `streamable-http` | required (JWT) | 🔲 Templates only — **not deployed** |
| Public MCP platform (OAuth, external customers) | `streamable-http` | OAuth | ⏸️ Deferred, out of scope |

Nothing below changes the default local experience: `stdio` with no
authentication remains the default for Claude Desktop, Cursor, and MCP
Inspector. See `docs/research_intelligence_mcp_client_setup.md` for
client-side connection instructions.

---

## 2. Run locally over HTTP (no container)

```bash
uv sync

MCP_TRANSPORT=streamable-http \
MCP_HOST=127.0.0.1 \
MCP_PORT=8000 \
uv run python -m research_intelligence_mcp
```

Verify:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/ready
curl -s http://127.0.0.1:8000/metrics | head -20
```

To exercise authentication too, follow
`docs/research_intelligence_mcp_authentication_testing.md` first — it is a
verified, step-by-step walkthrough of `AUTH_ENABLED=true` locally (HS256
shared secret, no JWKS server required).

---

## 3. Run the Docker container

```bash
docker build -t research-intelligence-mcp:local .

docker run --rm -p 8000:8000 --env-file .env research-intelligence-mcp:local
```

The image (`Dockerfile`) already sets production-shaped defaults —
`MCP_TRANSPORT=streamable-http`, `MCP_HOST=0.0.0.0`, `MCP_PORT=8000` — so no
extra flags are required for a basic run. It builds in two stages (uv-synced
dependency layer, then a non-root runtime layer), runs as a non-root user,
uses exec-form `CMD` so `SIGTERM` reaches the Python process directly, and
ships a container-level `HEALTHCHECK` against `/health`.

**Verified during implementation** (see Phase 7B in the roadmap for the
exact commands): image builds from a clean checkout; `/health`, `/ready`,
and `/metrics` all respond correctly; `docker inspect --format
'{{json .State.Health}}'` reports `"healthy"`; `docker stop` exits in well
under a second with a clean `mcp_server_shutdown_complete` log line and no
unclosed-client warnings.

To run the Level 1 smoke test against the container (see §6):

```bash
uv run python deployment/scripts/wait_for_ready.py --base-url http://127.0.0.1:8000
uv run python deployment/scripts/smoke_test.py --base-url http://127.0.0.1:8000
```

### Pushing to ECR

```bash
aws ecr get-login-password --region <REGION> \
  | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com

docker build -t <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/research-intelligence-mcp:<IMAGE_TAG> .
docker push <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/research-intelligence-mcp:<IMAGE_TAG>
```

---

## 4. Deploy to AWS ECS (private, service-to-service)

Full reference templates, security-group rules, and a rollback runbook live
in [`deployment/ecs/README.md`](../deployment/ecs/README.md) —
[`task-definition.json`](../deployment/ecs/task-definition.json) and
[`service-connect-example.json`](../deployment/ecs/service-connect-example.json)
are unapplied examples with `<PLACEHOLDER>` values to fill in.

At a glance, the sequence is:

```text
Build & push image → ECR
        ↓
Register task definition (fill in placeholders first)
        ↓
Create/update ECS service with Service Connect enabled
        ↓
aws ecs wait services-stable
        ↓
Run deployment/scripts/smoke_test.py from inside the same VPC
```

The task definition defaults to `AUTH_ENABLED=true` with an RS256/JWKS
issuer (production shape) — no `AUTH_JWT_SECRET` is used in ECS; that
setting is for local HS256 testing only.

---

## 5. Secrets

Store in AWS Secrets Manager, referenced from the task definition's
`secrets` block (never baked into the image or committed to git):

- `SEMANTIC_SCHOLAR_API_KEY` (optional — Semantic Scholar works anonymously)
- Any future OAuth/JWT signing material

`AUTH_ISSUER`, `AUTH_AUDIENCE`, `AUTH_JWKS_URL`, and `AUTH_REQUIRED_SCOPES`
are plain (non-secret) configuration and can stay as task-definition
environment variables.

---

## 6. Smoke tests

| Level | Script | Status |
|---|---|---|
| 1 — Local container | `deployment/scripts/smoke_test.py` | ✅ Implemented, run and passing against a local container (health/ready/metrics, MCP session init, tool discovery, `health_check` + `search_papers` calls against live providers) |
| 2 — ECS (from another private-VPC task) | Same script, pointed at the Service Connect DNS name | 🔲 Not run — requires a deployed ECS service |
| 3 — ResearchMind end-to-end | Owned by the companion ResearchMind repository | 🔲 Not run — requires both services deployed |

```bash
# Level 1 (local or already-running container)
uv run python deployment/scripts/wait_for_ready.py --base-url http://127.0.0.1:8000
uv run python deployment/scripts/smoke_test.py --base-url http://127.0.0.1:8000 [--auth-token "$TOKEN"]

# Level 2 (from a task inside the same Service Connect namespace)
uv run python deployment/scripts/smoke_test.py \
  --base-url http://research-intelligence-mcp:8000 \
  --auth-token "$MCP_SERVICE_TOKEN"
```

`smoke_test.py` never prints the bearer token, uses a small fixed query
(`"retrieval augmented generation"`, limit 2), and exits non-zero with the
failing step named — safe to gate a CI/CD pipeline on.

---

## 7. Observability once deployed

- **Logs**: structured JSON to stdout/CloudWatch when `LOG_FORMAT=json` (set this in production — the task definition template does). Correlation IDs (`X-Request-ID`/`X-Correlation-ID`) are bound to every tool-call log line.
- **Metrics**: `GET /metrics` (Prometheus text format) — `mcp_tool_*`, `provider_*`, `cache_*`, `mcp_http_*`. Keep this endpoint network-private; it is unauthenticated by design (see the security-group rules in `deployment/ecs/README.md`).
- **Health**: ECS container health check hits `/health` (liveness only — never calls Semantic Scholar or arXiv). `/ready` is available for any additional readiness probing and returns `503` once graceful shutdown begins.

---

## 8. Remaining manual tasks

Everything below requires an AWS account and was intentionally **not**
performed as part of implementing this guide — these are the concrete next
steps for whoever owns the AWS environment:

- [ ] Create the ECR repository and push a built image.
- [ ] Create/confirm the ECS cluster, private subnets with NAT egress, and Service Connect namespace.
- [ ] Create the two IAM roles referenced in `task-definition.json` (execution role, task role).
- [ ] Create the `SEMANTIC_SCHOLAR_API_KEY` secret in Secrets Manager (optional — omit the `secrets` block entirely if not using a key).
- [ ] Confirm or obtain the real `AUTH_ISSUER` / `AUTH_JWKS_URL` / `AUTH_REQUIRED_SCOPES` values from whichever service issues ResearchMind's service tokens.
- [ ] Create the two security groups (ResearchMind → MCP on 8000; MCP → 0.0.0.0/0 on 443) — **never** open inbound 0.0.0.0/0 on port 8000.
- [ ] Fill in every `<PLACEHOLDER>` in `deployment/ecs/task-definition.json` and `service-connect-example.json`.
- [ ] Register the task definition and create/update the ECS service.
- [ ] Run the Level 2 smoke test from a task inside the same VPC.
- [ ] Hand off the MCP base URL, Service Connect discovery name, JWT issuer/audience/scope, and JWKS URL to the ResearchMind team (see "Cross-Repository Handoff" in `docs/remote_mcp_deployment_prd.md`).
- [ ] Once ResearchMind is also deployed, run the Level 3 end-to-end smoke test.
- [ ] Optional hardening: add HTTP response-header echo for `X-Request-ID`/`X-Correlation-ID` (currently log-bound only — see Phase 7B "Known limitations" in the roadmap) and `provider_rate_limits_total` / `provider_retries_total` metrics.

---

## 9. Related documents

- [`docs/remote_mcp_deployment_prd.md`](remote_mcp_deployment_prd.md) — original requirements this implementation follows.
- [`docs/research_intelligence_mcp_deployment.md`](research_intelligence_mcp_deployment.md) — architecture and long-term deployment vision.
- [`docs/research_intelligence_mcp_roadmap.md`](research_intelligence_mcp_roadmap.md) (Phase 7B) — the detailed implementation record: what was built, tested, and left as a known limitation.
- [`docs/research_intelligence_mcp_authentication.md`](research_intelligence_mcp_authentication.md) / [`_authentication_testing.md`](research_intelligence_mcp_authentication_testing.md) — JWT auth architecture and a verified local walkthrough.
- [`docs/research_intelligence_mcp_client_setup.md`](research_intelligence_mcp_client_setup.md) — connecting Claude Desktop, Cursor, MCP Inspector, and streamable-http clients.
- [`deployment/ecs/README.md`](../deployment/ecs/README.md) — ECS templates, security groups, deploy/rollback commands.
