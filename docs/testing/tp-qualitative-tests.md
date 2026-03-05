# TP Qualitative Test Playbook

> Tests for the structural overhaul ([2026.03.05.1], [2026.03.05.3]).
> Run these in the browser at yarnnn.com. Log in as your test user.

---

## Pre-test: Baseline check

Before starting, confirm your test user has:
- At least one deliverable with a generated version (e.g., "Weekly Work Status" has v10)
- Empty `deliverable_instructions` and `deliverable_memory` on most deliverables

---

## Test 1: Version Visibility (scoped session)

**Go to:** `/deliverables` → click "Weekly Work Status"

**In the chat panel, ask:**
> "What did the last version look like?"

**Expected:** TP should answer using the version preview from its working memory (auto-injected) — NOT say "I don't have access to generated content" or try to use a tool that fails. It may also call `Read(ref="version:latest?deliverable_id=...")` for the full content.

**Pass if:** TP references specific content from the latest version.
**Fail if:** TP says it can't see versions, hallucinates content, or errors out.

---

## Test 2: Instruction Update (scoped session)

**Same deliverable page, send:**
> "Make it shorter. I only need the top 3 blockers and a one-line summary."

**Expected:** TP should:
1. Call `Edit(ref="deliverable:{id}", changes={deliverable_instructions: "..."})` with something reflecting "top 3 blockers, one-line summary"
2. Confirm the update briefly

**Pass if:** TP proactively updates `deliverable_instructions` via Edit tool call.
**Fail if:** TP just says "Got it, I'll remember that" without calling Edit, or asks "Would you like me to save this preference?"

---

## Test 3: Observation Append (scoped session)

**Same deliverable page, send:**
> "By the way, we just closed our seed round. That context matters for future reports."

**Expected:** TP should:
1. Call `Edit(ref="deliverable:{id}", changes={append_observation: {note: "...seed round closed..."}})`
2. Acknowledge briefly ("Noted." or similar)

**Pass if:** TP appends an observation via the Edit primitive.
**Fail if:** TP just says "congratulations" without recording anything, or tries to write to user memory.

---

## Test 4: One-off vs Persistent (scoped session)

**Same deliverable page, send:**
> "Just this time, can you also include calendar events in the next version?"

**Expected:** TP should NOT update instructions (this is a one-off request per the "When NOT to act" guidance). It should acknowledge the request conversationally but not call Edit.

**Pass if:** TP responds conversationally without modifying instructions.
**Fail if:** TP calls Edit to update deliverable_instructions with calendar info.

---

## Test 5: General Session — Hands-Off

**Go to:** the main chat (not scoped to any deliverable — e.g., `/chat` or the default TP)

**Send:**
> "How are my deliverables doing?"

**Expected:** TP should `List(pattern="deliverable:*")` and give a summary. It should NOT browse into any deliverable's workspace to update instructions or append observations unprompted.

**Pass if:** TP lists deliverables and summarizes statuses.
**Fail if:** TP starts editing instructions or appending observations on any deliverable.

---

## Test 6: Headless Draft Quality (manual trigger)

**Prerequisite:** Test 2 should have set instructions on "Weekly Work Status."

**Trigger a generation** (either wait for schedule, or via admin trigger if available):
```
POST /admin/trigger-generation/{deliverable_id}
```
Or just wait for the next scheduled run.

**Check the generated version content.**

**Pass if:** The draft is shorter than previous versions and reflects "top 3 blockers + one-line summary" from the instructions set in Test 2.
**Fail if:** The draft ignores instructions and looks identical to previous versions.

---

## Test 7: Version Comparison (scoped session)

**Go to:** the deliverable page (after Test 6 has generated a new version)

**Send:**
> "Compare the latest version to the previous one. What changed?"

**Expected:** TP should use `Search(scope="version", deliverable_id="{id}")` or `Read(ref="version:*?deliverable_id={id}")` to fetch multiple versions and compare them.

**Pass if:** TP fetches and compares two versions, noting differences.
**Fail if:** TP says it can't access version history.

---

## Test 8: Goal Mode (scoped session)

**Go to:** any deliverable page.

**Send:**
> "Let's track a goal for this: ship the investor update by Friday. Milestones are draft, review with co-founder, and send."

**Expected:** TP should call:
```
Edit(ref="deliverable:{id}", changes={set_goal: {
  description: "Ship investor update by Friday",
  status: "in_progress",
  milestones: ["Draft", "Review with co-founder", "Send"]
}})
```

**Pass if:** TP sets the goal via Edit with correct structure.
**Fail if:** TP just acknowledges without calling set_goal.

---

## Verification

After running Tests 1-5 and 8, check the DB to confirm state was persisted:

```sql
SELECT title, deliverable_instructions, deliverable_memory
FROM deliverables
WHERE user_id = '<your-user-id>'
  AND title = 'Weekly Work Status';
```

- `deliverable_instructions` should contain the preference from Test 2
- `deliverable_memory.observations` should have the seed round note from Test 3
- `deliverable_memory.goal` should have the investor update goal from Test 8

---

## Results Template

| Test | Result | Notes |
|------|--------|-------|
| 1: Version Visibility | | |
| 2: Instruction Update | | |
| 3: Observation Append | | |
| 4: One-off vs Persistent | | |
| 5: General Session Hands-Off | | |
| 6: Headless Draft Quality | | |
| 7: Version Comparison | | |
| 8: Goal Mode | | |
