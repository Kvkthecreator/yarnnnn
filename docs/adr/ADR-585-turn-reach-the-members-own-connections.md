# ADR-585: Turn Reach — the Member's Own Connections, Inside Their Own Turn

> **Status**: DRAFT — proposed 2026-08-19, awaiting operator ratification.
> Nothing in this ADR is built; the lane allowlist stays closed until it is.
>
> **Disposition (declared first, per the intake-pipeline.md §5 rule)**: this
> is **TURN REACH** — an LLM calling a platform live inside a conversation
> turn, transient, the result dying with the turn unless explicitly saved.
> It is NOT intake: nothing lands automatically, nothing is retained, the
> capture writer (ADR-582) is untouched.
>
> **Dimensional classification (Axiom 0)**: **Mechanism** (platform tools
> enter member lane turns) + **Boundary** (whose credential a turn may
> wield).

---

## 1. The question, and the cut line

The operator, driving the deployed chat surface (2026-08-19): a lane engine
correctly reported the Notion connection as active and correctly refused to
read a pasted Notion link — then asked, *shouldn't chat's LLM be able to
utilize the user connections? while Agents and APP dedicated principals
adopt the workspace level settings and connections?*

The proposed cut line is **presence of the principal**:

- **A chat turn is the member, present, driving.** The LLM is the member's
  instrument for that turn. Letting it read the member's OWN connections is
  the member wielding their own credential through the shell — the mirror
  image of the MCP lane, where an external client acts in-session under its
  own grant (ADR-431).
- **Agents and apps are autonomous** — no principal present at execution.
  They keep exactly what canon gives them today: workspace substrate, landed
  capture files, never a credential (ADR-577; ADR-582 D6). **Unchanged.**

This reading is consistent with ADR-577's actual logic: its refusal was
never "LLMs must not touch platforms" — it was that the headless path fell
through to the OWNER's token with nobody present. A member-driven turn has
the principal present and consenting.

Canon left this door deliberately open: turn reach is a named seam
(connector-reach-and-the-commons.md §5), and the deleted
`get_platform_tools_for_user` entry states this is "the exact seam where
chat-reaches-connector would land," to be recreated **deliberately with a
surface, not by reviving an orphan**. This ADR is that deliberate recreation.

## 2. Decisions (proposed)

### D1 — The principal-presence rule

Turn reach exists ONLY in member-driven lane turns, and reaches ONLY the
connections of **the member driving the turn** (`platform_connections`
keyed by their `user_id`). Never the workspace owner's by fall-through —
a member without their own Notion connection gets an honest refusal even if
the owner has one. The ADR-577 chokepoint (`platform_credentials.py`)
resolves by the TURN's principal; the agent-caller refusal stays intact.

### D2 — The allowlist opens deliberately, behind a flag

`lane_runner`'s closed tool set (the "Seeing a connector is NOT reaching
through one" exclusion) is amended: platform read tools join member lane
turns for platforms the member has connected — behind a deploy flag
(`TURN_REACH_ENABLED`, default OFF), enforced at the transport like the
router flags (ADR-557: a flag a caller can forget is not a gate). Steward,
app lanes, and wake-path invocations get NOTHING (D1 — no principal
present).

### D3 — Transient by default; saving is an ordinary attributed write

Fetched content lives and dies in the turn's context. If the member asks to
keep something, the save is an ordinary substrate write attributed to the
turn's author, per the `mcp` lane precedent (intake-pipeline.md: `mcp`
correctly has no derive step). No auto-landing, no `inbound/` writes, no
`observation` rows — that is the capture writer's job and stays opt-in.

### D4 — The bound is the OAuth grant, plus declared narrowings

Turn reach is bounded by what the platform granted the member's token
(Notion's page-shares are already page-grained; the platform enforces).
Where a declared narrowing exists — the ADR-576 D2 GitHub selection — it
bounds turn reach the same way it bounds platform tools today (empty =
unrestricted, the ratified fail-open posture). The CAPTURE selection is
otherwise the writer's config, not a turn-reach permission (ADR-582 recut,
2026-08-19).

### D5 — The engine disclosure

A lane's engine is member-chosen and may be any provider (ADR-558/559).
Turn reach sends connection content into that engine as context — same
exposure as pasting it, but automatic. The consent surface (wherever the
flag's operator-facing dial lands) must say this in one sentence.

## 3. What this explicitly does not change

- Agents/apps: landed files only (ADR-582 D6); the ADR-577 credential
  refusal; the capture writer and its dials; the two-dispositions vocabulary
  (this ADR is the turn-reach half finally getting its decision).
- MCP inbound: ADR-563 scopes and ADR-573 binding are orthogonal.

## 4. Build sketch (for the implementing session)

Platform tool schemas per connected platform (the read tools already exist
in `platform_tools.py`); `lane_runner` allowlist amendment behind the
transport-enforced flag; credential resolution through
`resolve_platform_credential` with the turn principal; refusal copy for the
not-connected case; the detail page's "Agents" capability fact gains a
"Chat" row once live. Gates: drive a turn with the flag off (nothing
reachable), with the flag on as a connected member (reach works), as a
member without the connection (honest refusal), and as the steward (still
nothing).
