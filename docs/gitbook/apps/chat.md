# Chat

Chat is where you think. It's a set of conversation **lanes**, each one grounded in your workspace.

## Lanes, not one long thread

A lane is a single conversation. You can have many — up to **20 active lanes** at a time (archive old ones to make room). Bound lanes inside Studio don't count toward that limit.

Each lane is **private to you**. In a shared workspace, your teammates never see your lanes. What gets shared is what lands in Files.

Lanes are listed newest-first. You can:

- **Rename** a lane inline
- **Pin** it so it sorts to the top
- **Archive** it when you're done
- **Search** across lane names and transcript content
- **Filter by colleague** — see all your Researcher lanes, for instance

## You pick who, not which model

When you start a new lane, you choose a **colleague**, not an engine:

| Colleague | What they're for |
|---|---|
| **Thinker** | Thinks a problem through with you — writing, judgment, hard calls |
| **Researcher** | Digs through material fast — your workspace and the web, with sources |
| **Designer** | Makes the thing itself — decks, docs, the artifact in front of you |
| **Critic** | Pressure-tests an idea — finds the hole before it costs you |

The engine behind each colleague stays visible as a chip on the lane, but it isn't the thing you choose. You can also hire and name your own colleagues on the [Agents](agents.md) surface — a lane started with them works identically.

Under the hood the roster spans Claude, GPT, Gemini, and DeepSeek models. Which one is running is a fact you can see, not a decision you have to make.

## What a lane can do

Every colleague has the same capabilities — no agent can do something another can't.

- **Read and search your workspace** — semantic search across everything you've authored
- **Search the web**
- **Read, write, edit, and list files** — a lane can create a file or revise one, and the result appears as a card you can open
- **Take attachments** — drop in a file or an image; images go to the model as vision content when the model supports it
- **Learn from a file** — point a lane at an existing file and it works from that

Every file a lane writes is an attributed revision — the ledger records that the write came from you, through that model.

## Editing and resending

You can edit a previous message and resend it. That truncates the conversation from that point.

Note: files a lane already wrote **stay written**. The transcript rewinds; the record doesn't. That's intentional — the workspace is a ledger, not a draft.

## Grounding

The point of chatting here rather than in a general-purpose chat app is that the conversation starts from your material. Ask about a project and the lane can pull the actual files rather than guessing.

Grounding is strongest for material that's been indexed — files you've settled, uploaded, or explicitly saved. Everything is searchable by text; semantic search reaches indexed content.

## Limits

| | |
|---|---|
| Active lanes | 20 per person, per workspace |
| Lane name | 60 characters |
| Message length | 32,000 characters |
| History sent per turn | Last 20 messages |
| Response timeout | 120 seconds |

On a phone, the lane list and the conversation are separate screens — pick a lane to open it, and there's a way back.
