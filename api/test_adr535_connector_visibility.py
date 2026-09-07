"""ADR-535 — a bound connector is VISIBLE to the member's lane.

Run: python3 test_adr535_connector_visibility.py   (NOT pytest — check()-gates
print ✗ but pytest would PASS them; this file's exit code is the signal.)

What it protects:
  1. The member's binding INVENTORY is on the lane surface (D2) — a lane that
     cannot see a binding guesses about it, and guessed wrong on a live surface
     (§1: "this workspace doesn't have a live Notion connector", said over an
     active Notion binding).
  2. ⚠️ THE CEILING HOLDS (D2 preserves ADR-463 D4.a) — visibility is NOT reach.
     No `platform_*` tool may ride onto the lane surface behind this addition.
  3. ⚠️ THE FRAME STATES ITS OWN EDGE (D3). This is the half with no gate of its
     own in the D4.a derivation: `list_integrations` clears the ceiling
     mechanically, so nothing in the existing gates would notice if the prose
     re-closed the world or dropped the can't-read-through clause. A model
     handed an inventory with no stated edge infers the reach. That inference is
     a prompt defect the derivation cannot see, which is why it is gated HERE.
  4. The metadata boundary is real — the primitive reads platform_connections,
     never a provider API, never a credential.

Made to fail (verified 2026-08-07): removing `list_integrations` from
LANE_SURFACE_EXTRA turns 4 red; restoring the closed-world sentence turns 1 red;
dropping the can't-read-through clause turns 1 red; adding a `platform_*` name
to the surface turns 2 red.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.lane_runner import (  # noqa: E402
    LANE_SURFACE_EXTRA,
    LANE_TOOL_NAMES,
    build_lane_conventions,
    lane_tool_names,
    lane_tools_openai,
)
from services.primitives.permission import READ_ONLY_PRIMITIVES  # noqa: E402

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"  {'✓' if cond else '✗'} {label}")


class _EmptyResp:
    data: list = []


class _EmptyQuery:
    def select(self, *a, **k): return self
    def eq(self, *a, **k): return self
    def like(self, *a, **k): return self
    def order(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def execute(self): return _EmptyResp()


class _EmptyClient:
    def table(self, *a, **k): return _EmptyQuery()


def _frame(agent=None) -> str:
    model = "gemini/gemini-2.5-flash" if agent else "anthropic/claude-sonnet-4-6"
    return build_lane_conventions(
        _EmptyClient(), "u_test", model=model, agent=agent, member_label="Kev"
    )


def _tools_section(frame: str) -> str:
    return frame.split("## Your tools", 1)[1].split("## Format discipline", 1)[0]


def run() -> bool:
    print("\n── 1. D2 — the binding inventory is ON the surface ──")
    _check(
        "list_integrations is on the uniform lane surface",
        "list_integrations" in LANE_SURFACE_EXTRA,
    )
    _check(
        "…and therefore in the EXECUTION allowlist",
        "list_integrations" in lane_tool_names(),
    )
    _payload = {t["function"]["name"] for t in lane_tools_openai()}
    _check(
        "…and in the DECLARED payload the model receives",
        "list_integrations" in _payload,
    )
    _check(
        "the three-way agreement still holds exactly (payload == allowlist)",
        _payload == set(lane_tool_names()),
    )

    print("\n── 2. ⚠️  THE CEILING (ADR-463 D4.a) — visibility is NOT reach ──")
    # The addition rides the EXISTING derivation; it does not widen it. If a
    # future session ever needs to widen READ_ONLY_PRIMITIVES to make a lane
    # addition fit, that is the signal it does not belong on the surface.
    _check(
        "list_integrations was ALREADY a non-consequential read (nothing widened)",
        "list_integrations" in READ_ONLY_PRIMITIVES,
    )
    # ADR-568 D3 restates the ceiling: every extra is CLASSIFIED by the
    # permission layer — a read, or an artifact verb that passes the gate.
    # ADR-535's own claim (list_integrations widened nothing) is untouched
    # above; this loop no longer asserts that EVERY extra must be a read,
    # because `GenerateImage` is deliberately consequential.
    from services.lane_runner import LANE_ARTIFACT_VERBS

    for _t in LANE_SURFACE_EXTRA:
        _check(
            f"surface extra {_t!r} derives from permission.py's own classification",
            _t in READ_ONLY_PRIMITIVES or _t in LANE_ARTIFACT_VERBS,
        )
    # ⚠️ THE ONE THAT MATTERS. Seeing a connector must never become reading
    # through one. A `platform_*` name on this surface IS connector reach —
    # the ADR-420 §10 demand-gate + moat-leak test govern that, not this ADR.
    _check(
        "NO platform_* tool rode onto the lane surface (reach stays gated)",
        not any(t.startswith("platform_") for t in lane_tool_names()),
    )
    # ADR-535's claim is that IT added no tools to the file-verb half — not
    # that the half can never grow. Pinning the exact tuple made any later
    # legitimate change (2026-08-21: DeleteFile + MoveFile, closing the
    # lane-vs-MCP asymmetry) read as an ADR-535 violation. Assert the
    # INVARIANT instead: the file half is file verbs only, no connector reach
    # smuggled in among them.
    # ADR-337 D8 (2026-08-21) added the folder grain to the same half.
    _check(
        "the file+folder half carries only substrate verbs (no reach among them)",
        all(
            t in {"ReadFile", "WriteFile", "EditFile", "DeleteFile",
                  "MoveFile", "DeleteFolder", "MoveFolder", "Restore",
                  "SearchFiles", "ListFiles"}
            for t in LANE_TOOL_NAMES
        ),
    )

    print("\n── 3. ⚠️  D3 — the frame STATES ITS OWN EDGE (all four reach states) ──")
    # The frame previously asserted a CLOSED WORLD ("you read this member's
    # commons and the open web"). D2 falsifies that sentence. Left standing it
    # is the Scout bug inverted: prose DENYING a surface the model holds.
    #
    # RE-CUT 2026-09-07. This section asserted one literal sentence — "cannot
    # read through it" — against whichever branch the deployment default
    # happened to take. ADR-615 landed reach and moved that default, so the
    # check went RED against prose that was live-CORRECT: the lane now holds
    # nine platform_* read tools, and telling it otherwise would be the very
    # hallucination-one-rung-off this section exists to prevent. The pinned
    # sentence had become the defect (Part Q: a gate that pins a spelling pins
    # the defect).
    #
    # `resolve_turn_reach` documents FOUR states. Each states a DIFFERENT true
    # edge, so the invariant is not one sentence — it is that every state names
    # the inventory tool, states its own edge truthfully, and never denies a
    # binding it can see. Drive all four; the pre-615 sentence survives as the
    # assertion for the two states where it is still true.
    import services.lane_runner as _lr

    _REACH_STATES = (
        # (label, (has_reach, platforms), must-contain, must-NOT-contain)
        # ⚠️ The two no-reach states must NOT render the same prose. They were
        # identical until 2026-09-07 because the branch guard keyed on `_reach`
        # (unreachable as True with empty platforms), so scoped-to-nothing got
        # the darkened wording and was offered a remedy that does not apply.
        ("darkened", (False, None),
         ("cannot read through", "paste it"), ("on your agent page",)),
        ("scoped-to-nothing", (False, ()),
         ("cannot read through", "scoped you to no connections",
          "widen your connections on your agent page"),
         ("connect in settings",)),
        ("unscoped", (True, None),
         ("read through",), ("cannot read through",)),
        ("scoped-to-slack", (True, ("slack",)),
         ("you can read through", "slack"), ("cannot read through",)),
    )

    for _label, _state, _must, _must_not in _REACH_STATES:
        _orig = _lr.resolve_turn_reach
        _lr.resolve_turn_reach = lambda *a, **k: _state
        try:
            _sec = _tools_section(_frame(None))
        finally:
            _lr.resolve_turn_reach = _orig
        # Collapse the wrap: the fact is the sentence, not where it breaks.
        _low = " ".join(_sec.lower().split())
        _check(
            f"[{_label}] the frame NAMES the inventory tool",
            "list_integrations" in _sec,
        )
        # ⚠️ Without an edge clause a model that can SEE a Notion binding infers
        # what it may DO with it, and hallucinates one rung above what it holds.
        # Naming a capability's edge is part of granting it — in BOTH directions:
        # a lane WITH reach that is told it cannot read will refuse work it can do.
        for _frag in _must:
            _check(
                f"[{_label}] …states its own edge: {_frag!r}",
                _frag in _low,
            )
        for _frag in _must_not:
            _check(
                f"[{_label}] …and does not state an edge it does not have: {_frag!r}",
                _frag not in _low,
            )
        _check(
            f"[{_label}] …and does not claim the connector is absent",
            "no live" not in _low,
        )

    print("\n── 4. the metadata boundary is real ──")
    import inspect
    from services.primitives.registry import handle_list_integrations

    _src = inspect.getsource(handle_list_integrations)
    _check(
        "the handler reads platform_connections (the binding row)",
        "platform_connections" in _src,
    )
    _check(
        "…scoped to THIS member (ADR-425 + ADR-408 D2 · ADR-460 — the lane's reach is the member's)",
        "user_id" in _src,
    )
    # Metadata only: no credential ever leaves the row, no provider is called.
    _check(
        "…and never decrypts a credential",
        "decrypt" not in _src and "credentials_encrypted" not in _src,
    )
    _check(
        "…and never calls a provider API client",
        not any(
            c in _src
            for c in ("get_notion_client", "get_slack_client", "get_github_client")
        ),
    )

    print()
    _failed = [lbl for lbl, ok in _results if not ok]
    if _failed:
        print(f"✗ {len(_failed)}/{len(_results)} FAILED:")
        for lbl in _failed:
            print(f"    - {lbl}")
        return False
    print(f"✓ {len(_results)}/{len(_results)} passed")
    return True


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
