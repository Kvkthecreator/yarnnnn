# ADR-585: Turn Reach — the Member's Own Connections, Inside Their Own Turn

> **Status**: Ratified + Implemented DORMANT 2026-08-19. The operator
> confirmed the cut line in their own words the same day: *"a chat should
> use the user settings, and the agents principals follow the existing
> workspace settings discipline. thus, it's just following the same
> discipline applied. and the same goes for dedicated APPs with agents."*
> That framing makes this ADR the EXISTING scope taxonomy applied (ADR-407:
> verbs are user-scoped; ADR-425: the credential is the member's account
> object), not a new discipline. Built behind `TURN_REACH_ENABLED`
> (default OFF — the ADR-404 D2 pattern: built whole, lit deliberately);
> production behavior is unchanged until the flag flips.
> Gate: `api/test_adr585_turn_reach.py`.
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

## 4. As built (same day, dormant)

- **`services/turn_reach.py`** — the flag + the surface, DERIVED from the
  capability registry's read rosters (`read_slack` + `read_notion` +
  `read_github` → 9 read-only tools) and the provider rosters' own schemas.
  A write tool cannot drift in without editing the registry itself.
- **`lane_runner.turn_has_reach(app, artifact_path, derive_recipe)`** — the
  principal-presence fact, derived per turn from the turn's OWN shape: only
  the open chat turn (no app binding, no bound artifact, no derive recipe)
  carries reach. Both run variants and the frame prose derive it from the
  same arguments, so payload, allowlist, and prose cannot disagree (the
  ADR-467 D4 rule, held with the flag on or off).
- **Dispatch needed nothing new**: `execute_primitive` already routes
  platform reads to `handle_platform_tool`, whose ADR-577 chokepoint
  (`resolve_platform_credential` + `is_agent_caller`) resolves by the turn's
  member and refuses agent-shaped callers — the lane's `member:{user_id}`
  embodiment is a human's hands by construction. The not-connected case is
  the chokepoint's existing `credential_missing_error`.
- **The frame's connector edge** (ADR-535 D3) is now stated affirmatively in
  BOTH directions: without reach, "you CANNOT read through it"; with reach,
  the bound (member's own · read-only · transient · save-to-keep).
- **The detail page's capability facts** gain a `chat` row derived from the
  flag ("chat cannot reach platforms on this deployment" until it flips).
- **D5, the engine disclosure (2026-08-20)**: the second sentence of that
  same `chat` row — "What it reads goes to the engine you picked for that
  chat, the same as pasting it in." It lives on the connector page rather
  than the chat surface because the row is ALREADY flag-derived (a
  hand-kept sentence at the new-chat door could disagree with the
  capability it describes), and because a standing exposure fact belongs
  where the connection is granted, not repeated at every conversation
  until it stops being read. Gate §6, falsified against the pre-D5 string.
- Steward, app lanes, derive turns, wake paths: unchanged — no platform
  tool on any of their surfaces.
