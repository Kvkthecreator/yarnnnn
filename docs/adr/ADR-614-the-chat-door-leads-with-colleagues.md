# ADR-614: The chat door leads with colleagues — and the cast stays the one authority

**Status**: Ratified + Implemented 2026-08-27 (operator ruling: *"i want us to create new chat Agents here is first class (preferred priority) in the UI UX, with engines being secondary … and thus yes, the existing chat room model is the right one"*).

**Amends**: [ADR-558](ADR-558-chat-is-the-engine-surface-agents-are-personified.md) **D1** — the chat door's *centring* is reversed. ADR-558 **D3 is UNTOUCHED and is what this ADR's gate now defends**: the cast remains the single authority on who replies, and no birth-persona scalar is written.

**Preserves** (load-bearing, untouched): [ADR-495](ADR-495-the-conversation-one-object-one-cast.md) (one Conversation object, one species-blind cast), [ADR-562](ADR-562-an-apps-ai-configuration-is-declared-where-the-app-lives.md) D3 (a BOUND lane's resident is its app's declaration, never the client's), [ADR-596](ADR-596-the-agent-is-a-being.md) D1 (authority/clock/judgment never live on a being), [ADR-460](ADR-460-agents-one-concept-independent-facts-one-gate.md) D4 (the engine rides behind the name).

---

## 1. Context — the frame that was missing

ADR-558 separated three acts that one modal had fused, and that separation was right. What it also decided — almost incidentally — was **which act leads at the chat door**, and it chose the engine.

The operator's challenge, returning to this door months later, was not that the separation was wrong. It was that the *ordering* was:

> *"i want us to create new chat Agents here is first class (preferred priority) in the UI UX, with engines being secondary."*

The reasoning that settles it is ADR-460 D4's, which ADR-558 preserved everywhere except here: **a member starting work thinks "I want to write this deck", not "I want Claude Sonnet 5".** The colleague is the intent; the engine is the implementation detail behind them. ADR-558 D1's own words concede the point — *"a member who never thinks about engines never has to"* — while building a door whose first and only question is which engine.

### The conceptual question underneath, answered before building

The session first asked whether an agent can be a *permanent persona* at all, given ADR-596 D1's cliff (authority never lives on a being). Resolving that was the prerequisite, and it produced a three-layer partition worth recording, because the ADRs had it implicitly and nowhere stated:

| Layer | Lives where | Example |
|---|---|---|
| **Kernel identity** — who this being IS | `agents_registry.AGENTS` (kernel code) | name · character · engine |
| **The relationship** — how THIS MEMBER works with them | `member_state`, keyed by slug | the ADR-612 connector opt-in |
| **Authority** — what may bind | grants · declarations · gates | never on a being (ADR-596 D1) |

Layer 2 already exists and is already legitimate: ADR-612's `agent_connectors` is per-member, per-being, and outlives every conversation. **A standing relationship with a colleague is not authority on that colleague**, which is why it can live in `member_state` without touching the cliff. Naming a colleague at a door is the same kind of fact.

Per-agent MEMORY — a being that accumulates your corrections across conversations — is a **fourth** thing, explicitly deferred by the operator and NOT decided here.

## 2. D1 — The door asks WHO first, and WHICH ENGINE second

`NewChatModal` lists beings as the primary answer and folds engines behind one click ("Or start with an engine"). Both remain one gesture; only the order changed.

Two intents, both still served, neither handed the other's abstraction — ADR-558's insight, with the priority the operator ruled:

- *"I want to write this deck"* → a colleague. The engine is never shown; printing it would hand back the spec sheet ADR-460 removed.
- *"I want to use GPT-5"* → an engine, one click away, with its provider mark and its ADR-559 availability reason.

**The sticky mark is ONE key** (`yarnnn.chat.lastStart`), holding a colleague slug or an engine id. Two keys would let the door claim two "last used" marks for one question.

**No commentary.** The restated instructions ("Add people or agents once the chat is open", "Manage your agents →") are deleted. The door states choices; it does not narrate the product.

## 3. D2 — Naming a colleague SEEDS THE CAST; it is not a birth-persona

This is the load-bearing half, and it is what keeps ADR-558 D3 intact rather than reversed.

`POST /lanes { agent }` on an **unbound** lane:
- resolves the being server-side and takes **its** engine (the client never names a model on the member's behalf);
- writes **a cast row** — `add_participant(member_kind="agent", agent_slug=…)`;
- writes **nothing** to `lane_meta`.

That row is byte-identical to the one CastBar would write a second later. Nothing downstream can distinguish a conversation started from a name from one started from an engine and joined after — which is precisely the point: **presence is a cast row, at every door.**

What ADR-558 D3 actually forbade was a *second authority* on who replies. The scalar it deleted (`lane_meta["agent"]`) produced a live bug it records verbatim: an Agent added via CastBar never replied, because the cast said yes and the scalar said nobody. **This ADR adds no second authority.** `select_responder` still reads the cast, exclusively.

The gate drives this rather than asserting it: it executes `create_lane`, inspects the participant writes AND the persisted `lane_meta`, and fails if an `agent` key appears.

## 4. D3 — `app` still requires a binding, and a bound lane still refuses a client colleague

Two refusals survive, with their reasons re-stated because one of them changed:

- **`app` without a binding → 422.** `register_app` answers "who works this desk", which is meaningless with no desk. The refusal now names the *binding*, not a banned persona.
- **`agent` WITH a binding → 422.** A bound lane's colleague is its app's declaration (ADR-562 D3). Two authorities in one request is a caller bug.

`extra="forbid"` is unchanged: an unknown field is refused, never silently dropped.

## 5. D4 — The being glyph gets one home

`ICONS` + `BeingIcon` were local to `AgentsSurface.tsx`. The door now lists beings too, and a second copy of that map is the exact drift its own comment warned about — Supervisor rendered the fallback `Bot` for a day because the registry declared `clipboard-list` and the map had three keys.

Extracted to `web/components/agents/BeingIcon.tsx`, one exported `BEING_ICONS`. `test_agent_registry.py`'s two icon checks (missing key / orphan key) re-point at that module.

## 6. Consequences

**Good.** The member's first question is answered first. A colleague-started conversation is structurally an ordinary conversation, so mixed rooms, `@mention`, adding a teammate, and the visibility window all work unchanged — nothing special-cases how the conversation began. One home for the glyph map.

**Cost.** `NewChatModal` is rewritten. `readLastEngine`/`rememberEngine` are renamed (no other callers). Three gates move with the decision: `test_adr558_chat_is_engines` (the assertions pinning engine-first were describing a UI ordering, not an invariant), `test_adr562_app_owned_config` (now asserts the invariant — a bound lane refuses a client colleague — instead of the field's absence, which was only ever a proxy), `test_agent_registry` (icon map re-pointed).

**The trade being accepted.** A conversation started from a colleague and one started from an engine are the same object with the same cast; only the door differs. That is deliberate — it is what makes this an ordering change rather than a second conversation model.

**Not decided here.** Per-agent memory (a being that accumulates across conversations) — deferred by the operator. A per-agent conversation *list* on `/agents` — the section deleted at `32cd8b9` was a dead list, and whether a resumable one earns its place is its own question.

---

**One line**: the door asks who you want to work with before it asks what engine to run — and picking a colleague seeds the cast, so ADR-558 D3's single authority on who replies is preserved exactly, not traded away for the reordering.
