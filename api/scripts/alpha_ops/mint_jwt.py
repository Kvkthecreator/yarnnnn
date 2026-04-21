#!/usr/bin/env python3
"""
Mint a fresh production JWT for a persona.

Usage:
    python -m api.scripts.alpha_ops.mint_jwt alpha-trader
    python -m api.scripts.alpha_ops.mint_jwt alpha-commerce

Prints the access token on stdout so it can be piped:
    export JWT=$(python -m api.scripts.alpha_ops.mint_jwt alpha-trader)
    curl -H "Authorization: Bearer $JWT" https://yarnnn-api.onrender.com/api/memory/user/onboarding-state

JWTs are typically valid for 1 hour. Mint a fresh one each session.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shared import load_registry, mint_jwt  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Mint a short-lived JWT for an alpha persona.")
    ap.add_argument("persona", help="Persona slug (e.g. alpha-trader, alpha-commerce)")
    args = ap.parse_args()

    registry = load_registry()
    persona = registry.require(args.persona)
    jwt = mint_jwt(persona, registry=registry)
    print(jwt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
