"""Service-to-service JWT bearer-token verification.

Implements the Stage 2 authentication flow described in
``docs/research_intelligence_mcp_authentication.md``: a trusted backend
(for example ResearchMind) presents a bearer JWT issued by its auth server,
and this server verifies the token's signature, issuer, audience, and
expiry before trusting the request. Scope enforcement against
``AuthSettings.required_scopes`` is handled by the MCP SDK's
``RequireAuthMiddleware``; this verifier is only responsible for producing
a trustworthy ``AccessToken`` from a raw token string.
"""

from __future__ import annotations

from typing import Any

import jwt
from anyio import to_thread
from mcp.server.auth.provider import AccessToken

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.logging import get_logger

logger = get_logger(__name__)


class JWTBearerTokenVerifier:
    """Verifies bearer JWTs against a configured issuer, audience, and key.

    Supports RS256/ES256/PS256 verification against a remote JWKS endpoint
    (production) and HS256 verification against a configured shared secret
    (local development and tests). The signing-key source is resolved from
    validated application settings; see
    ``Settings.validate_auth_configuration``.
    """

    def __init__(self, settings: Settings) -> None:
        self._issuer = settings.auth_issuer
        self._audience = settings.auth_audience
        self._algorithms = settings.auth_jwt_algorithms_list()
        self._leeway_seconds = settings.auth_jwt_leeway_seconds
        self._secret = settings.auth_jwt_secret_value()

        self._jwks_client: jwt.PyJWKClient | None = None
        if settings.auth_jwks_url is not None:
            self._jwks_client = jwt.PyJWKClient(
                str(settings.auth_jwks_url),
                cache_keys=True,
                max_cached_keys=16,
                lifespan=settings.auth_jwks_cache_ttl_seconds,
            )

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify a bearer token and return access info if valid.

        Returns ``None`` for any invalid, expired, or malformed token rather
        than raising, matching the MCP SDK's ``TokenVerifier`` protocol. No
        token material or verification-key content is logged.
        """

        try:
            signing_key = await self._resolve_signing_key(token)
        except jwt.PyJWTError:
            logger.warning("auth_token_signing_key_unresolved")
            return None

        try:
            claims = jwt.decode(
                token,
                key=signing_key,
                algorithms=self._algorithms,
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._leeway_seconds,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.PyJWTError as exc:
            logger.warning(
                "auth_token_rejected",
                error_type=type(exc).__name__,
            )
            return None

        return self._to_access_token(token=token, claims=claims)

    async def _resolve_signing_key(self, token: str) -> str | jwt.PyJWK:
        if self._jwks_client is not None:
            return await to_thread.run_sync(
                self._jwks_client.get_signing_key_from_jwt,
                token,
            )

        if self._secret is not None:
            return self._secret

        raise jwt.PyJWTError("No JWT signing-key source is configured.")

    def _to_access_token(
        self,
        *,
        token: str,
        claims: dict[str, Any],
    ) -> AccessToken:
        subject = claims.get("sub")
        client_id = str(claims.get("client_id") or claims.get("azp") or subject)

        scope_claim = claims.get("scope") or claims.get("scp") or []
        scopes = (
            scope_claim.split() if isinstance(scope_claim, str) else list(scope_claim)
        )

        expires_at_claim = claims.get("exp")
        expires_at = int(expires_at_claim) if expires_at_claim is not None else None

        access_token = AccessToken(
            token=token,
            client_id=client_id,
            scopes=scopes,
            expires_at=expires_at,
            subject=str(subject) if subject is not None else None,
            claims={"iss": claims.get("iss")},
        )

        logger.info(
            "auth_token_verified",
            client_id=client_id,
            scope_count=len(scopes),
        )

        return access_token
