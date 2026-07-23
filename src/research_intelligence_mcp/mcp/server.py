"""FastMCP server construction."""

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from research_intelligence_mcp.infrastructure.auth.jwt_verifier import (
    JWTBearerTokenVerifier,
)
from research_intelligence_mcp.infrastructure.lifecycle import (
    LifecycleState,
)
from research_intelligence_mcp.mcp.dependencies import (
    AppDependencies,
)
from research_intelligence_mcp.mcp.tools.health import (
    register_health_routes,
    register_health_tools,
)
from research_intelligence_mcp.mcp.tools.metrics import (
    register_metrics_route,
)
from research_intelligence_mcp.mcp.tools.paper import (
    register_paper_tools,
)
from research_intelligence_mcp.mcp.tools.search import (
    register_search_tools,
)


def create_mcp_server(
    dependencies: AppDependencies,
    *,
    lifecycle: LifecycleState | None = None,
) -> FastMCP:
    """Create and configure the Research Intelligence MCP server.

    Args:
        dependencies:
            Long-lived application dependencies shared by registered tools.
        lifecycle:
            Shared readiness/shutdown state backing the ``/ready`` HTTP
            route. Defaults to a fresh, always-ready state, which is
            sufficient for tests and for callers that never signal
            shutdown explicitly.

    Returns:
        A fully configured FastMCP server with academic paper discovery,
        metadata retrieval, citation graph, reference graph, recommendation,
        and access-resolution capabilities.
    """

    if lifecycle is None:
        lifecycle = LifecycleState()

    settings = dependencies.settings

    token_verifier: JWTBearerTokenVerifier | None = None
    auth_settings: AuthSettings | None = None

    if settings.auth_enabled:
        # Bearer-JWT verification for the streamable-http transport (Stage 2
        # of docs/research_intelligence_mcp_authentication.md). The stdio
        # transport never routes through HTTP auth middleware, so these
        # settings have no effect when MCP_TRANSPORT=stdio.
        assert settings.auth_issuer is not None  # enforced by settings validation

        token_verifier = JWTBearerTokenVerifier(settings)
        auth_settings = AuthSettings(
            # `AuthSettings.issuer_url` is only used for OAuth
            # protected-resource-metadata discovery, not for bearer-token
            # verification, so pydantic's URL normalization here (e.g. an
            # added trailing slash) is harmless — actual `iss` comparison
            # uses the raw `settings.auth_issuer` string in the verifier.
            issuer_url=AnyHttpUrl(settings.auth_issuer),
            resource_server_url=(
                AnyHttpUrl(str(settings.auth_resource_server_url))
                if settings.auth_resource_server_url is not None
                else None
            ),
            required_scopes=settings.auth_required_scopes_list(),
        )

    server = FastMCP(
        name=settings.mcp_server_name,
        host=settings.mcp_host,
        port=settings.mcp_port,
        token_verifier=token_verifier,
        auth=auth_settings,
        instructions=(
            "Research Intelligence MCP provides provider-neutral academic "
            "research tools backed by Semantic Scholar and arXiv. "
            "Use search_papers to discover academic literature by topic, "
            "keywords, title, author, publication year, or academic field. "
            "Use get_paper to retrieve canonical metadata for one paper. "
            "Use get_paper_citations to find papers that cite an origin paper. "
            "Use get_paper_references to retrieve papers referenced by an "
            "origin paper. "
            "Use get_related_papers to discover recommendations related to a "
            "seed paper. "
            "Use resolve_paper_access to determine known access status, "
            "landing-page URLs, PDF URLs, licenses, and repository metadata. "
            "Semantic Scholar supports citation graphs, reference graphs, and "
            "related-paper recommendations. arXiv supports search, individual "
            "paper metadata, and open-access metadata, but does not expose "
            "citation, reference, or recommendation APIs. "
            "Use health_check only to verify server availability. "
            "The server retrieves structured research metadata; it does not "
            "perform autonomous research synthesis or generate reports."
        ),
    )

    register_health_tools(
        server=server,
        dependencies=dependencies,
    )

    register_health_routes(
        server=server,
        dependencies=dependencies,
        lifecycle=lifecycle,
    )

    register_metrics_route(
        server=server,
        dependencies=dependencies,
    )

    register_search_tools(
        server=server,
        dependencies=dependencies,
    )

    register_paper_tools(
        server=server,
        dependencies=dependencies,
    )

    return server
