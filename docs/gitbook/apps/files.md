# Files

Files is the whole workspace, laid out as a browser: a tree on the left, a viewer on the right.

## What's in it

| Zone | What lives there |
|---|---|
| **Documents** | Your authored work — the home level. Folders you create appear as peers of Documents, the way a home directory works |
| **Downloads** | Everything that arrived from somewhere else — uploads, and anything captured from a connected source |
| **System files** | Kernel and configuration files, collapsed out of the way |
| **Trash** | Deleted files, held until you empty it |

When nothing is selected, you see **Recents** — the most recent revisions across the workspace, so you can pick up where anyone left off.

## Working with files

Right-click anything:

- **Open** — opens it in the app that owns its type. A deck opens in Studio; an image composition opens in Images; anything else opens in a generic viewer
- **Get Info / Properties** — kind, location, ownership, modified date, contributors, and the full revision history
- **Rename**
- **Move to…** — or drag and drop
- **Share…** — creates a link
- **Move to Trash**

Changes apply immediately and optimistically; you don't wait on a save.

## Revision history

Every file carries its full chain of revisions, newest first: which revision, who authored it, the message that came with it, and how long ago.

Click any revision to see a diff against the current version. On any revision that isn't the current one, you can **Revert** — which writes the old content back as a *new* revision, attributed to you. Nothing is erased; the correction is part of the record.

Authors are colour-coded by kind — you, an agent, an external AI reaching in over MCP, or the system.

## Uploads

Right-click the canvas → **Add Files**, or drag files onto it. On touch devices there's a button in the header.

Uploads land in **Downloads**, and the dialog tells you so up front: *your agents can read these files.*

The file picker accepts **PDF, DOCX, TXT, MD, and ZIP** (a ZIP is unpacked on arrival). Documents and images are capped at 25 MB; audio and video at 100 MB.

For text-bearing documents, YARNNN also derives a searchable text version alongside the original. The original is never modified — the derived version cites it.

## Trash and permanent delete

Deleting moves a file to Trash. The file still exists, its history is intact, and **Restore** puts it back exactly as it was.

If other files were made from the one you're trashing, you'll be told: *N other files were made from this one — they keep their history, but their live references will point at the Trash.*

Trash has no timer. Nothing is auto-deleted after 30 days; it waits for you. When you're ready there are two terminal actions, both requiring explicit confirmation:

- **Delete Permanently** on a single file
- **Empty Trash** on everything in it

Permanent delete removes the bytes. **It does not remove the record** — the attributed history of what existed and who changed it survives. Unrecoverable, not unremembered.

## Sharing a file

Right-click → **Share…** copies a link to your clipboard.

Be aware of what that link does: anyone with it who signs in **joins your workspace as a member**, with access to the whole commons — not just that one file. The file is the landing page; opening it is the activation. Treat share links like an invitation, because that's what they are. You can set an expiry when you create one.

To bring someone in deliberately, use an email invite instead — see [Working with a team](../concepts/working-with-a-team.md).
