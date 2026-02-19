# ADR-040: Architecture Diagrams

> **Companion document to ADR-040**
> **Visual reference for proactive layer architecture**

---

## High-Level Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              USER TOUCHPOINTS                                 │
├────────────────────┬─────────────────────┬───────────────────────────────────┤
│     TP (Chat)      │    Desk (Work)      │         Platform Apps             │
│   "Create a..."    │   Review/Approve    │   Slack, Gmail, Calendar          │
└────────┬───────────┴──────────┬──────────┴──────────────┬────────────────────┘
         │                      │                          │
         ▼                      ▼                          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           PROACTIVE LAYER                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐   │
│  │  DELIVERABLES   │  │  NOTIFICATIONS  │  │         MONITORS            │   │
│  │                 │  │                 │  │                             │   │
│  │ • Heavy pipeline│  │ • Light pipeline│  │ • Condition evaluation      │   │
│  │ • Governance    │  │ • Always auto   │  │ • Triggers deliverables     │   │
│  │ • Recurring     │  │ • One-off alerts│  │ • Triggers notifications    │   │
│  └────────┬────────┘  └────────┬────────┘  └──────────────┬──────────────┘   │
│           │                    │                          │                   │
│           └────────────────────┼──────────────────────────┘                   │
│                                ▼                                              │
│                    ┌───────────────────────┐                                  │
│                    │   DELIVERY SERVICE    │                                  │
│                    │ • Export to platforms │                                  │
│                    │ • Track outcomes      │                                  │
│                    └───────────────────────┘                                  │
└──────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         PLATFORM INTEGRATIONS                                 │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│   │  Slack   │  │  Gmail   │  │  Notion  │  │ Calendar │  │   Push   │       │
│   │ Exporter │  │ Exporter │  │ Exporter │  │ Exporter │  │ Service  │       │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Deliverable Creation to Delivery

```
User: "Create a weekly digest from #daily-work"
                    │
                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                          TP AGENT                                │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │list_platform │   │sync_platform │   │ create_deliverable   │ │
│  │_resources    │──▶│_resource     │──▶│                      │ │
│  │(find channel)│   │(get messages)│   │ title, prompt, dest, │ │
│  └──────────────┘   └──────────────┘   │ governance, schedule │ │
│                                        └───────────┬──────────┘ │
└────────────────────────────────────────────────────┼────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DELIVERABLE PIPELINE                          │
│                                                                  │
│  ┌────────┐   ┌────────────┐   ┌───────┐   ┌─────────┐   ┌────┐ │
│  │ GATHER │──▶│ SYNTHESIZE │──▶│ STAGE │──▶│ APPROVE │──▶│SEND│ │
│  └────────┘   └────────────┘   └───┬───┘   └────┬────┘   └──┬─┘ │
│                                    │            │           │    │
│                                    ▼            ▼           ▼    │
│                              [NOTIFICATION] [NOTIFICATION] [LOG] │
│                              "Ready for     "Delivered     Audit │
│                               review"        to #general"  trail │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Event-Triggered Proactive Action

```
Platform Event (Slack mention)
            │
            ▼
┌───────────────────────────────────────────────────────────────────┐
│                      EVENT TRIGGER SERVICE                         │
│  ┌───────────────┐   ┌───────────────┐   ┌─────────────────────┐  │
│  │ Parse Event   │──▶│ Match Monitors│──▶│ Check Cooldown      │  │
│  │ (normalize)   │   │ (find matches)│   │ (rate limit)        │  │
│  └───────────────┘   └───────┬───────┘   └──────────┬──────────┘  │
│                              │                      │              │
│                              ▼                      ▼              │
│                     ┌────────────────────────────────────────┐    │
│                     │            FOR EACH MATCH              │    │
│                     │  ┌─────────────────────────────────┐   │    │
│                     │  │ action_type == "deliverable"    │   │    │
│                     │  │ → execute_deliverable()         │   │    │
│                     │  ├─────────────────────────────────┤   │    │
│                     │  │ action_type == "notification"   │   │    │
│                     │  │ → send_notification()           │   │    │
│                     │  ├─────────────────────────────────┤   │    │
│                     │  │ action_type == "both"           │   │    │
│                     │  │ → execute both                  │   │    │
│                     │  └─────────────────────────────────┘   │    │
│                     └────────────────────────────────────────┘    │
│                                      │                             │
│                                      ▼                             │
│                          ┌────────────────────┐                    │
│                          │ LOG TRIGGER EVENT  │                    │
│                          │ (audit + cooldown) │                    │
│                          └────────────────────┘                    │
└───────────────────────────────────────────────────────────────────┘
```

---

## Notification Channels

```
┌─────────────────────────────────────────────────────────────────┐
│                    NOTIFICATION SERVICE                          │
│                                                                  │
│  send_notification(user, message, channel, urgency, context)    │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    CHANNEL ROUTER                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│            │            │            │            │              │
│            ▼            ▼            ▼            ▼              │
│     ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│     │  IN_APP  │ │  EMAIL   │ │ SLACK_DM │ │   PUSH   │        │
│     ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤        │
│     │ Write to │ │ Send via │ │ Send via │ │ Firebase │        │
│     │ table,   │ │ Resend   │ │ MCP Slack│ │ or       │        │
│     │ frontend │ │ or SES   │ │ exporter │ │ OneSignal│        │
│     │ polls    │ │          │ │          │ │ (future) │        │
│     └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│                                                                  │
│  All channels:                                                   │
│  1. Insert notification record (pending)                         │
│  2. Attempt delivery via channel                                 │
│  3. Update status (sent/failed)                                  │
│  4. Log for audit                                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Governance Flow

```
                    Deliverable Instance Created
                              │
                              ▼
                    ┌───────────────────┐
                    │  Check Governance │
                    └─────────┬─────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │  MANUAL  │        │ SEMI_AUTO│        │ FULL_AUTO│
    └────┬─────┘        └────┬─────┘        └────┬─────┘
         │                   │                   │
         ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │  Stage   │        │  Stage   │        │  Stage   │
    │ (draft)  │        │ (brief)  │        │ (skip)   │
    └────┬─────┘        └────┬─────┘        └────┬─────┘
         │                   │                   │
         ▼                   │                   │
    ┌──────────┐             │                   │
    │ Notify   │             │                   │
    │ "Ready   │             │                   │
    │  for     │             │                   │
    │ review"  │             │                   │
    └────┬─────┘             │                   │
         │                   │                   │
         ▼                   ▼                   │
    ┌──────────┐        ┌──────────┐             │
    │  WAIT    │        │ DELIVER  │◀────────────┘
    │ for user │        │ immediate│
    │ approval │        └────┬─────┘
    └────┬─────┘             │
         │                   ▼
         │              ┌──────────┐
         │              │ Notify   │
         │              │ "Sent to │
         │              │  #chan"  │
         │              └────┬─────┘
         │                   │
         ▼                   ▼
    ┌──────────────────────────────┐
    │         DELIVERED            │
    │  (track outcome in instance) │
    └──────────────────────────────┘
```

---

## Database Schema Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CORE TABLES                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  users ─────────────┬────────────────┬──────────────────────────┤
│                     │                │                          │
│                     ▼                ▼                          │
│              deliverables      notifications                    │
│                     │                │                          │
│                     │                │                          │
│                     ▼                │                          │
│         deliverable_instances        │                          │
│                     │                │                          │
│                     │                │                          │
│                     ▼                ▼                          │
│               export_logs    event_trigger_log                  │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  deliverables                    │ notifications                │
│  ─────────────                   │ ─────────────                │
│  id                              │ id                           │
│  user_id                         │ user_id                      │
│  title                           │ message                      │
│  prompt                          │ channel                      │
│  destinations[]                  │ urgency                      │
│  governance (manual/semi/full)   │ source_type                  │
│  trigger_type (schedule/event)   │ source_id                    │
│  trigger_config                  │ status                       │
│  status                          │ context                      │
│                                  │                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  deliverable_instances           │ event_trigger_log            │
│  ─────────────────────           │ ─────────────────            │
│  id                              │ id                           │
│  deliverable_id                  │ user_id                      │
│  status (pending/staged/...)     │ deliverable_id               │
│  content                         │ monitor_id                   │
│  trigger_context                 │ platform                     │
│                                  │ event_type                   │
│                                  │ cooldown_key                 │
│                                  │ triggered_at                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## TP Tool Decision Tree

> **Updated for ADR-065 (2026-02-19)**: Live platform tools are primary. `get_sync_status` is NOT in TP's tool list. Sync is async — TP hands off to the user rather than polling.

```
User asks about platform content
              │
              ▼
     ┌────────────────────┐
     │ Is platform        │
     │ connected?         │
     └─────────┬──────────┘
               │
    ┌──────────┴──────────┐
    │ NO                  │ YES
    ▼                     ▼
┌────────────┐    ┌──────────────────────────┐
│ Suggest    │    │ Call live platform tool  │
│ connecting │    │ directly (primary path)  │
│ in Settings│    │                          │
└────────────┘    │ platform_slack_*         │
                  │ platform_gmail_*         │
                  │ platform_notion_*        │
                  └─────────────┬────────────┘
                                │
                   ┌────────────┴────────────┐
                   │ RESULT                  │ CROSS-PLATFORM /
                   │ RETURNED                │ LIVE TOOL FAILED
                   ▼                         ▼
          ┌─────────────┐        ┌───────────────────────┐
          │ Summarize   │        │ Search(scope=          │
          │ for user    │        │ "platform_content")    │
          └─────────────┘        │ [cache fallback]       │
                                 └───────────┬────────────┘
                                             │
                              ┌──────────────┴─────────────┐
                              │ RESULTS                     │ EMPTY
                              ▼                             ▼
                   ┌────────────────────┐    ┌─────────────────────────┐
                   │ Respond, disclose  │    │ Execute(platform.sync)  │
                   │ cache age:         │    │ + tell user:            │
                   │ "Based on sync     │    │ "Syncing now, ~30–60s.  │
                   │ from Feb 18..."    │    │ Ask again once done."   │
                   └────────────────────┘    │ → STOP                  │
                                             └─────────────────────────┘
```
