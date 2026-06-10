# Playbook — author-compose-money-truth-remake

## Metadata

```json
{
  "scenario_slug": "author-compose-money-truth-remake",
  "scenario_description": "THE COMPOSITION THESIS (ADR-333). author-produce-corpus-piece proved the\nReviewer can AUTHOR flat prose to content.md. This scenario proves the next\nlayer: can the Reviewer author a piece with STRUCTURE NATIVE TO THE ACT \u2014\nemitting kind:-tagged section partials (comparison-table / mermaid / callout\nspine) where a section-kind carries the argument better than prose would,\nper the piece-composition spec (the alpha-author program's first PRODUCTION,\nnon-audit, spec)?\n\nTHE A/B CONTROL. The subject is a deliberate RE-MAKE of an existing strong\nFLAT post \u2014 `money-truth-as-a-file-not-a-dashboard` (content/posts/, 104-post\ncorpus, published 2026-04-07). That post has structure latent in its prose\nthe flat form hides:\n  - \"The Two Architectures\" (A dashboard vs B substrate, point by point)\n    \u2192 comparison-table\n  - \"predictable failure modes\" (3 named patterns: same-mistake repetition /\n    drift unnoticed / operator-mediated calibration) \u2192 status-matrix\n  - \"How Money-Truth Gets Computed\" (4-step deterministic pipeline:\n    fetch \u2192 compute \u2192 write \u2192 idempotency) \u2192 mermaid flow\n  - \"What this article answers (plain language)\" gloss \u2192 callout\nThe flat post is the control; the composed re-make is the treatment. The\nA/B is direct and clean (same argument, two forms).\n\nCRITERION (declared per docs/evaluations/README.md criterion-declaration\ndiscipline). Measured against:\n  - ADR-333 D5 (structure is native to authoring \u2014 the Reviewer emits\n    kind:-tagged sections as part of the single authoring act, no separate\n    enrich step) +\n  - piece-composition.md \u00a71 (the \"could this be a paragraph without loss?\"\n    gate \u2014 a section-kind earns its place only when it carries the argument\n    better than prose; richness = argument-fidelity-gain, NEVER asset count) +\n  - piece-composition.md \u00a72 palette ranking (comparison-table + mermaid +\n    callout spine; metric-cards/status-matrix/trend-chart only with real\n    substrate data; generated images Tier-3/exceptional, one max).\n\nPASS-BAR (substrate-receipt-backed, NOT narration). The pass is real\nworkspace_file_versions revisions, attributed reviewer:ai:*, at:\n  - /workspace/operation/authored/money-truth-remake/content.md (the prose), AND\n  - /workspace/operation/authored/money-truth-remake/{date}/sections/*.md\n    (\u22651 kind:-tagged section partial \u2014 the composition substrate), AND\n  - /workspace/operation/authored/money-truth-remake/{date}/sys_manifest.json\n    (the section\u2192kind map the composer reads).\nAn empty / narrate-only / flat-content.md-only turn is NOT a pass \u2014 the\nCOMPOSITION substrate (sections + sys_manifest) must exist on disk. Then the\nconsumption-pull surface (GET /api/authored/money-truth-remake/render) must\nreturn composed HTML (verified post-run, ADR-333 D6).\n\nANTI-GAMING (the criterion measures the opposite of asset-count by\nconstruction). A piece with one well-placed comparison-table + one mermaid\nscores HIGHER than one with five decorative charts. The \u00a71 gate is the\njudgment under test: does the Reviewer place kinds where they carry\nargument, and leave prose as prose where prose carries it? A composed piece\nthat fragments the em-dash-fluent connective voice into bullet-shards FAILS\nvoice-integrity even if every section is individually justified.\n",
  "persona": "yarnnn-author",
  "caller": "operator-proxy:scenario-runner:acting-as-yarnnn-author",
  "evaluations": [
    {
      "phase": "setup",
      "action": "write_substrate",
      "path": "/workspace/governance/_autonomy.yaml",
      "authored_by": "operator-proxy:scenario-runner:acting-as-yarnnn-author",
      "revision_id": "b357a022-8c64-4c29-aff9-bc9c0be31790"
    },
    {
      "phase": "setup",
      "action": "write_substrate_from_file",
      "path": "/workspace/operation/specs/piece-composition.md",
      "source": "/Users/macbook/yarnnn/docs/programs/alpha-author/reference-workspace/operation/specs/piece-composition.md",
      "authored_by": "system:bundle-fork",
      "revision_id": "1a3299c5-fcc4-4e46-8c27-0bae5ce82b4d"
    },
    {
      "phase": "setup",
      "action": "write_substrate_from_file",
      "path": "/workspace/operation/authored/money-truth-remake/source-flat.md",
      "source": "/Users/macbook/yarnnn/content/posts/money-truth-as-a-file-not-a-dashboard.md",
      "authored_by": "operator-proxy:scenario-runner:acting-as-yarnnn-author",
      "revision_id": "14ef0265-f219-437a-8e87-35ebb109d806"
    },
    {
      "phase": "turn",
      "turn_index": 0,
      "expect": [
        "reviewer_responded",
        "content_md_written",
        "sections_partials_written",
        "sys_manifest_written",
        "kinds_earn_their_place"
      ],
      "action": "send_message",
      "content": "Reviewer, I want you to re-make one of our strongest existing posts as a\n*composed* piece \u2014 structured, not flat. The source is our published post\n\"Money-Truth As A File, Not A Dashboard\" (the architecture argument: where\nyou put performance data \u2014 dashboard vs substrate file \u2014 determines whether\nautonomous AI can learn from outcomes). I've put the flat source in your\nworkspace at /workspace/operation/authored/money-truth-remake/source-flat.md\n\u2014 read it first; that's the prose you're re-making.\n\nThe flat version is strong but text-heavy \u2014 the structure the argument is\nalready reasoning in is hidden in the prose. Re-make it as a composed\narticle per the piece-composition spec at\n/workspace/operation/specs/piece-composition.md. Author the prose in our\nvoice (claim-first, em-dash-fluent, anti-slop floor), AND decide structure\nas you author: where a section-kind carries the argument better than prose,\nemit it as a kind:-tagged section. Apply the gate the spec names \u2014 \"could\nthis be a paragraph without loss?\" \u2014 per section. Don't decorate; place a\nkind only where it earns its place.\n\nThe source's latent structure is real: the \"two architectures\" passage is\na contrast (a comparison-table); the \"failure modes\" passage is a named-\npattern set (a status-matrix); the \"how money-truth gets computed\" passage\nis a 4-step pipeline (a mermaid flow); the plain-language gloss is a\ncallout. Use the spine the spec ranks (comparison-table + mermaid +\ncallout); reach for status-matrix only if the pattern set genuinely reads\nbetter as a matrix; no generated images (this argument is architectural,\nnot evocative).\n\nWrite:\n  - the prose to /workspace/operation/authored/money-truth-remake/content.md\n    (+ a profile.md with status: draft),\n  - the kind:-tagged section partials to\n    /workspace/operation/authored/money-truth-remake/{today}/sections/{n}-{slug}.md,\n  - the section\u2192kind map to\n    /workspace/operation/authored/money-truth-remake/{today}/sys_manifest.json\n    (surface_type: article; sections: {slug: {kind, title}}).\n\nAuthor and compose it now. The composition substrate (sections +\nsys_manifest) is the deliverable \u2014 not narration about it.\n",
      "response_text_preview": "Wrote to Reviewer substrate on its direction. path=/workspace/operation/authored/money-truth-remake/content.mdWrote to Reviewer substrate on its direction. path=/workspace/operation/authored/money-truth-remake/profile.mdExecuted `DispatchSpecialist` on Reviewer's direction. okWrote to Reviewer substrate on its direction. path=/workspace/operation/authored/money-truth-remake/2026-06-10/sections/1-architectures.mdWrote to Reviewer substrate on its direction. path=/workspace/operation/authored/mone",
      "reviewer_verdict_present": false
    },
    {
      "phase": "turn",
      "turn_index": 1,
      "expect": [
        "reviewer_responded",
        "names_kind_argument_fidelity_per_section",
        "names_a_passage_kept_as_prose_on_purpose"
      ],
      "action": "send_message",
      "content": "Now make your structural judgment legible. For each non-prose section you\ncomposed, name the kind and answer the gate explicitly: what argument does\nthis kind carry that prose could NOT carry as well? And name at least one\npassage you DELIBERATELY left as prose where a kind would have been\ndecoration \u2014 show me you applied the gate in both directions, not just\n\"add a table everywhere you can.\" If you placed a generated image, justify\nwhy a diagram-kind couldn't carry it (the spec caps images at one,\nexceptional).\n",
      "response_text_preview": "Wrote to Reviewer substrate on its direction. path=/workspace/persona/judgment_log.mdWrote to Reviewer substrate on its direction. path=/workspace/persona/judgment_log.mdWrote to Reviewer substrate on its direction. path=/workspace/persona/judgment_log.mdWrote to Reviewer substrate on its direction. path=/workspace/persona/judgment_log.mdWrote to Reviewer substrate on its direction. path=/workspace/persona/judgment_log.mdWrote to Reviewer substrate on its direction. path=/workspace/persona/judgm",
      "reviewer_verdict_present": false
    }
  ]
}
```
