"""ADR-595 gate — Strings is the tending surface.

Holds:
  §1 the content law — the desk view NEVER serves the maintained file's
     contents (enforced at the model), and the FE renders no private file
     face (composition-anchored, comments stripped)
  §2 source enrichment DRIVEN — receipt-prefix derivation, receipts,
     aperture standing, contribution mapping (ADR-595 D3)
  §3 the tabs — four, wired, with loud states ABOVE them
  §4 sources as parties — standing/receipt/seed affordances wired

Script-style (python3, from api/).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
REPO = API.parent
sys.path.insert(0, str(API))

PASS = 0
FAIL = 0


def check(label: str, ok, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))


def _strip_ts_comments(src: str) -> str:
    """Drop /* … */ blocks and whitespace-led // line comments so a check can
    never pass (or fail) against prose (the ADR-587 gate lesson)."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$", "", src)


# ═════════════════════════════════════════════════════════════════════════════
print("§1 the content law — situation, never contents")
# ═════════════════════════════════════════════════════════════════════════════

from routes.strings import StringSource, StringView  # noqa: E402

check("1a StringView serves NO content field (the law at the model)",
      "content" not in StringView.model_fields,
      str(sorted(StringView.model_fields)))
check("1b head FACTS ride instead (updated_at · lines · bytes)",
      {"head_updated_at", "head_lines", "head_bytes"} <= set(StringView.model_fields))

FE = REPO / "web" / "components" / "strings" / "StringsSurface.tsx"
fe = _strip_ts_comments(FE.read_text())

check("1c the FE never reads a view content field",
      "view.content" not in fe and "FileCanvas" not in fe and "CsvTable" not in fe)
_md_uses = re.findall(r"MarkdownRenderer\s+content=\{([^}]+)\}", fe)
check("1d every MarkdownRenderer in the pane renders the CONTRACT, never the file",
      bool(_md_uses) and all("contract" in u for u in _md_uses), str(_md_uses))
check("1e the Open door exists — reading happens at the file's own surface",
      "Open file" in fe and "openInFiles(view.target_path)" in fe)


# ═════════════════════════════════════════════════════════════════════════════
print("§2 source enrichment — DRIVEN (ADR-595 D3)")
# ═════════════════════════════════════════════════════════════════════════════

from routes.strings import _enrich_sources, _receipt_prefix  # noqa: E402

_conn_src = StringSource(id="standup", connector="slack", selector="C001")
_http_src = StringSource(id="mrr-feed", url="https://example.com/mrr.csv")

check("2a a connector source's receipt prefix is the fixed intake lane",
      _receipt_prefix(_conn_src) == "/workspace/inbound/slack/c001/",
      str(_receipt_prefix(_conn_src)))
_http_prefix = _receipt_prefix(_http_src)
check("2b an http source's receipt prefix is its inbound/web slug lane",
      _http_prefix is not None and _http_prefix.startswith("/workspace/inbound/web/")
      and _http_prefix.endswith("/"), str(_http_prefix))


class _Q:
    """A minimal supabase-chain fake routed by table + like-pattern."""

    def __init__(self, table: str, state: dict):
        self._table = table
        self._state = state
        self._like: str | None = None
        self._eq: dict = {}

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._eq[col] = val
        return self

    def like(self, _col, pattern):
        self._like = pattern
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        from types import SimpleNamespace
        if self._table == "workspace_files":
            # Only the slack source has a landed receipt.
            if self._like and self._like.startswith("/workspace/inbound/slack/c001/"):
                return SimpleNamespace(data=[{
                    "path": "/workspace/inbound/slack/c001/2026-08-21T09:00:00Z.md",
                    "created_at": "2026-08-21T09:00:00Z",
                }])
            return SimpleNamespace(data=[])
        if self._table == "platform_connections":
            return SimpleNamespace(data=[{
                "platform": "slack",
                "landscape": {"selected_sources": [{"id": "C001"}]},
                "settings": {}, "status": "active",
                "user_id": "u1", "connected_by": None,
            }])
        if self._table == "workspace_file_versions":
            return SimpleNamespace(data=[{
                "created_at": "2026-08-21T09:01:00Z",
                "derived_from": ["/workspace/inbound/slack/c001/2026-08-21T09:00:00Z.md"],
            }])
        return SimpleNamespace(data=[])


class _C:
    def table(self, name):
        return _Q(name, {})


_sources = [
    StringSource(id="standup", connector="slack", selector="C001"),
    StringSource(id="offsel", connector="slack", selector="C999"),
    StringSource(id="mrr-feed", url="https://example.com/mrr.csv"),
]
_enrich_sources(_C(), "u1", _sources, "/workspace/operation/kpi/weekly.md")
_by_id = {s.id: s for s in _sources}

check("2c the landed receipt is composed per source (path + stamp)",
      _by_id["standup"].last_landed_path
      == "/workspace/inbound/slack/c001/2026-08-21T09:00:00Z.md"
      and _by_id["standup"].last_landed_at == "2026-08-21T09:00:00Z")
check("2d aperture standing: a selected selector reads inside, an unselected "
      "one reads OUTSIDE (the ADR-594 intersection law, visible)",
      _by_id["standup"].in_aperture is True
      and _by_id["offsel"].in_aperture is False)
check("2e an http source carries NO aperture (not applicable, never false)",
      _by_id["mrr-feed"].in_aperture is None)
check("2f contribution: the revision citing this source's receipt marks it",
      _by_id["standup"].last_contributed_at == "2026-08-21T09:01:00Z"
      and _by_id["offsel"].last_contributed_at is None)
check("2g a source with nothing landed reports the honest empty",
      _by_id["offsel"].last_landed_path is None)


# ═════════════════════════════════════════════════════════════════════════════
print("§3 the tabs — four, wired, loudness above")
# ═════════════════════════════════════════════════════════════════════════════

check("3a the four tabs are declared",
      all(f"key: '{k}'" in fe for k in ("overview", "sources", "activity", "contract")))
check("3b the tab bar is composed from the declaration (no hand-kept copy)",
      "STRINGS_TABS.map" in fe and "setTab(t.key)" in fe)
# The params map is the FIRST bracketed `strings:` row (a keyPrefix string
# earlier in the file also contains "strings:" — a plain split matched it).
_prefs = _strip_ts_comments(
    (REPO / "web" / "lib" / "shell" / "surface-preferences.ts").read_text()
)
_strings_rows = re.findall(r"strings:\s*\[([^\]]*)\]", _prefs)
check("3c the tab param is registered on the surface",
      bool(_strings_rows) and "'tab'" in _strings_rows[0], str(_strings_rows[:1]))

_repair_at = fe.find("desk.phase === 'repair'")
_tabs_at = fe.find('aria-label="String tabs"')
check("3d loud states render ABOVE the tabs — a repair is never behind one",
      0 <= _repair_at < _tabs_at, f"repair@{_repair_at} tabs@{_tabs_at}")


# ═════════════════════════════════════════════════════════════════════════════
print("§4 sources as parties — the affordances are wired")
# ═════════════════════════════════════════════════════════════════════════════

check("4a the standing branch renders (outside-the-aperture is stated, "
      "not a generic empty)",
      "in_aperture === false" in fe and "outside your" in fe)
check("4b the receipt is an openable door",
      "openInFiles(s.last_landed_path)" in fe)
check("4c per-source seeds carry the source id",
      "Change source '${s.id}'" in fe and "Remove source '${s.id}'" in fe)
check("4d the arity law is stated in the pane, not discovered by refusal",
      "exactly one feed" in fe and "PROSE_SOURCE_CAP" in fe)

# ═════════════════════════════════════════════════════════════════════════════
print("§5 setup is first-class (D4) — the pane carries the act")
# ═════════════════════════════════════════════════════════════════════════════

check("5a the unconfigured pane renders the anatomy slots, not a placard",
      "SetupPanel" in fe and fe.count("SetupSlot") >= 4)
check("5b the aperture is surfaced at designation (selected slices fetched "
      "across the connection roster, not guessed in prose)",
      "getCaptureSignal" in fe and "FRESHNESS_PROVIDERS" in fe
      and ".filter((d) => d.selected)" in fe)
check("5c an aperture chip's seed carries the SELECTOR ID (the declaration "
      "needs the id; the name is display)",
      "(${s.id})" in fe)
check("5d the one direct gesture survives — the file pick, in slot one",
      "Pick the file to keep current" in fe)
check("5e the contract slot fills live from the substrate",
      "done={!!contract}" in fe)

n = PASS + FAIL
print(f"\n{PASS}/{n} ADR-595 assertions pass")
sys.exit(0 if FAIL == 0 else 1)
