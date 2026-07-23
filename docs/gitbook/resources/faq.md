# Frequently Asked Questions

## The difference

### What is YARNNN?

A workspace that holds everything you and your AI produce — notes, decisions, documents, decks, images — attributed to whoever made it, with the full history of every change. You work in it two ways: **Chat** for thinking, **Studio** for making. And you can reach the same workspace from ChatGPT, Claude, or any AI that speaks MCP.

### How is this different from ChatGPT's or Claude's memory?

Three ways.

**It's authored, not inferred.** Their memory is scraped from your activity — you can't fully see it, can't correct it precisely, and can't take it with you. Yours is a set of files you wrote, can read, and can fix.

**It's shared across AIs.** Their memory works in their app. Yours works in every AI you connect.

**It has history.** Ask a memory feature how it came to believe something and it can't tell you. Ask YARNNN and you get `trace` — who wrote it, when, and what it said before.

### What is `trace`?

Every change to a file is a revision carrying its author, timestamp, and a message. `trace` walks that chain. You can see it in the app (any file → Get Info) or ask a connected AI for it.

It's the capability a storage connector structurally can't offer, because storage keeps the current state and YARNNN keeps the history.

### Is my data mine?

Yes. You author it, you can read every file, correct any of it, delete any of it, and take it with you. We don't train models on it and we don't share it between workspaces.

### Does it work with my team?

Yes. Invite by email; everyone writes into the same workspace and every change carries their name. Chat lanes stay private per person — you diverge privately and settle publicly.

## The work

### How do I get things in?

Three routes: **upload** them in Files (PDF, DOCX, TXT, MD, ZIP), **save** them from a connected AI over MCP, or **author** them here in Chat and Studio.

### Which AI models does it work with?

Inside YARNNN, the colleagues run on Claude, GPT, Gemini, and DeepSeek models — you pick a colleague and the engine rides behind the name. From outside, any MCP-capable client can connect.

Engines are deliberately swappable. The memory is the thing that stays.

### Can it read my Slack and Notion?

You can authorise Slack, Notion, and GitHub and choose what's in scope. **Scheduled background pulling isn't running yet**, so connecting alone doesn't populate your workspace today. Uploads and MCP are the reliable routes in for now.

### What's the "second set of eyes"?

That's Freddie — the workspace's own steward. He tends the record: organising, deriving, noticing what needs your attention. He's in beta, does only reversible things, and you meet him in the activity log rather than in a chat window. See [Freddie](../concepts/freddie.md).

### Can I undo things?

Yes, at several levels. **⌘Z** in Studio. **Revert** on any previous revision of any file. **Restore** from Trash, which has no timer. Even permanent delete keeps the record of what existed.

## Pricing

### What does it cost?

Free for one person. $20/mo per teammate you add. Plus shared usage — $15/mo included on the paid plan, then top up.

### Do connected AIs cost a seat?

Never. Connect as many as you like.

### Can I cap what it spends?

Yes — set a workspace budget at Workspace Settings → System. And the balance itself is a hard floor: at zero, AI work stops rather than overdrafting.

### What if my allowance runs out?

Work pauses until you top up. Nothing is lost. Your files, history, and MCP access are unaffected — reading and keeping your workspace is free.

## Getting started

### How do I start?

Sign in, open Chat, and ask a real question. Then get the answer out of the chat and into a file. That's the whole loop.

### What's the best first move?

Upload the documents you already work from. An empty workspace can't ground anything; a workspace with your material in it is useful from the first conversation.

### What should I not expect yet?

Scheduled background work from connected platforms, and Freddie as a conversational partner. Both are named plainly in these docs where they come up.
