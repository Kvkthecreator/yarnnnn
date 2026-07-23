# Working With a Team

A YARNNN workspace is a shared commons. Everyone in it writes into the same filesystem, and every change carries the name of whoever made it.

## Diverge privately, settle publicly

The rule that makes a shared workspace usable:

- **Chat lanes are private.** Your conversations are yours. Teammates never see them, and you never see theirs.
- **Files are shared.** What lands in the workspace is visible to everyone in it.

So you can think messily without an audience, and share the conclusion rather than the process.

## Inviting someone

**Workspace Settings → Access → Workspace Members.** Invite by email; they get a link that only works for that address. Accepting mints their membership and drops them into the workspace.

The first person in a workspace — the owner — is free. Each additional person is a billed seat. See [Plans and pricing](../plans/plans.md).

## The members roster

The Access pane shows everyone who can write to the workspace, in two groups:

**People** — the owner and members. For each, you can:
- **Narrow** their write access to specific regions of the workspace
- **Revoke** them entirely

**AI connections** — every external AI that's been connected over MCP, listed by provider and by who connected it. Each is a named, revocable row. If you and a teammate both connect your own ChatGPT, those are two separate rows — revoking yours leaves theirs alone.

The owner's own access can't be narrowed or revoked. There's no way to lock yourself out.

## Share links

Right-clicking a file gives you **Share…**, which copies a link.

Read this carefully: **a share link is an invitation to the workspace, not to the file.** Anyone who opens it and signs in becomes a member with access to everything. The file is just where they land.

Use share links for people you'd invite anyway. For anything narrower, send the content rather than the link. You can set an expiry when you create the link.

## What everyone sees

- **Files → Recents** — the latest revisions across the workspace, whoever made them
- **Any file → Get Info** — its contributors and full history
- **Notifications** — what needs attention

Because every revision is attributed, "who changed this?" is always answerable — which is what makes a shared workspace something other than a shared folder.
