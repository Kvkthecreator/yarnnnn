# How Your Data Is Used

## What's in your workspace

Everything in a YARNNN workspace got there because someone put it there:

- **What you author** — chat lanes, documents, decks, images, notes
- **What you upload** — files you add through Files
- **What arrives over MCP** — things you asked ChatGPT or Claude to remember
- **What a connected platform sends** — from any connection you've authorised

Nothing is scraped from your activity. There's no background inference building a hidden profile. If it's in your workspace, it's a file you can open, read, correct, and delete.

## What YARNNN does with it

**Grounds your conversations.** When you ask a chat lane something, it can search and read your workspace so the answer starts from your material.

**Feeds the work.** Studio artifacts, derived summaries, and anything an agent produces draw on the files you point them at.

**Gets sent to model providers to do that work.** This is worth being plain about: when a lane reasons over a file, that file's relevant content is sent to whichever model is running the lane — Anthropic, OpenAI, Google, or DeepSeek. Which engine a colleague runs on is shown on its card.

## What YARNNN doesn't do

- **It doesn't train models on your data.** Your content isn't used to train foundation models.
- **It doesn't share your workspace with other users.** Only principals you've granted access to can read it.
- **It doesn't infer memory in the background.** What's remembered is what was written.
- **It doesn't store your passwords.** Platform connections store encrypted OAuth tokens.

## Retention

**What you author is kept until you delete it.** There's no expiry on your own work.

**Deleting is reversible by default.** Files go to Trash and stay there — no timer — until you explicitly empty it. Permanent delete removes the bytes; the attributed record that they existed remains.

**Raw material captured from a connected platform** is subject to a retention window set by your plan, and by your own retention setting within that ceiling. Derived work made from it is not affected.

## Your controls

| What | Where |
|---|---|
| Read, correct, or delete any file | Files |
| See who changed what | Files → Get Info → history |
| Restore something deleted | Files → Trash |
| Permanently delete | Files → Trash → Delete Permanently / Empty Trash |
| Revoke an AI's access | Workspace Settings → Access |
| Narrow or remove a teammate | Workspace Settings → Access |
| Disconnect a platform | Settings → Connections |
| Cap what the workspace can spend | Workspace Settings → System → Budget |
| Clear work history or the whole workspace | Workspace Settings → Danger Zone |
| Reset or deactivate your account | Settings → Account |

## Security

- Encrypted in transit and at rest
- OAuth tokens encrypted at rest
- Access enforced per principal, per workspace, on every read and write
- Workspace-destroying actions are owner-grade and require explicit confirmation
