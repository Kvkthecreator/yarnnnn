# ADR-584 — The connector can name where it is standing

**Status**: Ratified
**Date**: 2026-08-19
**Supersedes**: nothing. Discharges ADR-373 D6's residual and the SESSION-HANDOFF
Part B owed item #4 ("the connector is still not TOLD which workspace it is in").
**Related**: ADR-373 D6 (the client is stamped with a workspace) · ADR-573 (the
operator picks that workspace at consent) · ADR-563 (scopes) · ADR-533 D6 (what
does NOT port to the external surface) · ADR-512 D5 (the reference grammar).

---

## 1. The finding

A connected external principal — Claude, ChatGPT, any MCP host — **cannot learn
which workspace it is bound to.** Probed from a live claude.ai connection
(2026-08-19) and confirmed against the source:

- The workspace exists server-side as a bare UUID on `AuthenticatedClient.workspace_id`
  (`mcp_server/auth.py`), used purely as a query filter and discarded before every
  response.
- All eight `compose_*` builders in `services/mcp_composition.py` return file-level
  data only. `compose_list` returns `{success, reference, path, files, count,
  truncated, explanation}`; not one builder carries a workspace key.
- The `workspaces` row is **never fetched on the MCP request path**. The name is read
  exactly once — for the operator's browser consent screen (`routes/mcp.py`) — and
  never crosses the MCP boundary.
- No `whoami` verb, no identity resource. The four resources are UI widget bundles.
- `instructions` is composed at **import time**, before any request exists, so it
  structurally cannot carry per-connection identity.

Every path is rooted at a generic `/workspace/…` and every handle is
`yarnnn://workspace/{path}`. **The grammar has no workspace slot** (ADR-512 D5), so
even a pasted reference cannot disambiguate.

## 2. Why this is a defect and not a missing nicety

ADR-373 D6 exists because a member working in a workspace they do not own had every
connector write land in their **owner** workspace instead — "succeeding, returning a
revision id, and being invisible in the surface they were looking at. An incorrect
success with no error anywhere" (`auth.py:147-152`).

D6 fixed the *routing*. It did not fix the *observability*, and one branch of the
resolver still reaches the same end state by design:

> ⚠️ The one asymmetry with the browser: an UNREACHABLE requested workspace 403s at
> the JWT door, but here it degrades to the default rather than failing the tool call.
> — `resolve_mcp_workspace`, `auth.py:204-209`

**That degrade is correct and this ADR keeps it.** The operator is not present to
re-authorize mid-session; a connector that silently stops working is worse than one
that falls back to substrate it can always reach. The reach loss is still enforced —
the unreachable workspace is never returned.

What is *not* acceptable is that the degrade is **unobservable**. When it fires:

- the model is holding a workspace the operator did not choose,
- every read and write is correct, attributed, and lands *somewhere real*,
- and **no signal exists anywhere in the response** that the chosen binding was not honoured.

This is the class the memory names as the expensive one: a `200` with plausible
content. Sentry cannot see it, gates cannot see it, and the model — the one actor
positioned to say "wait, you asked me to file that in the team workspace" — is the
one actor kept ignorant.

**The identity gap and the silent degrade are one defect.** Naming the workspace is
what converts the fallback from silent to stated. That is why this ADR decides both.

## 3. D1 — `whoami`: a tenth verb, not an envelope key

**Decision: the connector learns where it stands by calling a verb.**

Rejected: **a `workspace` key on every response envelope.** It self-heals without the
model suspecting anything, which is genuinely its strongest property. But:

- It taxes all eight builders and every future one — an eighth-plus-forever edit to
  add a field that answers a question asked once per session.
- It duplicates a constant string into every page of a 283-file listing.
- It puts identity in the *return* of verbs whose subject is a file, conflating "what
  did I just do" with "where am I" — the same conflation ADR-563 unpicked for scopes
  (identity answers *who*, scopes answer *what*) and ADR-573 for binding (the binding
  answers *where*). Three questions, three answers. The envelope would re-merge one.

Rejected: **per-verb `workspace` argument.** Already rejected in ADR-573 §2 and that
rejection holds: nine signatures change, **the model becomes the chooser** (a wrong
guess writes to the wrong commons with full attribution), and the reference grammar
has no workspace slot. Recorded here so it is not re-discovered as novel.

Rejected: **an identity MCP resource.** The prior lane's note ("per-connection identity
would have to be a resource, never the instructions") correctly ruled out instructions
but reached for the wrong replacement. Resources are host-fetched artifacts, not
per-request calls; our four are static bundles read from disk. Hosts vary in whether
they surface resources to the model at all, and a resource read does not route through
`resolve_request_client`, so it would need its own identity and scope path. **A verb
rides machinery that already exists.**

So: **`whoami`**.

```
whoami() → {
  success, workspace, workspace_id, workspace_named,
  binding, you, client, scopes, capabilities, file_count, explanation
}
```

- `workspace` — the operator's chosen name, via `display_workspace_name`, which
  returns `None` while the row still wears the mint default. An unnamed workspace
  reports `workspace: null` + `workspace_named: false` and is described by its
  address, never by a leaked `"My Workspace"` (a string that is not "my" to the
  reader — the rule the helper already enforces on invite and share landings).
- `binding` — **the observability half.** `"chosen"` when the token's stamped
  workspace was honoured; `"default"` when no stamp existed (every pre-573 token);
  `"fallback"` when a stamp existed and was unreachable, i.e. the degrade fired.
- `you` / `client` — the attribution the writes will carry (`yarnnn:mcp:<client>`),
  so the model can state who the signature will name before it signs.
- `scopes` / `capabilities` — the verbs this token may actually use, from the ADR-563
  tiers. A model that knows it cannot `share` stops offering to.

**`whoami` requires `files:read`.** It is a pure read, and it must be the *weakest*
verb — a token that can do anything at all can ask where it is.

### Why a verb is the future-proof shape

The envelope answers one question forever. A verb is where **every** "what is my
situation" question lands as the surface grows: which workspace, what may I do, who
will my writes be signed as, was my binding honoured. All four are already answered
above, in one round, and none of them required touching a file verb. That is the test
this ADR set for itself — *is this the optimal shape for the whole tool set, or only
for the question asked today?*

The roster is DATA (`_INTEROP_VERBS`) and the prose is DERIVED, so `whoami` announces
itself in `instructions` by construction — no sentence to hand-edit, no count to drift.
The existing `test_adr533_participant_contract.py` gate asserts roster ≡ registered
`@mcp.tool` set, so the tenth verb cannot ship announced-but-absent.

## 4. D2 — the fallback becomes loud where it can be heard

**Decision: `resolve_mcp_workspace` keeps degrading, and starts reporting.**

The resolver returns the same value it always did. What changes is that the *reason*
survives the call instead of being written only to a log nobody reads mid-session:

- A new `resolve_mcp_workspace_detail(user_id, bound) -> (workspace_id, binding)`
  returns the resolution **and** how it was reached.
- `resolve_mcp_workspace` stays as-is — same name, same signature, same return — a
  thin wrapper over the detail form. **~90 construction sites do not change.** (The
  prior lane measured that exposure and dropped a threading cleanup for exactly this
  reason; this ADR does not re-incur it.)
- `whoami` reports `binding`, so the degrade is stateable in the room where it matters.
- The `logger.warning` stays. Logs are for us; the verb is for the model.

**This is deliberately not an error.** The operator is absent; failing the call helps
nobody. The fix for an unobservable-but-correct outcome is to make it observable, not
to make it fatal — the ADR-572 D18 shape (a snapshot's defect is *silence*, so state
the freeze in the document rather than refusing to write one).

## 5. D3 — the name is an address, not intent

ADR-533 D6 refuses to port the workspace MANDATE to a third-party host: the commons
contract is *how the workspace works* (kernel-universal, portable); the mandate is
*what this workspace is for* (workspace-specific intent, stays home).

**A workspace's name sits on the contract side of that line.** It is an address — the
label that distinguishes two commons a principal can reach. It is not a statement of
purpose, and it carries no strategy, no content, no mandate. Three checks:

1. **The operator has already disclosed it to this exact client.** ADR-563's consent
   screen prints the workspace name, and ADR-573 makes choosing it the point of the
   screen. A binding the operator made by name, reported back by name, exports nothing
   the approval did not already contain.
2. **It leaves once per session on request, not on every connection.** D6's objection
   is 40 lines of intent entering a foreign context window on every connect, for a
   benefit no verb requires. This is one string, pulled by a verb, for a benefit the
   binding itself requires.
3. **An unnamed workspace stays unnamed.** `display_workspace_name` returns `None` for
   the mint default, so we never leak a placeholder as if it were a choice.

D6's boundary is **unchanged and re-affirmed**: the MANDATE does not port, lane posture
overlays do not port, Altitude 1 does not port. This ADR moves the address, and stops.

## 6. What this does not do

- **No new schema.** `workspaces(id, name, …)` already holds everything; there is no
  `slug` column and this ADR does not add one (`name` and `id` are the whole vocabulary).
- **No change to the reference grammar.** `yarnnn://workspace/{path}` is untouched.
  Adding a workspace segment would be a breaking change to every handle ever pasted,
  to answer a question one verb answers.
- **No change to routing, reach, or scope enforcement.** Reads and writes land exactly
  where they landed before this ADR.

## 7. Gate

`api/test_adr584_connector_names_its_workspace.py` (py3.11 — anything importing
`mcp_server/*` needs `/tmp/mcpenv`; the API venv is 3.9 and dies at import on a
`str | None` default annotation).

It asserts: `whoami` is in the roster and registered; it is scoped `files:read` and
routes through `resolve_request_client(verb=…)`; the three `binding` values are each
reachable by **driving the real resolver** with a stubbed reach function (chosen /
default / fallback), not by reading the source; the mint-default name degrades to
`null` with `workspace_named: false`; `resolve_mcp_workspace` still returns a bare
id for its ~90 existing callers; and no `compose_*` builder gained a workspace key
(the envelope decision, enforced rather than remembered).
