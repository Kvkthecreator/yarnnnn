"""Derive `services/connector_directory_seed.json` from upstream (ADR-635 D1).

The seed is CONSUMED, never authored: this script reads Anthropic's published
knowledge-work plugins — every `.mcp.json` server and the category each
plugin's CONNECTORS.md assigns it — and writes the seed stamped with the
repository and commit it was derived from. Re-run it to pick up upstream
changes; the diff is the change.

Usage:
    python3 scripts/refresh_connector_directory.py [/path/to/knowledge-work-plugins]

Without a path it clones a shallow copy into a temp dir.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

UPSTREAM = "https://github.com/anthropics/knowledge-work-plugins"
API = Path(__file__).resolve().parent.parent
SEED = API / "services" / "connector_directory_seed.json"

# Servers with no URL in upstream (the member supplies their own host).
# They stay in the seed as "bring your own URL" entries, with url=None
# refused by the loader — so they are recorded here for the refresh log
# and excluded from the seed itself.
_TABLE_RX = re.compile(r"^\|\s*([^|]+?)\s*\|\s*`~~([^`]+)`\s*\|\s*([^|]*?)\s*\|", re.M)


def _clone(tmp: str) -> Path:
    subprocess.run(["git", "clone", "--depth", "1", "--quiet", UPSTREAM, tmp], check=True)
    return Path(tmp)


def _commit(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          check=True, capture_output=True, text=True).stdout.strip()


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _category_map(plugin_dir: Path) -> dict[str, str]:
    """server-name (normalized) → category, from the plugin's CONNECTORS.md
    table: | Category | `~~placeholder` | Included servers | Other options |."""
    f = plugin_dir / "CONNECTORS.md"
    if not f.exists():
        return {}
    out: dict[str, str] = {}
    for m in _TABLE_RX.finditer(f.read_text(encoding="utf-8")):
        category = m.group(1).strip()
        if category.lower() in ("category",):
            continue
        for name in re.split(r",\s*", m.group(3)):
            name = re.sub(r"\\?\*", "", name).strip()
            name = re.sub(r"\s*\(.*?\)", "", name).strip()
            if name and name != "—":
                out[_norm(name)] = category
    return out


def _title_for(key: str, cfg_name: str) -> str:
    return re.sub(r"[-_]+", " ", cfg_name).strip().title() or key


def derive(repo: Path) -> dict:
    servers: dict[str, dict] = {}
    skipped: list[str] = []
    plugin_dirs = sorted(p for p in repo.iterdir() if p.is_dir() and not p.name.startswith("."))
    plugin_dirs += sorted(p for p in (repo / "partner-built").glob("*") if p.is_dir())
    for pdir in plugin_dirs:
        mcp = pdir / ".mcp.json"
        if not mcp.exists():
            continue
        try:
            cfg = json.loads(mcp.read_text(encoding="utf-8")).get("mcpServers", {})
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {pdir.name}: {exc}", file=sys.stderr)
            continue
        cats = _category_map(pdir)
        for name, spec in cfg.items():
            if not isinstance(spec, dict):
                continue
            url = (spec.get("url") or "").strip()
            if not url:
                skipped.append(f"{pdir.name}/{name}")
                continue
            if spec.get("type") not in (None, "http", "streamable-http", "sse"):
                skipped.append(f"{pdir.name}/{name} ({spec.get('type')})")
                continue
            key = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
            entry = servers.setdefault(url.rstrip("/"), {
                "key": key,
                "title": _title_for(key, name),
                "url": url,
                "category": None,
                "auth": ("header" if spec.get("headers") else
                         "preregistered" if spec.get("oauth") else "oauth-or-anonymous"),
                "plugins": [],
            })
            if pdir.name not in entry["plugins"]:
                entry["plugins"].append(pdir.name)
            cat = cats.get(_norm(name)) or cats.get(_norm(name.replace("-", " ")))
            if not cat:
                # try matching by the title words (e.g. "google-calendar" → "Google Calendar")
                for k, v in cats.items():
                    if k and (k in _norm(name) or _norm(name) in k):
                        cat = v
                        break
            if cat and not entry["category"]:
                entry["category"] = cat
    rows = sorted(servers.values(), key=lambda s: (s["key"], s["url"]))
    return {
        "source_repo": UPSTREAM,
        "source_commit": _commit(repo),
        "derived_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "derived_by": "api/scripts/refresh_connector_directory.py",
        "note": ("DERIVED, never hand-edited (ADR-635 D1). Every server is a "
                 "remote MCP endpoint Anthropic's knowledge-work plugins name; "
                 "category is the plugin's own CONNECTORS.md placeholder."),
        "skipped_no_url": sorted(skipped),
        "servers": rows,
    }


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1]:
        repo = Path(argv[1]).resolve()
        seed = derive(repo)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            seed = derive(_clone(tmp))
    SEED.write_text(json.dumps(seed, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {SEED.relative_to(API.parent)}: {len(seed['servers'])} servers "
          f"@ {seed['source_commit'][:8]} (skipped {len(seed['skipped_no_url'])} with no URL)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
