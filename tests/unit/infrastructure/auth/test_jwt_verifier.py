"""Tests for service-to-service JWT bearer-token verification."""

from __future__ import annotations

import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from research_intelligence_mcp.config.settings import Settings
from research_intelligence_mcp.infrastructure.auth.jwt_verifier import (
    JWTBearerTokenVerifier,
)

ISSUER = "https://auth.researchmind.ai/"
AUDIENCE = "research-intelligence-mcp"
TEST_SECRET = "test-shared-secret-with-at-least-32-bytes-of-entropy"


def _hs256_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "AUTH_ENABLED": True,
        "AUTH_ISSUER": ISSUER,
        "AUTH_AUDIENCE": AUDIENCE,
        "AUTH_JWT_ALGORITHMS": "HS256",
        "AUTH_JWT_SECRET": TEST_SECRET,
        "AUTH_JWT_LEEWAY_SECONDS": 5,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def _encode_hs256(claims: dict[str, object], secret: str = TEST_SECRET) -> str:
    return jwt.encode(claims, secret, algorithm="HS256")


def _base_claims(**overrides: object) -> dict[str, object]:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "researchmind-backend",
        "scope": "research-intelligence/invoke",
        "iat": now,
        "exp": now + 300,
    }
    claims.update(overrides)
    return claims


@pytest.mark.asyncio
async def test_valid_hs256_token_is_verified() -> None:
    """A correctly signed, non-expired token should verify successfully."""

    verifier = JWTBearerTokenVerifier(_hs256_settings())
    token = _encode_hs256(_base_claims())

    access_token = await verifier.verify_token(token)

    assert access_token is not None
    assert access_token.subject == "researchmind-backend"
    assert access_token.client_id == "researchmind-backend"
    assert access_token.scopes == ["research-intelligence/invoke"]
    assert access_token.claims == {"iss": ISSUER}


@pytest.mark.asyncio
async def test_scopes_parsed_from_list_valued_scp_claim() -> None:
    """The `scp` claim may carry scopes as a list instead of a string."""

    verifier = JWTBearerTokenVerifier(_hs256_settings())
    token = _encode_hs256(
        _base_claims(
            scope=None,
            scp=["research-intelligence/invoke", "research-intelligence/search"],
        )
    )

    access_token = await verifier.verify_token(token)

    assert access_token is not None
    assert access_token.scopes == [
        "research-intelligence/invoke",
        "research-intelligence/search",
    ]


@pytest.mark.asyncio
async def test_client_id_prefers_explicit_client_id_claim() -> None:
    """An explicit `client_id` claim should take priority over `sub`."""

    verifier = JWTBearerTokenVerifier(_hs256_settings())
    token = _encode_hs256(_base_claims(client_id="researchmind-service-account"))

    access_token = await verifier.verify_token(token)

    assert access_token is not None
    assert access_token.client_id == "researchmind-service-account"


@pytest.mark.asyncio
async def test_expired_token_is_rejected() -> None:
    """An expired token must not be trusted, even with configured leeway."""

    verifier = JWTBearerTokenVerifier(_hs256_settings())
    now = int(time.time())
    token = _encode_hs256(_base_claims(iat=now - 3600, exp=now - 3600))

    assert await verifier.verify_token(token) is None


@pytest.mark.asyncio
async def test_token_within_leeway_is_accepted() -> None:
    """Small clock skew within the configured leeway should be tolerated."""

    verifier = JWTBearerTokenVerifier(_hs256_settings(AUTH_JWT_LEEWAY_SECONDS=30))
    now = int(time.time())
    token = _encode_hs256(_base_claims(exp=now - 3))

    assert await verifier.verify_token(token) is not None


@pytest.mark.asyncio
async def test_wrong_audience_is_rejected() -> None:
    """A token issued for a different audience must be rejected."""

    verifier = JWTBearerTokenVerifier(_hs256_settings())
    token = _encode_hs256(_base_claims(aud="some-other-service"))

    assert await verifier.verify_token(token) is None


@pytest.mark.asyncio
async def test_bare_domain_issuer_without_trailing_slash_is_matched() -> None:
    """Regression test: issuer comparison must be exact, not URL-normalized.

    `HttpUrl` silently appends a trailing slash to a bare-domain value
    (`https://auth.researchmind.ai` -> `https://auth.researchmind.ai/`).
    `AUTH_ISSUER` must be stored and compared verbatim so a real IdP's
    unmodified `iss` claim (commonly without a trailing slash) still
    verifies, even though the configured value looks identical to what a
    human operator typed.
    """

    bare_issuer = "https://auth.researchmind.ai"
    verifier = JWTBearerTokenVerifier(_hs256_settings(AUTH_ISSUER=bare_issuer))
    token = _encode_hs256(_base_claims(iss=bare_issuer))

    access_token = await verifier.verify_token(token)

    assert access_token is not None


@pytest.mark.asyncio
async def test_wrong_issuer_is_rejected() -> None:
    """A token issued by an untrusted authority must be rejected."""

    verifier = JWTBearerTokenVerifier(_hs256_settings())
    token = _encode_hs256(_base_claims(iss="https://attacker.example/"))

    assert await verifier.verify_token(token) is None


@pytest.mark.asyncio
async def test_wrong_signature_is_rejected() -> None:
    """A token signed with an untrusted secret must be rejected."""

    verifier = JWTBearerTokenVerifier(_hs256_settings())
    token = _encode_hs256(
        _base_claims(),
        secret="not-the-configured-secret-but-still-32-bytes-plus",
    )

    assert await verifier.verify_token(token) is None


@pytest.mark.asyncio
async def test_missing_subject_claim_is_rejected() -> None:
    """Tokens missing required claims must be rejected, not raise."""

    verifier = JWTBearerTokenVerifier(_hs256_settings())
    claims = _base_claims()
    del claims["sub"]
    token = _encode_hs256(claims)

    assert await verifier.verify_token(token) is None


@pytest.mark.asyncio
async def test_malformed_token_is_rejected() -> None:
    """A syntactically invalid token must not raise."""

    verifier = JWTBearerTokenVerifier(_hs256_settings())

    assert await verifier.verify_token("not-a-jwt") is None


def _generate_rsa_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


@pytest.mark.asyncio
async def test_rs256_token_verified_via_jwks_signing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RS256 tokens should be verified using the key resolved from the JWKS client."""

    private_pem, public_pem = _generate_rsa_keypair()

    settings = Settings(
        _env_file=None,
        AUTH_ENABLED=True,
        AUTH_ISSUER=ISSUER,
        AUTH_AUDIENCE=AUDIENCE,
        AUTH_JWT_ALGORITHMS="RS256",
        AUTH_JWKS_URL="https://auth.researchmind.ai/.well-known/jwks.json",
    )
    verifier = JWTBearerTokenVerifier(settings)

    assert verifier._jwks_client is not None
    monkeypatch.setattr(
        verifier._jwks_client,
        "get_signing_key_from_jwt",
        lambda token: public_pem,
    )

    token = jwt.encode(
        _base_claims(),
        private_pem,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    access_token = await verifier.verify_token(token)

    assert access_token is not None
    assert access_token.subject == "researchmind-backend"


@pytest.mark.asyncio
async def test_rs256_token_signed_by_untrusted_key_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A token signed by a key other than the one the JWKS endpoint serves must fail."""

    _untrusted_private_pem, _ = _generate_rsa_keypair()
    _trusted_private_pem, trusted_public_pem = _generate_rsa_keypair()

    settings = Settings(
        _env_file=None,
        AUTH_ENABLED=True,
        AUTH_ISSUER=ISSUER,
        AUTH_AUDIENCE=AUDIENCE,
        AUTH_JWT_ALGORITHMS="RS256",
        AUTH_JWKS_URL="https://auth.researchmind.ai/.well-known/jwks.json",
    )
    verifier = JWTBearerTokenVerifier(settings)

    assert verifier._jwks_client is not None
    monkeypatch.setattr(
        verifier._jwks_client,
        "get_signing_key_from_jwt",
        lambda token: trusted_public_pem,
    )

    forged_token = jwt.encode(
        _base_claims(),
        _untrusted_private_pem,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    assert await verifier.verify_token(forged_token) is None


@pytest.mark.asyncio
async def test_unresolvable_signing_key_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A JWKS lookup failure should be treated as a rejected token, not an error."""

    settings = Settings(
        _env_file=None,
        AUTH_ENABLED=True,
        AUTH_ISSUER=ISSUER,
        AUTH_AUDIENCE=AUDIENCE,
        AUTH_JWT_ALGORITHMS="RS256",
        AUTH_JWKS_URL="https://auth.researchmind.ai/.well-known/jwks.json",
    )
    verifier = JWTBearerTokenVerifier(settings)

    assert verifier._jwks_client is not None

    def _raise(token: str) -> str:
        raise jwt.PyJWKClientError("no matching key")

    monkeypatch.setattr(verifier._jwks_client, "get_signing_key_from_jwt", _raise)

    private_pem, _ = _generate_rsa_keypair()
    token = jwt.encode(_base_claims(), private_pem, algorithm="RS256")

    assert await verifier.verify_token(token) is None
