"""
Shared helpers for Alpha-1 operator scripts.

Reads persona registry from docs/alpha/personas.yaml. Mints short-lived JWTs
via the Supabase admin magic-link OTP flow (same pattern documented in
docs/database/ACCESS.md). Provides a lightweight prod-API client that injects
the JWT so the connect/verify/reset scripts don't each reimplement auth.

Env vars required:
    SUPABASE_SERVICE_KEY   - service-role key (same as docs/database/ACCESS.md)
    ALPHA_TRADER_ALPACA_KEY + ALPHA_TRADER_ALPACA_SECRET  (for connect.py trading)
    ALPHA_COMMERCE_LEMONSQUEEZY_KEY                        (for connect.py commerce)

All loaded from a .env file in api/ or the shell environment. Nothing
secret-bearing is ever read from the yaml registry.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Make this package importable whether invoked as `python verify.py` from
# the alpha_ops dir or as `python scripts/alpha_ops/verify.py` from api/.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

# Silence the "please upgrade" banner on older supabase-py; we pin elsewhere.
try:
    import yaml  # type: ignore[import-untyped]
except ImportError as exc:
    print(f"Missing dependency: PyYAML. Install with `pip install pyyaml`.", file=sys.stderr)
    raise SystemExit(1) from exc

import httpx

# dotenv is optional — scripts run fine with exported env vars too.
try:
    from dotenv import load_dotenv

    _ENV_PATH = _THIS_DIR.parents[1] / ".env"  # api/.env
    if not _ENV_PATH.exists():
        _ENV_PATH = _THIS_DIR.parents[2] / ".env"  # repo/.env
    load_dotenv(_ENV_PATH)
except ImportError:
    pass


REPO_ROOT = _THIS_DIR.parents[2]  # api/scripts/alpha_ops -> repo root
REGISTRY_PATH = REPO_ROOT / "docs" / "alpha" / "personas.yaml"


@dataclass(frozen=True)
class Persona:
    slug: str
    label: str
    email: str
    user_id: str
    workspace_id: str
    # ADR-230 D1: every persona declares the program it activates. Validated
    # at load_registry() time against docs/programs/{program}/MANIFEST.yaml.
    # Persona slug and program slug are independent — alpha-trader + alpha-
    # trader-2 both have program="alpha-trader".
    program: str
    platform: dict[str, Any]
    context_domains: list[str]
    credentials_env: dict[str, str]
    vault_entry: str
    expected: dict[str, Any]

    @property
    def platform_kind(self) -> str:
        return self.platform["kind"]

    @property
    def platform_provider(self) -> str:
        return self.platform["provider"]


@dataclass(frozen=True)
class Registry:
    supabase_url: str
    prod_api_base: str
    personas: dict[str, Persona]

    def require(self, slug: str) -> Persona:
        if slug not in self.personas:
            available = ", ".join(sorted(self.personas))
            raise SystemExit(f"unknown persona '{slug}' (available: {available})")
        return self.personas[slug]


_PROGRAMS_ROOT = REPO_ROOT / "docs" / "programs"


def _validate_program(persona_slug: str, program_slug: str | None) -> str:
    """ADR-230 D1: every persona must declare a `program` field whose
    target bundle exists at docs/programs/{program}/. Fail fast at load
    time so any operation against an unlinked persona errors with a
    clear message instead of silently using kernel defaults later.
    """
    if not program_slug:
        raise SystemExit(
            f"persona '{persona_slug}' has no `program` field. "
            f"Per ADR-230 D1 every persona must declare which program it "
            f"activates (e.g. `program: alpha-trader`). Add the field to "
            f"docs/alpha/personas.yaml."
        )
    bundle_dir = _PROGRAMS_ROOT / program_slug
    manifest = bundle_dir / "MANIFEST.yaml"
    if not manifest.exists():
        raise SystemExit(
            f"persona '{persona_slug}' declares program='{program_slug}' but "
            f"docs/programs/{program_slug}/MANIFEST.yaml does not exist. "
            f"Either fix the persona's program field or ship the bundle."
        )
    return program_slug


def load_registry() -> Registry:
    if not REGISTRY_PATH.exists():
        raise SystemExit(f"persona registry missing: {REGISTRY_PATH}")
    raw = yaml.safe_load(REGISTRY_PATH.read_text())
    personas = {
        p["slug"]: Persona(
            slug=p["slug"],
            label=p["label"],
            email=p["email"],
            user_id=p["user_id"],
            workspace_id=p["workspace_id"],
            program=_validate_program(p["slug"], p.get("program")),
            platform=p["platform"],
            context_domains=p.get("context_domains", []),
            credentials_env=p.get("credentials_env", {}),
            vault_entry=p.get("vault_entry", ""),
            expected=p.get("expected", {}),
        )
        for p in raw.get("personas", [])
    }
    return Registry(
        supabase_url=raw["supabase"]["url"],
        prod_api_base=raw["api"]["prod_base_url"],
        personas=personas,
    )


def _require_env(var: str) -> str:
    val = os.environ.get(var)
    if not val:
        raise SystemExit(f"{var} not set. Export it or add to api/.env.")
    return val


def mint_jwt(persona: Persona, *, registry: Registry | None = None) -> str:
    """Mint a short-lived access token for a persona via admin magic-link OTP.

    Identical mechanics to the snippet in docs/database/ACCESS.md. Uses the
    Supabase admin API (service-role key) to generate a magic-link token hash,
    then exchanges the OTP for a session access_token.

    Returns the JWT string. Typically valid for 1 hour.
    """
    registry = registry or load_registry()
    service_key = _require_env("SUPABASE_SERVICE_KEY")
    base = registry.supabase_url.rstrip("/")

    with httpx.Client(timeout=20.0) as client:
        # 1. Ask admin API to generate a magic-link OTP for the user email.
        r = client.post(
            f"{base}/auth/v1/admin/generate_link",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
            },
            json={"type": "magiclink", "email": persona.email},
        )
        if r.status_code >= 300:
            raise SystemExit(f"admin generate_link failed [{r.status_code}]: {r.text}")
        payload = r.json()
        # Supabase returns the token_hash in a few possible shapes.
        properties = payload.get("properties") or payload
        token_hash = properties.get("hashed_token") or properties.get("token_hash")
        if not token_hash:
            raise SystemExit(f"admin generate_link: no token_hash in response: {payload}")

        # 2. Exchange the OTP token_hash for a session access token.
        r = client.post(
            f"{base}/auth/v1/verify",
            headers={
                "apikey": service_key,
                "Content-Type": "application/json",
            },
            json={
                "type": "magiclink",
                "token_hash": token_hash,
            },
        )
        if r.status_code >= 300:
            raise SystemExit(f"OTP verify failed [{r.status_code}]: {r.text}")
        access_token = r.json().get("access_token")
        if not access_token:
            raise SystemExit(f"OTP verify: no access_token in response: {r.text}")
        return access_token


class ProdClient:
    """Thin wrapper around the production API with JWT auth injected."""

    def __init__(self, persona: Persona, registry: Registry | None = None):
        self.persona = persona
        self.registry = registry or load_registry()
        self.jwt = mint_jwt(persona, registry=self.registry)
        self.base = self.registry.prod_api_base.rstrip("/")
        self._client = httpx.Client(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.jwt}",
                "Content-Type": "application/json",
            },
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ProdClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._client.get(f"{self.base}{path}", **kwargs)

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._client.post(f"{self.base}{path}", **kwargs)

    def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._client.delete(f"{self.base}{path}", **kwargs)


# Supabase direct DB access (for verify.py) — separate from ProdClient since
# verify is read-only and we have the service key anyway.
PG_CONN_STRING = (
    "postgresql://postgres.noxgqcwynkzqabljjyon:"
    "yarNNN%21%21%40%40%23%23%24%24"
    "@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
)


def pg_connect():
    """Return a psycopg2 connection to the shared Supabase Postgres.

    Connection string is the one documented in docs/database/ACCESS.md.
    URL-encoded password is intentional — do not "simplify".
    """
    try:
        import psycopg2  # type: ignore[import-untyped]
    except ImportError as exc:
        raise SystemExit("Missing dependency: psycopg2-binary. pip install psycopg2-binary") from exc
    return psycopg2.connect(PG_CONN_STRING)


# ----------------------------------------------------------------------------
# Cost-truth rollup — single source for per-workspace platform cost (SCOPE.md)
# ----------------------------------------------------------------------------
#
# Reads token_usage (ADR-171 universal LLM ledger) and produces two views:
#   - by_day: total cost per calendar day over the window
#   - by_caller_and_slug: breakdown over the window, joining metadata->>slug
#
# Anything else that needs cost-truth (cockpit element, future endpoint) reads
# this. Singular implementation: don't reimplement the SQL anywhere.
#
# Note: this is LLM cost only. Render service usage (ADR-118) is currently
# tracked via the `render_usage` RPC counter, not a queryable table — it's a
# smaller cost contributor in practice, but a follow-up should add it to the
# same rollup for full cost-truth honesty per SCOPE.md.


def fetch_cost_rollup(
    user_id: str,
    days: int = 7,
) -> dict[str, Any]:
    """Pull a per-workspace cost-truth rollup over the last `days` calendar days.

    Returns:
        {
            "user_id": str,
            "window_days": int,
            "since": str (iso),
            "total_cost_usd": float,
            "total_input_tokens": int,
            "total_output_tokens": int,
            "by_day": [
                {"day": "2026-04-29", "cost_usd": 1.23, "calls": 8},
                ...
            ],
            "by_caller_and_slug": [
                {
                    "caller": "invocation_dispatcher",
                    "slug": "track-universe-2",
                    "shape": "accumulation",
                    "calls": 5,
                    "input_tokens": 1246673,
                    "output_tokens": 30602,
                    "cost_usd": 8.40,
                },
                ...
            ],
        }
    """
    conn = pg_connect()
    cur = conn.cursor()

    # Window boundary
    cur.execute("SELECT NOW() - INTERVAL '%s days'" % int(days))
    since = cur.fetchone()[0].isoformat()

    # Total + tokens
    cur.execute(
        """
        SELECT
            COALESCE(SUM(cost_usd), 0)::float,
            COALESCE(SUM(input_tokens), 0)::int,
            COALESCE(SUM(output_tokens), 0)::int
        FROM token_usage
        WHERE user_id = %s
          AND created_at > NOW() - INTERVAL '%s days'
        """ % ("%s", int(days)),
        (user_id,),
    )
    total_cost, total_in, total_out = cur.fetchone()

    # By calendar day
    cur.execute(
        """
        SELECT
            DATE(created_at AT TIME ZONE 'UTC') AS day,
            ROUND(SUM(cost_usd)::numeric, 4)::float AS cost_usd,
            COUNT(*)::int AS calls
        FROM token_usage
        WHERE user_id = %s
          AND created_at > NOW() - INTERVAL '%s days'
        GROUP BY day
        ORDER BY day DESC
        """ % ("%s", int(days)),
        (user_id,),
    )
    by_day = [
        {"day": row[0].isoformat(), "cost_usd": row[1], "calls": row[2]}
        for row in cur.fetchall()
    ]

    # By caller + recurrence slug + shape (metadata-driven breakdown)
    cur.execute(
        """
        SELECT
            caller,
            metadata->>'slug' AS slug,
            metadata->>'shape' AS shape,
            COUNT(*)::int AS calls,
            COALESCE(SUM(input_tokens), 0)::int AS input_tokens,
            COALESCE(SUM(output_tokens), 0)::int AS output_tokens,
            ROUND(SUM(cost_usd)::numeric, 4)::float AS cost_usd
        FROM token_usage
        WHERE user_id = %s
          AND created_at > NOW() - INTERVAL '%s days'
        GROUP BY caller, slug, shape
        ORDER BY cost_usd DESC
        """ % ("%s", int(days)),
        (user_id,),
    )
    by_caller_and_slug = [
        {
            "caller": row[0],
            "slug": row[1],
            "shape": row[2],
            "calls": row[3],
            "input_tokens": row[4],
            "output_tokens": row[5],
            "cost_usd": row[6],
        }
        for row in cur.fetchall()
    ]

    cur.close()
    conn.close()

    return {
        "user_id": user_id,
        "window_days": days,
        "since": since,
        "total_cost_usd": round(total_cost, 4),
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "by_day": by_day,
        "by_caller_and_slug": by_caller_and_slug,
    }


def format_cost_rollup(rollup: dict[str, Any]) -> str:
    """Format a cost rollup as a human-readable text block for verify.py output."""
    lines = []
    days = rollup["window_days"]
    total = rollup["total_cost_usd"]

    # Project to monthly rate for sanity-check against money-truth
    daily_avg = total / max(days, 1)
    monthly_proj = daily_avg * 30

    lines.append(f"Cost-truth rollup — last {days} days")
    lines.append(f"  Total: ${total:.4f}  ({rollup['total_input_tokens']:,} in / "
                 f"{rollup['total_output_tokens']:,} out tokens)")
    lines.append(f"  Daily average: ${daily_avg:.4f}  →  monthly projection ${monthly_proj:.2f}")
    lines.append("")

    if rollup["by_day"]:
        lines.append("  By day:")
        for entry in rollup["by_day"][:10]:
            lines.append(f"    {entry['day']}: ${entry['cost_usd']:.4f} ({entry['calls']} calls)")
        lines.append("")

    if rollup["by_caller_and_slug"]:
        lines.append("  By caller × recurrence (top 10 by cost):")
        for entry in rollup["by_caller_and_slug"][:10]:
            slug = entry["slug"] or "<no slug>"
            shape = entry["shape"] or "—"
            lines.append(
                f"    [{entry['caller']:22}] {slug:32} ({shape:14}) "
                f"${entry['cost_usd']:.4f} × {entry['calls']} calls"
            )

    return "\n".join(lines)
