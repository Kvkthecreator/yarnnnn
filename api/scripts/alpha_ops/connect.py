#!/usr/bin/env python3
"""
Connect a persona's external platform credentials to their YARNNN workspace.

Usage:
    python -m api.scripts.alpha_ops.connect alpha-trader
    python -m api.scripts.alpha_ops.connect alpha-commerce

What it does:
    1. Looks up the persona in docs/alpha/personas.yaml
    2. Reads the persona's credentials from env vars named in credentials_env:
       - alpha-trader:   ALPHA_TRADER_ALPACA_KEY + ALPHA_TRADER_ALPACA_SECRET
       - alpha-commerce: ALPHA_COMMERCE_LEMONSQUEEZY_KEY
    3. Mints a JWT for the persona's user_id
    4. Calls the production connect endpoint:
       - trading:  POST /api/integrations/trading/connect  (ADR-187)
       - commerce: POST /api/integrations/commerce/connect (ADR-183)

Credentials never leave your machine: scripts POST them to prod over TLS,
where Render decrypts+encrypts with INTEGRATION_ENCRYPTION_KEY (a secret
neither you nor Claude have access to locally — by design).

Idempotent: the connect endpoints upsert. Re-running rotates the stored key.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shared import ProdClient, load_registry  # noqa: E402


def _build_payload(persona) -> tuple[str, dict]:
    kind = persona.platform_kind
    env = persona.credentials_env

    if kind == "trading":
        key = os.environ.get(env["api_key"])
        secret = os.environ.get(env["api_secret"])
        if not key or not secret:
            raise SystemExit(
                f"Missing credentials. Set {env['api_key']} and {env['api_secret']} in env. "
                f"Retrieve from: {persona.vault_entry}"
            )
        payload = {
            "api_key": key,
            "api_secret": secret,
            "paper": persona.platform.get("mode", "paper") == "paper",
        }
        return "/api/integrations/trading/connect", payload

    if kind == "commerce":
        key = os.environ.get(env["api_key"])
        if not key:
            raise SystemExit(
                f"Missing credentials. Set {env['api_key']} in env. "
                f"Retrieve from: {persona.vault_entry}"
            )
        payload = {"api_key": key}
        return "/api/integrations/commerce/connect", payload

    raise SystemExit(f"Unsupported platform kind: {kind}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Connect external platform creds to a persona workspace.")
    ap.add_argument("persona", help="Persona slug (e.g. alpha-trader, alpha-commerce)")
    args = ap.parse_args()

    registry = load_registry()
    persona = registry.require(args.persona)

    path, payload = _build_payload(persona)

    with ProdClient(persona, registry=registry) as client:
        r = client.post(path, json=payload)

    if r.status_code >= 300:
        print(f"connect failed [{r.status_code}]: {r.text}", file=sys.stderr)
        return 1

    print(json.dumps(r.json(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
