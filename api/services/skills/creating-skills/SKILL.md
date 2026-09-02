---
name: creating-skills
description: Creates and improves skills for this workspace, turning a repeated instruction, checklist, or procedure into a skills/{name}/SKILL.md any agent here can find and follow, with a description written for discovery. Use when a member wants to make, fix, or fork a skill, or to teach a way of working.
metadata:
  target: One folder skills/{name}/ holding SKILL.md (frontmatter name + description; body under 500 lines) and any references it needs, one level deep.
---
# Creating skills

## What a skill is here

A how-to file for a kind of work. It teaches craft; it never grants reach. The runtime's gates decide what any agent may do, and a skill that claims otherwise is ignored. yarnnn's own skills live under `system/skills/` and are read-only. A workspace's own live under `skills/{name}/SKILL.md` as ordinary files: attributed, versioned, revertible. Every agent's frame lists both by description, so the description is the door.

## Steps

1. Capture intent: what work, how often, what "done" looks like. Ask for a concrete recent example.
2. Write the frontmatter. `name` is kebab-case and equals the folder name. `description` is third person, says what the skill does AND when to use it, uses the words a member would actually say, and stays under 300 characters. Optionally `metadata.apps: [slides]` (or `[text, blogger]`) names the panes the skill is for, so it is offered there and not elsewhere; leave it out and the skill is offered everywhere, which is the right default unless its output only makes sense in one pane.
3. Write the body: What you produce · Steps · Quality bar · Anti-patterns. State what to do, not why. Under 500 lines. Long references go in sibling files, named with when to read them.
4. Fork rather than edit a kernel skill: duplicate `system/skills/{name}/SKILL.md` to `skills/{name}/SKILL.md` and change the copy. The duplicate records what it forked from.
5. Test by using it: open a lane, ask for the work, watch whether the agent reads the skill and whether the output meets the bar. Tighten the description if it did not trigger.

## Anti-patterns

Restating the pane's grammar the frame already carries. A description that says "helps with". Authority language ("you may access…"). One skill that does five jobs. A body that narrates why instead of stating what.
