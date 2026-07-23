# Testing the Authentication Flow

This is a practical, verified walkthrough for configuring and testing Stage
2 (service-to-service JWT) authentication locally. It complements
`docs/research_intelligence_mcp_authentication.md` (architecture) — this doc
is "how do I actually run and test it."

Every step below was executed against this codebase (`streamable-http`
transport, HS256 shared-secret mode) before being written down: server
startup, an unauthenticated request, an expired token, a wrong-scope token,
and a full authenticated MCP tool call, including correlation-ID and
caller-context propagation into logs.

---

## 1. Do you need to configure anything for local (Claude Desktop / Cursor / Inspector) use?

**No.** `stdio` is the default transport (`MCP_TRANSPORT=stdio`), and
`AUTH_ENABLED` defaults to `false`. Nothing in this doc is required for the
normal local workflow described in the main README. Authentication only
applies to the `streamable-http` transport.

---

## 2. Configuration for testing streamable-http + auth locally

The fastest path is **HS256 with a shared secret** — it needs no JWKS
server. Set these in `.env` (or export them in your shell):

```bash
MCP_TRANSPORT=streamable-http
MCP_HOST=127.0.0.1
MCP_PORT=8000

AUTH_ENABLED=true
AUTH_ISSUER=https://auth.researchmind.ai
AUTH_AUDIENCE=research-intelligence-mcp
AUTH_JWT_ALGORITHMS=HS256
AUTH_JWT_SECRET=dev-only-shared-secret-please-rotate
AUTH_REQUIRED_SCOPES=research-intelligence/invoke
```

**Important — `AUTH_ISSUER` must match token `iss` claims exactly, byte for
byte.** It is stored as a plain string, not normalized. If you instead use
`AUTH_JWKS_URL` for RS256/ES256/PS256 (production-shaped setup), the same
exact-match rule applies to whatever `iss` your real IdP issues — configure
`AUTH_ISSUER` to that literal value.

Production-shaped (RS256 + JWKS) configuration is documented in
`docs/research_intelligence_mcp_authentication.md` under "Stage 2
Configuration Reference." Testing that locally requires standing up (or
mocking) a JWKS endpoint, which is out of scope for this quick-start doc.

---

## 3. Start the server

```bash
uv run python -m research_intelligence_mcp
```

You should see, on stderr:

```text
mcp_server_starting ... auth_enabled=True transport=streamable-http ...
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

The process is now an HTTP server (not waiting on stdin), listening at
`http://127.0.0.1:8000/mcp`.

---

## 4. Confirm unauthenticated requests are rejected

```bash
curl -i -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

Expected: `401 Unauthorized` with a `WWW-Authenticate: Bearer
error="invalid_token", ...` header. This confirms the MCP SDK's own auth
middleware (`RequireAuthMiddleware`) is active — no custom code in this
project produces this response.

---

## 5. Mint a test token

Use the included dev helper (HS256 only — signs with a secret you supply,
never a real production key):

```bash
uv run python scripts/generate_dev_token.py \
  --issuer https://auth.researchmind.ai \
  --audience research-intelligence-mcp \
  --secret dev-only-shared-secret-please-rotate \
  --scope research-intelligence/invoke
```

This prints a signed JWT to stdout. `--issuer`, `--audience`, and `--secret`
must match `AUTH_ISSUER`, `AUTH_AUDIENCE`, and `AUTH_JWT_SECRET` exactly;
`--scope` must satisfy `AUTH_REQUIRED_SCOPES`.

---

## 6. Test the failure paths

```bash
TOKEN=$(uv run python scripts/generate_dev_token.py \
  --issuer https://auth.researchmind.ai \
  --audience research-intelligence-mcp \
  --secret dev-only-shared-secret-please-rotate \
  --ttl-seconds -1)   # already expired

curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
# -> 401
```

```bash
TOKEN=$(uv run python scripts/generate_dev_token.py \
  --issuer https://auth.researchmind.ai \
  --audience research-intelligence-mcp \
  --secret dev-only-shared-secret-please-rotate \
  --scope research-intelligence/search)   # not the required scope

curl -s -i -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
# -> 403, {"error": "insufficient_scope", "error_description": "Required scope: research-intelligence/invoke"}
```

`curl` alone cannot complete a full MCP session (session negotiation and
SSE framing require a real MCP client), but it is sufficient to prove the
auth layer itself is enforced correctly.

---

## 7. Full authenticated round trip (real MCP client)

`curl` can't do the full JSON-RPC/SSE handshake, but the `mcp` package
(already a dependency) ships a streamable-http client:

```python
# roundtrip.py
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

TOKEN = "paste-token-from-step-5-here"

async def main() -> None:
    async with streamablehttp_client(
        "http://127.0.0.1:8000/mcp",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "X-Request-ID": "req-demo-1",
            "X-Correlation-ID": "corr-demo-1",
            "X-Request-Context": '{"tenant_id": "tenant_demo"}',
        },
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])
            result = await session.call_tool("health_check", {})
            print("health_check result:", result.structuredContent)

asyncio.run(main())
```

```bash
uv run python roundtrip.py
```

Verified output:

```text
Tools: ['health_check', 'search_papers', 'get_paper', 'get_paper_citations', 'get_paper_references', 'get_related_papers', 'resolve_paper_access']
health_check result: {'status': 'healthy', 'service': 'Research Intelligence MCP', ...}
```

And on the server's stderr, the tool-call log line carries every
correlation/caller field from the request headers:

```text
health_check_completed caller_tenant_id=tenant_demo correlation_id=corr-demo-1 request_id=req-demo-1 ...
```

This confirms, end to end: token verification, scope enforcement, tool
execution, and correlation/caller-context propagation into structured logs
(see "Correlation IDs and user-context propagation" in the architecture
doc) all work together.

---

## 8. Testing against Claude Desktop / Cursor / MCP Inspector over streamable-http

These clients generally support configuring a remote streamable-http MCP
server with a custom `Authorization` header (check each client's current
docs for the exact config field name — this changes between client
versions, so it isn't reproduced here to avoid going stale). Point the
client at `http://<MCP_HOST>:<MCP_PORT>/mcp` with `Authorization: Bearer
<token>`, using a token minted as in step 5.

---

## 9. Automated tests (no server required)

The scenarios above are also covered as fast, non-network unit tests:

```bash
uv run pytest tests/unit/infrastructure/auth/test_jwt_verifier.py -v
uv run pytest tests/unit/test_settings.py -v -k auth
uv run pytest tests/unit/mcp/test_server.py -v -k auth
uv run pytest tests/unit/mcp/test_observability.py -v
```

These don't start a real HTTP server; they exercise `JWTBearerTokenVerifier`,
settings validation, server wiring, and correlation/context resolution
directly.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Settings fail to load at startup (`SettingsError` / `ValidationError`) | Check `AUTH_JWT_ALGORITHMS`/`AUTH_REQUIRED_SCOPES` are comma-separated plain strings (not JSON arrays), and that HS256 has `AUTH_JWT_SECRET` set or an asymmetric algorithm has `AUTH_JWKS_URL` set. |
| `401` even with a token you're sure is correct | Almost always an exact-match mismatch on `iss` or `aud`. Confirm `AUTH_ISSUER`/`AUTH_AUDIENCE` are byte-for-byte identical to the token's `iss`/`aud` claims — no automatic trailing-slash normalization is applied. |
| `403 insufficient_scope` | The token's `scope` claim doesn't contain every scope listed in `AUTH_REQUIRED_SCOPES`. |
| `stdio` client (Claude Desktop, Cursor, Inspector via `uv run ... research_intelligence_mcp`) stops working after adding `AUTH_*` settings | Shouldn't happen — `AUTH_*` settings only affect `streamable-http`. If it does, check `MCP_TRANSPORT` wasn't accidentally changed to `streamable-http` in the same `.env`. |
