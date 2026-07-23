#!/usr/bin/env python3
"""Poll ``/ready`` until the server reports ready or a timeout elapses.

Intended for use between "deploy" and "smoke test" steps in a CI/CD pipeline
(see the "Deployment Pipeline" section of
docs/research_intelligence_mcp_deployment.md) and for local container
testing. Exits non-zero on timeout so it can gate a pipeline step.

Example:

    uv run python deployment/scripts/wait_for_ready.py \\
        --base-url http://127.0.0.1:8000 \\
        --timeout-seconds 60
"""

from __future__ import annotations

import argparse
import sys
import time

import httpx


def wait_for_ready(
    *,
    base_url: str,
    timeout_seconds: float,
    poll_interval_seconds: float,
) -> bool:
    """Poll ``{base_url}/ready`` until it returns 200 or the timeout elapses."""

    deadline = time.monotonic() + timeout_seconds
    url = f"{base_url.rstrip('/')}/ready"

    last_error: str | None = None

    with httpx.Client(timeout=5.0) as client:
        while time.monotonic() < deadline:
            try:
                response = client.get(url)
            except httpx.HTTPError as exc:
                last_error = str(exc)
            else:
                if response.status_code == 200:
                    print(f"ready: {response.json()}")
                    return True

                last_error = f"HTTP {response.status_code}: {response.text}"

            time.sleep(poll_interval_seconds)

    print(f"timed out waiting for {url} to become ready: {last_error}", file=sys.stderr)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Server base URL, without a trailing /ready or /mcp.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=2.0)
    args = parser.parse_args()

    ready = wait_for_ready(
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
        poll_interval_seconds=args.poll_interval_seconds,
    )

    sys.exit(0 if ready else 1)


if __name__ == "__main__":
    main()
