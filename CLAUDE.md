Use the following implementation rules.

1. Inspect the existing repository before changing files.
2. Reuse existing settings, dependency injection, logging, provider, cache, and lifecycle abstractions.
3. Do not introduce duplicate infrastructure.
4. Preserve the research_intelligence_mcp package namespace.
5. Keep all current MCP tools backward compatible.
6. Keep stdio as the default local transport unless current configuration indicates otherwise.
7. Use official FastMCP APIs supported by the installed version.
8. Verify current library APIs before writing implementation code.
9. Prefer mature libraries over custom security implementations.
10. Use Pydantic v2 for settings and request models.
11. Use async-safe implementations.
12. Do not use unbounded caches.
13. Do not log secrets or full authorization headers.
14. Do not use high-cardinality metric labels.
15. Add complete tests for every new behavior.
16. Update .env.example.
17. Update relevant documentation.
18. Run the full quality gate after each milestone.
19. Return a final implementation report listing:
files created
files modified
architecture decisions
commands run
test results
known limitations
deployment steps remaining