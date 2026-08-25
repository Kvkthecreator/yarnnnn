# ADR-605 mentions click-pass — run 1 (2026-08-25, Claude-driven, production)

**Surface**: the mention wire (ADR-605) end to end, two principals, prod.
**Principals**: MEMBER `seulkim88@gmail.com` (2be30ac5…) → OWNER
`kvkthecreator@gmail.com` (2abf3f96…), both declared test accounts
(OPERATOR-PACKET roster), workspace `yarnnn workspace` (d5b9029b…).
**Method**: playbook-conform — magic-link login via
`scripts.operator.browser_login_link`, **one isolated Chrome context per
principal** (`isolatedContext` on new_page — simultaneous, no cookie
overwrite), every step DOM half + substrate half (PostgREST service-key
reads; no DB writes outside the surface's own acts).
**Deploys asserted first**: API `8c10891` live on Render (dep-da6e5a5b);
FE proven live behaviorally (the @-palette showed the new person-row title).

## Steps

| # | Step | DOM half | Substrate half | Verdict |
|---|---|---|---|---|
| 1 | Member switches to the shared workspace | user-menu workspace list → "yarnnn workspace Member"; roster shows both humans | — | PASS |
| 2 | `@` in the DM composer | listbox "Address someone in this conversation": **KVKtheCreator selectable** (title: "Mentioning a person flags it for them…"); pick writes `@KVKtheCreator` | — | PASS |
| 3 | Send the mention | message renders; `@KVKtheCreator` renders as a **chip** (styled span), rest plain text | `session_messages` seq 22: `metadata.mentions=['2abf3f96…']`, author `2be30ac5…` — the write-time stamp, in prod | PASS |
| 4 | Never-ambient in a human DM | no agent reply fired (direct branch); stamp+notify ran before the direct return | no assistant row appended | PASS |
| 5 | Owner's bell | badge **1**; TO DO leads: "**Seul Kim** mentioned you · ‹conv› — @KVKtheCreator can you review the Q3 draft…4m ago" (name resolved, never a UUID) | derivation only — no inbap rows (table checked empty of in-app anything) | PASS |
| 6 | Click the bell row | lands in `/chat?chat.lane=1ee9f2eb…`, the exact conversation, message visible | — | PASS |
| 7 | Two-facts rule | opening the bell cleared the **badge**; the row **stayed listed** (membership ≠ seen) | — | PASS |
| 8 | Workbench queue | /notifications → To do → **MENTIONS** block: author + conversation + excerpt + "Open conversation" + "Done" | — | PASS |
| 9 | Done | block clears immediately | `member_state['mention_resolutions']` = `{1ee9f2eb…: 22}` per (d5b9029b, 2abf3f96) — monotonic cursor stored | PASS |
| 10 | Settings pane | Mentions dial live: exactly **"Every mention" / "Never"**, value `all`; `runs` still prints its refusal; no "Urgent only" on mentions | registry served (`/api/notification-kinds`: mentions `email_default:"all"`, note null) | PASS |
| 11 | Email leg, first attempt | — | **FAIL → FIXED**: `[NOTIFICATION] No email for user 2abf3f96…` in Render logs; no transport row. Root cause: `notify_mentioned` was handed the AUTHOR's user-scoped client; `auth.admin.get_user_by_id` needs the SERVICE key (and the recipient's prefs/transport rows are invisible to the author's RLS view — suppression that never suppresses). Fix `ee6d5e1`: the seam resolves its own service client (the `conversation_cast._svc` rule); gate 38/38 + new AST check falsified against the exact pre-fix call shape | see run 2 below |
| 12 | Email leg, post-fix re-drive | second mention sent from the member UI after deploy `92d37b0` (carries `ee6d5e1`) went live | `session_messages` seq 23 stamped; `notifications` row: user `2abf3f96…`, `source_type='mention'`, **`status='sent'`**, workspace-stamped, `06:35:39Z` — **the outbound seam's first production send ever** (the table had 0 rows in its life) | PASS |

## Findings

1. **F1 (fixed in-run, `ee6d5e1`)** — the wrong-client defect above. The class
   is recorded: a consequence that acts on the RECIPIENT must not run on the
   AUTHOR's client; the seam now makes the wrong client inexpressible.
2. **F2 (minor, open)** — the mentioned viewer's OWN handle doesn't render as
   a chip in their transcript view: `mentionCandidates` excludes the viewer,
   so `knownHandles` lacks their handle — the one chip that means "this is
   about me" is the one that doesn't mark. FE-only, cosmetic; fix is to add
   the viewer's own handle to the known set (not to candidates).
3. Conversation display name in mention rows is the lane's stored name
   (here the DM is named `seulkim88@gmail.com`) — correct per the model,
   slightly odd for a DM viewed by its namesake's counterpart; a DM-aware
   label would derive the counterpart name. Cosmetic, noted only.

## Not covered

- **Suppression, live** — the third mention (which should NOT email inside
  the 60-min window) was typed but never landed: the Chrome DevTools MCP
  browser restarted mid-send and the isolated contexts (plus the single-use
  links) died with it. Declared NOT RUN, not inferred. The suppression
  branch is behaviorally gate-covered (`test_adr605_mentions_attention.py`:
  recent-row suppresses · empty sendable · unreadable ledger SUPPRESSES),
  and the same ledger query demonstrably executed in prod on the run-2 send
  path (it found no rows and correctly sent).
- @agent regression (turn-routing) — not re-driven here (costs a live model
  turn; the addressing ladder is unchanged and gate-covered). The DM direct
  branch proved never-ambient held around the new stamp code.
- The "add them?" offer on mentioning a non-participant — not built (ADR-605
  §5, deliberate).

## End state, deliberate

KVK's bell holds **one genuine unresolved mention** ("seulkim88: second
ping…", seq 23) and their inbox one mention email — left in place so the
operator experiences the shipped surface first-hand; replying in the DM or
pressing Done in the workbench discharges it. The seq-22 mention was
resolved during the pass (the Done receipt above).
