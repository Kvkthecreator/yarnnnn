# Chat

Chat is where you think. It's a set of conversation **lanes**, each one grounded in your workspace.

## Lanes, not one long thread

A lane is a single conversation. You can have many — up to **20 active lanes** at a time (archive old ones to make room). Bound lanes inside Text, Slides, Blogger and Images don't count toward that limit.

Each lane is **private to you**. In a shared workspace, your teammates never see your lanes. What gets shared is what lands in Files.

Lanes are listed newest-first. You can:

- **Rename** a lane inline
- **Pin** it so it sorts to the top
- **Archive** it when you're done
- **Search** across lane names and transcript content

## You pick an engine

Starting a conversation is choosing a **model**, not a character. Chat is the raw-LLM surface: you're talking to an engine, grounded in your workspace.

The current roster spans four providers:

| Provider | Models |
|---|---|
| **Anthropic** | Claude Opus 5 · Claude Sonnet 5 · Claude Haiku 4.5 |
| **OpenAI** | GPT-5 · GPT-4o mini |
| **Google** | Gemini 2.5 Pro · Gemini 3.5 Flash Lite |
| **DeepSeek** | DeepSeek |

Your last choice is remembered, so you don't re-pick every time, and the full list is one click away. The engine is visible on the lane, because a revision it writes is signed with it — reading your own history has to tell you which model authored what.

They differ in price and in what they're good at. The [engines page](https://www.yarnnn.com/engines) is the current public reference.

If you want a *character* rather than an engine — someone with a job and a posture — that's an app's bound lane. See [Agents](agents.md).

## Who else is in the room

A lane isn't necessarily just you and a model. The **cast** shows who's in the conversation, and you can bring in another person from your workspace or an agent. What they say lands in the same transcript.

## What a lane can do

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
| History carried per turn | The most recent ~120,000 characters |

When a conversation outgrows the history window, the **oldest** messages drop first — never the middle, so the thread you're in stays intact.

A long file a lane reads is capped too, and it says so when it truncates rather than pretending it read the whole thing.

On a phone, the lane list and the conversation are separate screens — pick a lane to open it, and there's a way back.
