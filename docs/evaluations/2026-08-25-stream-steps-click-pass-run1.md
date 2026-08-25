# Stream steps click-pass — run 1 (2026-08-25)

**Surface**: the lane transcript's stepped streaming thread (`4e9df71`).
**Principal**: OWNER `kvkthecreator@yarnnn.com` (kvk-yarnnn RIG, ws bf5b25a9) —
a disposable rig, so the turns' reads ran for real against real substrate.
**Method**: playbook-conform — magic-link via
`scripts.operator.browser_login_link`, own isolated Chrome profile on port 9333
driven over CDP.
**Deploy asserted before concluding anything**: live API deploy `dfbe761`
(dep-da6jhf0u01pc73d7g0s0, status `live`) — CONTAINS `4e9df71`. Reached the real
app, not a bot-challenge page.

## Scope + non-coverage (declared)

COVERED: the streaming thread in the `/chat` housing — row accrual, verb+subject
composition, spinner placement, survival past the first token, settled handoff.

NOT COVERED, and not claimed:
- The other three `LanePanel` housings (Studio, Researcher's Desk, Text editor).
  Same component and same props shape, but not driven here.
- A **reach-bearing turn** (the 9 ADR-585 `platform_*` labels). No connector
  bound on the rig; the labels are gate-covered only.
- `GenerateImage`, `MoveFile`, `DeleteFile`, `Restore`, folder verbs — the rig
  lane's model reported no delete primitive on its surface, and the other
  producing verbs were not exercised.

## Steps + observations

| # | Step | Expected | Observed | Verdict |
|---|---|---|---|---|
| 1 | Send a 3-tool turn (list + read + search) | rows accrue in order | 3 rows, in the asked order | PASS |
| 2 | Verb + subject composition | subject named, not the bare verb | `Listing operation/` · `Reading operation/routing-click-pass.md` · `Searching your workspace for click-pass` | PASS |
| 3 | Workspace vocabulary | "your workspace", never "your computer" | `Searching your workspace for …` | PASS |
| 4 | Spinner placement | last row spins, earlier ones check | 3 steps, `spin=1`; screenshot shows 2 checks + 1 spinner | PASS |
| 5 | **Survives the first token** (the gating defect) | steps stay after narration starts | `t+10.8s working=false steps=3` — steps present with the working-bubble gone | PASS |
| 6 | Settled handoff | thread clears; footer states past tense | `steps=0`; footer `listed files · read a file · searched your workspace` | PASS |
| 7 | No verb duplication | bubble names WHO only | `Claude Sonnet 5 is working…` beneath the thread | PASS |
| 8 | Console clean | no errors from this surface | one 404, `GET /api/workspace/file?path=/workspace/persona/IDENTITY.md` — PRE-EXISTING, different subsystem, reproduced on a clean reload with no turn running | PASS (unrelated) |

Screenshot (mid-stream, 2 settled + 1 in flight):
`scratchpad/steps-live.png` — not committed (transient rig state).

Timing trace, turn 1:
```
t+1.2s  spin=0 working=true  steps=0     ← bubble before the first tool
t+8.4s  spin=1 working=true  steps=3     ← thread built, last row in flight
t+10.8s spin=1 working=false steps=3     ← SURVIVES the first token
t+12.0s spin=0 working=false steps=0     ← settled; footer takes over
```

## Notes for a future run

- **The MCP browser tools bind to one shared profile.** A concurrent session held
  it (`--remote-debugging-pipe`, unattachable). Launching an own Chrome on a
  separate `--user-data-dir` + `--remote-debugging-port` and driving it over raw
  CDP is the non-destructive path; killing the other browser would have broken a
  live click-pass mid-run.
- **`browser_login_link` loads `.env.alpha-ops` FIRST and its service key is
  STALE** (401 `Unregistered API key`). `api/.env`'s key returns 200. Overriding
  `SUPABASE_SERVICE_KEY` inline works; the stale file is worth fixing separately.
- Enter-to-send via synthetic `Input.dispatchKeyEvent` did NOT submit (focus).
  The `aria-label="Send"` button is the reliable control — note there are two
  send controls; the lane composer's is the enabled one.
