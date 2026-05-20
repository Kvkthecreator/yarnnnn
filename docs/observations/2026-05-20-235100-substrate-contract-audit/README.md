# Substrate contract audit — Step A + B

**Hat**: External Developer (Hat B). Discourse-driven audit; no system canon edits in this folder.
**Time**: 2026-05-20T23:51Z.
**Trigger**: kvk-vs-alpha-trader-2 cadence-authoring asymmetry observed on first natural Reviewer wake post-Fix-1A.

## One-line verdict

18 operator-relevant substrate files walked across four axes (authorship layer × document purpose × contract strength × prompt-text location). Step B class observation: **`_preferences.yaml` is the only file whose contract names a specific Reviewer ACTION but enforces that action through verbiage strength alone — and the verbiage is weaker than peer Reviewer-judgment-driven contracts (principles.md self-amendment, standing_intent.md every-cycle update).**

This is a one-gap finding, not a class gap. Audit ruled out the wider thesis of "multiple weak contracts producing a class problem." Three fix candidates (text tightening / structural gate / wait-and-observe) outlined in findings.md.

## Recommendation

R1: don't pre-fix. Wait for the second natural fire (kvk 2026-05-21T13:45Z) + yarnnn-author cadence-authoring observation 2026-05-21T05:00Z to confirm whether the asymmetry persists. Then decide.

R2: capture the four-axis audit table as reusable operator-side reference for reasoning about future operator-declaration substrate files.

R3: include yarnnn-author cadence-authoring observation as a third data point in the next cycle.

See `findings.md` for the full per-file audit + class observations + cross-references.

## Files

- `README.md` — this file
- `findings.md` — Step A walk (18 files × 4 axes) + Step B class observations + 4 candidate insights + recommendation
