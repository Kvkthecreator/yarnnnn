# ClawdBot (Moltbot) Research & Cross-Analysis with Yarn

> Research Date: January 2026
> Status: ClawdBot rebranded to Moltbot due to Anthropic trademark request

---

## Executive Summary

ClawdBot/Moltbot is an open-source, self-hosted AI assistant that went viral in late January 2026, reaching 60,000+ GitHub stars. Created by Peter Steinberger (founder of PSPDFKit), it represents a different paradigm from Yarn: **local-first execution agent** vs **cloud-hosted context platform**.

Both projects share core beliefs about AI needing persistent memory and autonomous action, but diverge significantly in architecture, target users, and security model.

---

## Part 1: ClawdBot/Moltbot Deep Dive

### 1.1 What It Is

ClawdBot is a self-hosted AI assistant that:
- Runs locally on user hardware (Mac, Linux, Windows, Raspberry Pi)
- Connects to messaging apps (WhatsApp, Telegram, Discord, Slack, Signal, iMessage)
- Has full system access (shell, files, browser automation)
- Maintains persistent memory across sessions
- Can proactively reach out via scheduled "heartbeats"

**Core Philosophy**: "The AI that actually does things" — an execution agent, not just a conversational assistant.

### 1.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER'S LOCAL MACHINE                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   GATEWAY    │◄──►│    AGENT     │◄──►│   SKILLS     │   │
│  │              │    │   (LLM)      │    │              │   │
│  │ - WebSocket  │    │ - Claude     │    │ - Shell      │   │
│  │ - Platform   │    │ - GPT-4      │    │ - Browser    │   │
│  │   bridges    │    │ - Gemini     │    │ - Files      │   │
│  │ - Routing    │    │ - Ollama     │    │ - Calendar   │   │
│  │ - Scheduling │    │   (local)    │    │ - Email      │   │
│  └──────────────┘    └──────────────┘    │ - GitHub     │   │
│         │                   │            │ - Smart Home │   │
│         │                   │            └──────────────┘   │
│         │                   ▼                               │
│         │            ┌──────────────┐                       │
│         │            │   MEMORY     │                       │
│         │            │              │                       │
│         │            │ - Markdown   │                       │
│         │            │   files      │                       │
│         │            │ - SOUL.md    │                       │
│         │            │ - USER.md    │                       │
│         │            │ - Sessions   │                       │
│         └────────────┴──────────────┘                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
              │
              ▼ (WebSocket bridges)
┌─────────────────────────────────────────────────────────────┐
│  WhatsApp │ Telegram │ Discord │ Slack │ Signal │ iMessage  │
└─────────────────────────────────────────────────────────────┘
```

**Four Core Components:**

| Component | Purpose | Implementation |
|-----------|---------|----------------|
| **Gateway** | Central control plane | Background daemon, WebSocket bridges to chat platforms, web UI |
| **Agent** | LLM reasoning engine | Supports Claude, GPT-4, Gemini, or local models via Ollama |
| **Skills** | Modular capabilities | Puppeteer browser, shell, filesystem, APIs, smart home |
| **Memory** | Persistent context | Local Markdown files (SOUL.md, USER.md, sessions as JSONL) |

### 1.3 Memory System

ClawdBot's memory is **file-based and local**:

```
~/clawd/                    # Agent workspace
├── SOUL.md                 # Persona and operating instructions
├── AGENTS.md               # Agent configurations
├── TOOLS.md                # Available skills
├── IDENTITY.md             # Identity context
├── USER.md                 # User preferences/info
├── HEARTBEAT.md            # Proactive task definitions
└── ...

~/.clawdbot/
├── moltbot.json            # Core configuration
└── agents/<agentId>/
    └── sessions/           # JSONL session files with token metadata
```

**Key Characteristics:**
- Plain text (Markdown) for human readability/editability
- Integrates with Obsidian, Raycast, standard backup tools
- No embeddings or vector search in core (third-party plugins like memU/Supermemory add this)
- Sessions reset via `/reset` command or scheduled triggers

### 1.4 Proactive "Heartbeat" System

Unlike reactive chatbots, ClawdBot can initiate contact:

```json
{
  "heartbeats": {
    "intervalMinutes": 30,
    "quietHours": { "start": "22:00", "end": "07:00" }
  }
}
```

- Reads `HEARTBEAT.md` for proactive task definitions
- Can trigger on cron schedules, stock alerts, weather warnings
- Returns `HEARTBEAT_OK` to suppress delivery if no action needed

### 1.5 Key Features

| Feature | Description |
|---------|-------------|
| **Full System Access** | Shell commands, file read/write, browser automation |
| **Headless Operation** | Executes commands directly (no GUI screenshots) |
| **Always-On** | Runs as daemon 24/7, persists across sessions |
| **Multi-Platform Chat** | Unified conversation across WhatsApp, Telegram, etc. |
| **Self-Modifying** | Can write and deploy its own skills |
| **Local-First** | All data stays on user hardware |

### 1.6 Pricing Model

ClawdBot itself is free (open source). Costs are infrastructure:

| Cost Component | Typical Range |
|----------------|---------------|
| VPS (if not local) | $3-6/month |
| Claude API | $20-50/month (moderate use) |
| Local models (Ollama) | $0 (requires GPU) |
| **Total** | **$25-75/month** |

### 1.7 Security Concerns (Critical)

ClawdBot has faced significant security criticism:

**Discovered Vulnerabilities:**
- Hundreds of publicly exposed instances with plaintext credentials
- Prompt injection: malicious email could trigger email forwarding to attackers
- OpenSSH private key extracted "in five minutes" via prompt injection
- No authentication on gateway by default
- Credentials stored in plaintext

**The 72-Hour Crisis (Jan 27, 2026):**
1. Anthropic issued trademark C&D → forced rebrand to "Moltbot"
2. Steinberger released old GitHub org + Twitter handles
3. Crypto scammers claimed both in seconds
4. Fake $CLAWD token reached $16M market cap before collapse

**Expert Assessment:**
> "A significant gap exists between the consumer enthusiasm for Clawdbot's one-click appeal and the technical expertise needed to operate a secure agentic gateway." — Eric Schwake, Salt Security

---

## Part 2: Yarn Architecture Summary

### 2.1 What Yarn Is

Yarn is a **cloud-hosted context platform** that:
- Accumulates knowledge over time (memories, documents)
- Runs specialized agents against that context
- Delivers work proactively (push, not pull)
- Isolates context by project (multi-tenant)

**Core Philosophy**: "Your AI agents understand your world because they read from your accumulated context."

### 2.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLOUD INFRASTRUCTURE                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
│  │   NEXT.JS   │────►│   FASTAPI   │────►│  SUPABASE   │    │
│  │  FRONTEND   │     │   BACKEND   │     │  POSTGRES   │    │
│  │             │     │             │     │  + STORAGE  │    │
│  │ - Dashboard │     │ - Routes    │     │             │    │
│  │ - Project   │     │ - Agents    │     │ - memories  │    │
│  │   views     │     │ - Services  │     │ - documents │    │
│  │ - Chat UI   │     │ - Jobs      │     │ - chunks    │    │
│  └─────────────┘     └─────────────┘     │ - sessions  │    │
│                             │            │ - tickets   │    │
│                             ▼            └─────────────┘    │
│                      ┌─────────────┐                        │
│                      │   AGENTS    │                        │
│                      │             │                        │
│                      │ - Thinking  │                        │
│                      │   Partner   │                        │
│                      │ - Research  │                        │
│                      │ - Content   │                        │
│                      │ - Reporting │                        │
│                      └─────────────┘                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Memory System

Yarn uses **semantic, scoped memory with embeddings**:

```sql
memories
├── id, workspace_id, project_id (nullable for user-scope)
├── content (text)
├── embedding (vector(1536))
├── importance (0-1)
├── source_type (chat, document, manual, import)
├── source_ref (JSON lineage)
└── is_active (soft delete)
```

**Key Characteristics:**
- Embeddings-first for semantic retrieval
- Scoped: user-level (portable) vs project-level (isolated)
- Full provenance tracking
- Document pipeline: upload → parse → chunk → embed → extract memories

### 2.4 Agent Types

| Agent | Purpose |
|-------|---------|
| **Thinking Partner** | Conversational reasoning with tools |
| **Research** | Investigate topics, synthesize patterns |
| **Content** | Create platform-specific content |
| **Reporting** | Structured report generation |

### 2.5 Pricing Model

SaaS subscription:

| Tier | Price | Limits |
|------|-------|--------|
| Free | $0 | 1 project, 50 memories, 5 sessions/month |
| Pro | $19/month | Unlimited + scheduled agents |

---

## Part 3: Cross-Analysis

### 3.1 Architectural Comparison

| Dimension | ClawdBot | Yarn |
|-----------|----------|------|
| **Deployment** | Self-hosted (local) | Cloud-hosted (SaaS) |
| **Data Location** | User's machine | Supabase cloud |
| **Memory Storage** | Markdown files | PostgreSQL + pgvector |
| **Memory Retrieval** | File-based (plugins for vectors) | Embeddings-first semantic search |
| **Execution** | Full system access | Sandboxed API calls only |
| **Interface** | Messaging apps (WhatsApp, etc.) | Web app (Next.js) |
| **Target User** | Technical power users | Knowledge workers |
| **Security Model** | User-managed (high risk) | Platform-managed |

### 3.2 Memory System Comparison

| Aspect | ClawdBot | Yarn |
|--------|----------|------|
| **Format** | Plain Markdown | Structured SQL + vectors |
| **Portability** | Copy files anywhere | Export API (TBD) |
| **Searchability** | grep/text (vectors via plugin) | Semantic similarity native |
| **Scoping** | Single user, single workspace | Multi-project, user + project scope |
| **Provenance** | Manual (file paths) | Automatic (source_type, source_ref) |
| **Importance** | Implicit (file placement) | Explicit (0-1 score) |

### 3.3 Agent Capabilities

| Capability | ClawdBot | Yarn |
|------------|----------|------|
| **System Access** | Full (shell, files, browser) | None (API-only) |
| **Specialization** | Single general agent + skills | 4 specialized agent types |
| **Tool Use** | 50+ integrations | Project tools, memory tools |
| **Self-Modification** | Can write own skills | No |
| **Proactive Execution** | Heartbeat system | Scheduled work (planned) |

### 3.4 Delivery Model

| Aspect | ClawdBot | Yarn |
|--------|----------|------|
| **Primary Channel** | Messaging apps | Web app + email |
| **Proactive Contact** | Heartbeats via chat | Scheduled digests (planned) |
| **Cross-Platform** | WhatsApp, Telegram, Discord, etc. | Web only (currently) |

### 3.5 Security Posture

| Aspect | ClawdBot | Yarn |
|--------|----------|------|
| **Attack Surface** | Massive (full system access) | Limited (API boundaries) |
| **Credential Storage** | Plaintext files | Supabase auth + RLS |
| **Multi-Tenancy** | Single user | Workspace isolation |
| **Prompt Injection Risk** | Critical (system commands) | Moderate (data exposure) |
| **User Responsibility** | High (configure firewalls, VPNs) | Low (platform manages) |

---

## Part 4: Learnings for Yarn

### 4.1 What ClawdBot Gets Right (Adopt)

#### 1. **Messaging-First Interface**
ClawdBot's killer UX is meeting users where they are (WhatsApp, Telegram). Users don't need to open a new app.

**Recommendation**: Add messaging integrations as delivery channels:
- Telegram bot for work delivery notifications
- Slack integration for team workspaces
- WhatsApp for personal projects

#### 2. **Proactive Heartbeat System**
The heartbeat concept—agent checks in periodically and initiates contact when relevant—is powerful.

**Recommendation**: Enhance scheduled work to include:
- Configurable check intervals per project
- Conditional triggers ("notify me if X changes")
- Quiet hours support

#### 3. **Human-Readable Memory Files**
SOUL.md, USER.md pattern makes the agent's "mind" inspectable and editable.

**Recommendation**: Add "Export as Markdown" feature:
- User can download project context as readable files
- Enables backup, editing, migration
- Builds trust through transparency

#### 4. **Local Model Support**
Ollama integration lets privacy-conscious users run fully local.

**Recommendation**: Consider hybrid mode:
- Keep cloud for storage/sync
- Allow local model inference for sensitive projects
- "Air-gapped project" mode for compliance

### 4.2 What ClawdBot Gets Wrong (Avoid)

#### 1. **Security as Afterthought**
Plaintext credentials, no auth by default, prompt injection vulnerabilities—these are fundamental design flaws.

**Lesson**: Yarn's sandboxed approach is correct. Never give agents system access without explicit user approval per action.

#### 2. **Single-User Assumption**
No multi-tenancy means no team collaboration path.

**Lesson**: Yarn's workspace model is better positioned for B2B expansion.

#### 3. **Memory Without Structure**
Plain files work for simple cases but don't scale to semantic search or importance ranking.

**Lesson**: Yarn's embeddings + importance scoring + provenance tracking is more powerful for knowledge work.

#### 4. **No Guardrails**
Users can easily misconfigure and expose themselves.

**Lesson**: Yarn should enforce sensible defaults and make security opt-out, not opt-in.

### 4.3 Feature Gap Analysis

| Feature | ClawdBot Has | Yarn Has | Priority |
|---------|-------------|----------|----------|
| Messaging delivery | ✅ | ❌ | **High** |
| Proactive triggers | ✅ | 🔄 (planned) | **High** |
| System access | ✅ | ❌ | Low (security risk) |
| Local models | ✅ | ❌ | Medium |
| Semantic memory | 🔌 (plugin) | ✅ | - |
| Multi-project | ❌ | ✅ | - |
| Team collaboration | ❌ | 🔄 (planned) | Medium |
| Document ingestion | ❌ | ✅ | - |
| Specialized agents | ❌ | ✅ | - |
| Provenance tracking | ❌ | ✅ | - |

### 4.4 Positioning Implications

ClawdBot's viral success validates the market for:
- **Persistent AI memory** (users want agents that remember)
- **Proactive agents** (push, not just pull)
- **Action, not just advice** (execution over conversation)

**Yarn's Differentiation**:
1. **Enterprise-ready**: Multi-tenant, secure by default
2. **Knowledge-focused**: Better for research/analysis than task automation
3. **Specialized agents**: Right tool for the job (vs. one general agent)
4. **Provenance**: Know what informed each output

**Target User Contrast**:
- ClawdBot: Technical users who want a personal AI assistant
- Yarn: Knowledge workers who need an AI research partner

---

## Part 5: Recommendations

### 5.1 Immediate (Next 30 Days)

1. **Add Telegram delivery channel**
   - Notify users when scheduled work completes
   - Allow quick chat responses via Telegram
   - Low effort, high perceived value

2. **Implement "Heartbeat" equivalent**
   - Project-level monitoring triggers
   - "Alert me when news about X appears"
   - Builds on existing scheduled work infrastructure

3. **Memory export feature**
   - Download project as Markdown bundle
   - SOUL.md equivalent for each project
   - Enables user inspection/editing

### 5.2 Medium-Term (60-90 Days)

4. **Slack integration**
   - Critical for team adoption
   - Deliver work to channels
   - Accept commands from DMs

5. **Conditional triggers**
   - "Run research agent when new document uploaded"
   - Event-driven, not just time-driven

6. **Mobile-friendly interface**
   - ClawdBot works because it's in your pocket (via messaging)
   - Yarn needs better mobile experience

### 5.3 Long-Term (Evaluate)

7. **Local model option**
   - Privacy-sensitive users
   - Enterprise on-prem deployments
   - Significant engineering effort

8. **Limited action capabilities**
   - Carefully scoped: create draft email, create calendar event
   - User approval required for each action
   - Never full system access

---

## Part 6: Competitive Landscape

```
                    HIGH SYSTEM ACCESS
                           │
         ClawdBot/Moltbot  │
              ●            │
                           │
                           │
    SELF-HOSTED ───────────┼─────────── CLOUD-HOSTED
                           │
                           │          Yarn ●
                           │
              ●            │              ● ChatGPT
         Open Interpreter  │                Memory
                           │
                    LOW SYSTEM ACCESS
```

**Yarn's Position**: Cloud-hosted, low system access, high knowledge management.

**Opportunity**: The enterprise quadrant (cloud + secure + proactive) is underserved.

---

## Part 7: Reframing for the Non-Technical User

> **Counter-thesis**: The technical comparison above misses the point. Yarn can be superior in ALL aspects—but the lens matters. Here's the analysis through the eyes of a non-technical user.

### 7.1 The Real ClawdBot Problem

ClawdBot's 60k stars are **misleading signal**. Look closer:

**Who actually uses ClawdBot?**
- Developers who can run `npm install -g moltbot@latest`
- People comfortable editing JSON config files
- Users who understand VPS, SSH, API keys, webhooks
- Security-savvy users who can configure firewalls

**Who WANTS an AI assistant?**
- Busy professionals drowning in information
- Small business owners who can't afford a VA
- Consultants juggling multiple clients
- Anyone who wishes they had a "second brain"

**The gap**: ClawdBot serves the builders, not the users. The viral moment was developer enthusiasm, not mainstream adoption.

### 7.2 Why "Self-Hosted" is a Bug, Not a Feature

From a non-technical user's perspective:

| ClawdBot Requires | What Normal People Think |
|-------------------|-------------------------|
| "Provision Ubuntu 22.04 VPS" | "What's a VPS?" |
| "Install Node.js 22+" | "I just want it to work" |
| "Configure moltbot.json" | "Why am I editing code?" |
| "Set up API keys" | "This feels like I'll break something" |
| "Run security audit" | "I don't know what I'm auditing" |

**ClawdBot's dirty secret**: The "free" open-source tool costs:
- $25-75/month in API + infrastructure
- Hours of setup and maintenance
- Ongoing security vigilance
- Technical debt when things break

**Yarn's advantage**: Sign up → Use it. That's it.

### 7.3 Reframing Yarn's Value Proposition

**Current framing** (technical):
> "Cloud-hosted context platform with embeddings-first semantic memory and specialized agents"

**Better framing** (human):
> "Your AI that actually knows you—and does the work"

Or even simpler:
> "The AI assistant that gets smarter the more you use it"

### 7.4 The Non-Technical User Journey

**What a consultant named Sarah actually wants:**

1. **Morning**: "What should I focus on today across all my clients?"
2. **Research**: "Summarize everything I know about Client X's industry"
3. **Preparation**: "Draft talking points for my 3pm call, based on our history"
4. **Follow-up**: "Turn my meeting notes into action items and send a recap"
5. **End of week**: "What did I accomplish? What's falling through cracks?"

**How ClawdBot handles this:**
- Sarah would need to set up WhatsApp integration ❌
- Configure shell access for calendar ❌
- Write custom skills for her workflow ❌
- Hope prompt injection doesn't leak client data ❌
- Sarah gives up after 2 hours of setup ❌

**How Yarn SHOULD handle this:**
- Sarah signs up, creates "Client X" project ✅
- Uploads past emails, notes, contracts ✅
- Chats naturally: "What do I know about their Q3 priorities?" ✅
- Gets weekly digest: "Here's what needs attention" ✅
- Never thinks about infrastructure ✅

### 7.5 Yarn's True Differentiators (User Lens)

| What Users Say They Want | ClawdBot Reality | Yarn Opportunity |
|--------------------------|------------------|------------------|
| "Just works" | 30-60 min technical setup | Sign up and go |
| "Remembers everything" | Manual file management | Automatic context accumulation |
| "Understands MY work" | Generic assistant | Project-scoped intelligence |
| "Keeps things separate" | Single workspace chaos | Clean project boundaries |
| "I can trust it" | Security vulnerabilities | Enterprise-grade by default |
| "Shows its work" | Black box responses | Provenance: "Based on your notes from Jan 15" |

### 7.6 The Messaging App Myth

ClawdBot's WhatsApp/Telegram integration seems compelling. But consider:

**Why messaging feels appealing:**
- Familiar interface
- Always in pocket
- Low friction to start conversation

**Why messaging is actually limiting:**
- Terrible for complex outputs (reports, analysis)
- No way to organize information
- Can't see your accumulated context
- Mixed with personal chats (cognitive load)
- No visual workspace for thinking

**Yarn's opportunity**: Don't copy the messaging interface. Build something better.

**What's better than messaging?**
- A dedicated space for each domain of your life/work
- Visual memory: see what your AI knows, organized
- Rich outputs: tables, reports, documents—not chat bubbles
- Ambient awareness: AI monitors and surfaces insights without you asking

### 7.7 Positioning Yarn for the Mainstream

**Target user persona shift:**

| Old Persona | New Persona |
|-------------|-------------|
| "Knowledge workers" (vague) | "Overwhelmed professionals" (specific) |
| "Enterprise" (cold) | "Solo consultants, small teams" (warm) |
| "Power users" (intimidating) | "Busy people who aren't technical" (inclusive) |

**Messaging shift:**

| Technical Framing | Human Framing |
|-------------------|---------------|
| "Persistent semantic memory" | "Never forgets what you told it" |
| "Multi-project context isolation" | "Keeps your clients separate" |
| "Specialized agent orchestration" | "Different AI helpers for different tasks" |
| "Document ingestion pipeline" | "Upload your files, it reads them" |
| "Proactive scheduled execution" | "Does work while you sleep" |
| "Provenance tracking" | "Shows you where answers come from" |

### 7.8 The "It Just Works" Roadmap

To win the non-technical user, Yarn needs:

#### Immediate (Perception)

1. **Landing page rewrite**
   - Lead with outcomes, not features
   - Show real workflows (consultant, freelancer, researcher)
   - Zero technical jargon above the fold

2. **Onboarding magic**
   - First project created automatically ("My Work")
   - Guided tour that creates first memory from user input
   - "Upload something you're working on" prompt

3. **Empty state storytelling**
   - Don't show blank dashboards
   - Show example projects with sample memories
   - "Here's what Yarn looks like after a month"

#### Near-term (Functionality)

4. **"Quick capture" everywhere**
   - Browser extension: highlight → save to project
   - Mobile: share sheet integration
   - Email: forward emails to project-specific address

5. **Proactive insights (not just heartbeats)**
   - "You haven't looked at Client X in 2 weeks"
   - "This document contradicts what you said in August"
   - "Based on your patterns, you might want to..."

6. **Natural language project setup**
   - "I'm a consultant with 5 clients" → creates 5 projects
   - "I'm researching AI for my thesis" → creates research structure
   - AI configures, user validates

#### Long-term (Differentiation)

7. **"Show your work" as brand**
   - Every output cites sources from user's own context
   - Builds trust that ChatGPT/ClawdBot can't match
   - Makes users feel ownership, not dependency

8. **Ambient AI (not reactive chat)**
   - Yarn monitors your context and surfaces insights
   - "Based on your client conversations this week..."
   - Move from pull (user asks) to push (AI offers)

### 7.9 Competitive Positioning Matrix (Revised)

```
                        EASY TO USE
                            │
                   Yarn     │     ChatGPT
                   (target) │     (current)
                      ◎     │        ●
                            │
    FORGETS ────────────────┼──────────────── REMEMBERS
                            │
                      ●     │        ●
                  ClawdBot  │     Notion AI
                  (actual)  │
                            │
                      HARD TO USE
```

**Yarn's strategic position**: Top-right quadrant—easy to use AND remembers everything.

ClawdBot is in the wrong quadrant entirely (hard to use). That's not competition, that's a cautionary tale.

### 7.10 The Counter-Narrative

**Stop saying:**
- "We're like ClawdBot but cloud-hosted"
- "We have better security than ClawdBot"
- "We're enterprise-ready"

**Start saying:**
- "AI that actually knows your work"
- "Never explain the same thing twice"
- "Your second brain that does the work"
- "See exactly why AI said what it said"

**The real competition isn't ClawdBot.** It's:
- The overwhelmed professional using ChatGPT and forgetting context every session
- The consultant with 47 browser tabs and scattered notes
- The person who gave up on "productivity tools"

Yarn wins by being the first AI that feels like it truly knows you—without requiring a CS degree to set up.

---

## Part 8: Summary — What Yarn Should Actually Do

### Don't Do (Technical Copying)
- ❌ Add WhatsApp/Telegram as primary interface
- ❌ Add "full system access" capabilities
- ❌ Position against ClawdBot feature-for-feature
- ❌ Target "power users" or developers

### Do (Market Positioning)
- ✅ Rewrite all messaging for non-technical users
- ✅ Nail the "zero to value" onboarding experience
- ✅ Make "provenance" a brand differentiator ("AI you can trust")
- ✅ Build ambient intelligence (push), not reactive chat (pull)
- ✅ Target overwhelmed professionals, not techies
- ✅ Let ClawdBot have the hacker market; take the mainstream

### The One-Liner Test

**ClawdBot**: "Self-hosted AI agent with full system access"
→ Appeals to: developers (small market)

**Yarn (current)**: "Context-aware AI work platform"
→ Appeals to: ???

**Yarn (reframed)**: "The AI assistant that actually knows your work"
→ Appeals to: everyone who's frustrated with forgetful AI (huge market)

---

## Sources

- [ClawdBot Complete Guide 2026 - God of Prompt](https://www.godofprompt.ai/blog/clawdbot-guide-2026)
- [From Clawdbot to Moltbot - DEV Community](https://dev.to/sivarampg/from-clawdbot-to-moltbot-how-a-cd-crypto-scammers-and-10-seconds-of-chaos-took-down-the-4eck)
- [Moltbot Official Website](https://clawd.bot/)
- [Moltbot Documentation](https://docs.molt.bot/start/clawd)
- [Moltbot Use Cases and Security - AIMultiple](https://research.aimultiple.com/moltbot/)
- [memU Memory Framework - GitHub](https://github.com/NevaMind-AI/memU)
- [Awesome Moltbot Skills - GitHub](https://github.com/VoltAgent/awesome-moltbot-skills)
- [Cloudflare Moltworker - GitHub](https://github.com/cloudflare/moltworker)
