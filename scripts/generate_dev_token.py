#!/usr/bin/env python3
"""Mint a local HS256 test JWT for exercising the streamable-http auth flow.

Development and testing use only. Signs with a shared secret you supply on
the command line — never point this at a production issuer or secret. See
docs/research_intelligence_mcp_authentication_testing.md.

Example:

    uv run python scripts/generate_dev_token.py \\
        --issuer https://auth.researchmind.ai \\
        --audience research-intelligence-mcp \\
        --secret dev-only-shared-secret-please-rotate \\
        --scope research-intelligence/invoke
"""

from __future__ import annotations

import argparse
import time

import jwt


def build_token(
    *,
    issuer: str,
    audience: str,
    secret: str,
    subject: str,
    scope: str,
    ttl_seconds: int,
) -> str:
    now = int(time.time())
    claims = {
        "iss": issuer,
        "aud": audience,
        "sub": subject,
        "scope": scope,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    return jwt.encode(claims, secret, algorithm="HS256")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--issuer", required=True, help="Must match AUTH_ISSUER exactly."
    )
    parser.add_argument("--audience", required=True, help="Must match AUTH_AUDIENCE.")
    parser.add_argument("--secret", required=True, help="Must match AUTH_JWT_SECRET.")
    parser.add_argument("--subject", default="researchmind-backend")
    parser.add_argument(
        "--scope",
        default="research-intelligence/invoke",
        help="Space-separated scopes. Must satisfy AUTH_REQUIRED_SCOPES.",
    )
    parser.add_argument("--ttl-seconds", type=int, default=300)
    args = parser.parse_args()

    token = build_token(
        issuer=args.issuer,
        audience=args.audience,
        secret=args.secret,
        subject=args.subject,
        scope=args.scope,
        ttl_seconds=args.ttl_seconds,
    )
    print(token)


if __name__ == "__main__":
    main()
