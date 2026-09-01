# ADR-628: The outbound disposition — a post leaves the workspace

**Status**: Ratified 2026-09-01 (design; operator-aligned). **Phase (a) BUILT
same day** (amendment below): WordPress is the first tenant. Phase (b)
automation stays gated on phase (a)'s track record.

## Amendment — 2026-09-01: phase (a) built, WordPress the first tenant

Operator ruling (same day): lock WordPress. The reasoning, recorded: it is the
only candidate high on all four axes the objective needs — layman-attractive
(largest installed base of people who *have* a blog), layman-connectable
(WordPress.com's OAuth2 flow is the same one-click connector gesture as
Slack/Notion), long-standing (a decade-stable REST write contract, backed by
open source — the anti-Medium property), and wide (one client covers
wordpress.com + Jetpack-connected sites). Substack is the more attractive
*brand* and has **no write API** (its new Publisher API is read/analytics —
noted as a strings opportunity, not a publish target); Ghost is the better API
with the smaller base (second connector); Dev.to/Hashnode are the wrong
audience.

**The three-state connect story** (a member does NOT need a pre-existing
site — but WordPress always publishes TO a site):

1. has a site → OAuth connect, pick it at publish time, done;
2. has a WordPress.com login, no site → a free `name.wordpress.com` site is
   ~2 clicks on their side, once — after which they never manage anything;
3. has nothing → the authorize page doubles as signup, which lands them in
   state 2.

The fully-invisible upgrade (yarnnn mints the site during connect via the
undocumented `sites/new`) is historically whitelisted to Automattic's own
clients — confirm with Automattic before designing around it; do not promise
it. And the refusal that pairs with this: **yarnnn never hosts blogs**
(`yarnnn.com/@user` is owning a publishing platform — the ADR-417 class);
the state-zero fallback is the already-shipped Share link.

**What the build found**: `integrations/exporters/` (the ADR-028
DestinationExporter ABC + Slack/Notion/Download exporters) was a FOSSIL —
its one `.deliver()` caller was deleted 2026-08-26 with a comment claiming
"live delivery paths" that do not exist, and `connector_does` was citing it
to print member-facing copy promising an export capability no route could
perform. Deleted whole; the copy now tells the truth. The phase (a) seam is
**`services/publish.py`** — new, narrow, ADR-628-shaped — with
`integrations/core/wordpress_client.py` beneath it and
`POST /api/publish/wordpress` as the one member-clicked door. The receipt is
a `_publish.yaml` sidecar beside the post (machine format per ADR-254),
written through `write_revision` as the member's own act.

**Builds on** `docs/architecture/intake-pipeline.md` §5 (a reach proposal must
declare its disposition in its first paragraph) · ADR-577 (the credential
claim: an agent caller is refused) · ADR-594 D2 (reach with a receipt: the
seam's caller is a string's run) · ADR-591 (no clock on a connection) ·
ADR-460 D3.a (consequential external authority is unrepresentable on a being).

## The disposition

Canon recognizes two dispositions of platform reach, both **inward**:

| Disposition | Shape | Canon |
|---|---|---|
| INTAKE | durable, inbound — observations land at the fixed lane | intake-pipeline |
| TURN REACH | transient, inbound — a turn reads, nothing lands | ADR-615 |
| **OUTBOUND** | **content leaves the workspace for an external platform** | **this ADR** |

Outbound is not a mirror of intake. An intake defect is recoverable (a bad
observation is a revision; delete it). An outbound act is **irrevocable in the
world** — a published post is cached, syndicated, read. That asymmetry drives
every decision below.

## Decisions

### D1 — The connection stays a rail; publishing is a CONSUMER's act

ADR-582's sentence holds unchanged: a connection is consent + credential +
aperture. A **publish target** is a connection whose aperture includes an
outbound verb. No per-connection settings (ADR-594 D1 stands) — *what* gets
published and *when* lives at the consumer (a declaration, or a member's
click), never on the connection row.

### D2 — Phase (a): the member carries the post across

v1 publish is a **member-clicked act on a workspace artifact**: the member
stands on a `post`, the surface offers "Publish to {target}", the API
performs the platform call with the member's own credential
(`platform_credentials.py`, the ONE path — the caller is the member, so
ADR-577's agent-refusal is never in question), and the receipt lands as an
attributed revision on the post (frontmatter or sidecar: platform, URL,
timestamp). The autonomy cliff is not approached: no agent decides to
publish, so nothing needs a dial.

### D3 — Phase (b): automation follows the capture precedent exactly

When a standing declaration is trusted to publish without a click, the
mechanism is ADR-594 D2's shape, outbound: the seam's caller is **a string's
run**, the identity is a **narrow non-agent system identity**
(`system:publish-{platform}` — the ADR-626 D4.b finding is the law here:
every live unattended lane grew its OWN narrow auth, and three lanes voting
the same way is the design), the act is **balance-checked before the call**
(ADR-618), **receipted** (execution event + the D2 revision), and
**bounded** (one post per run; no fan-out). The declaration's contract must
name the publish explicitly — a declaration that says "keep the drafts
folder true" never publishes.

Phase (b) does not begin until phase (a) has produced real receipts, and it
begins with an ADR amendment recording that evidence.

### D4 — Platform-generic, and the first paragraph rule

The seam is named by DISPOSITION, never by tenant (the intake-pipeline rule:
never name a lane after its first consumer). Candidate first targets, with
the 2026 reality stated: **Medium's public API stopped issuing integration
tokens years ago and is effectively closed** — it is not a viable first
target despite being the category's name. Viable: **Ghost** (Admin API,
first-class), **Dev.to/Forem**, **Hashnode** (GraphQL), **WordPress REST**.
The first target is chosen when phase (a) is built, against a real account
the operator holds; this ADR deliberately does not pick.

### D5 — What is refused

- **No bucket, no bypass**: the publish call goes through the platform's
  authenticated API from the yarnnn API service — never a pre-signed upload,
  never a client-side post (the ADR-622 shape: the control channel is ours).
- **No agent-held credential, ever** — phase (b)'s identity is non-agent
  system machinery; ADR-577's guard is untouched.
- **No publish from chat**: a turn that could publish is a turn that could be
  prompted into publishing. Phase (a) is a surface act; phase (b) is a
  declaration's run. The open conversational surface never carries the verb.

## Consequences

- ADR-627's Blogger ships with zero outbound reach and loses nothing by it.
- `connectors.md` gains the third disposition row when phase (a) builds (the
  doc change rides the build commit, not this one — a doc describing an
  unbuilt seam as live is the ADR-573 "ratified ≠ implemented" trap).
- The retention/pricing questions (does a publish receipt carry a disposition
  owed?) are deferred to phase (a) with the build.

## Gate

`test_adr628_outbound_publish.py` (arrived with phase (a), per the original
plan). Its first assertion is D5's: no module under `api/` performs an
outbound platform write outside the `services/publish.py` seam — which now
also pins the exporter fossil's grave.
