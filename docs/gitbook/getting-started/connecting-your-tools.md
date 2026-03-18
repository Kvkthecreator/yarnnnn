# Connecting Your Tools

YARNNN becomes useful by staying connected to the places where your work already happens.

## What happens when you connect a tool

1. You authorize YARNNN through the platform's OAuth flow
2. YARNNN gets read-only access
3. It discovers the available sources on that platform
4. It applies smart default coverage for the first sync
5. You can refine that coverage later if needed

The important shift is this: connection is not supposed to dump you into a long manual setup flow. It is supposed to move you quickly toward first value.

## What each platform adds

### Slack

YARNNN can:

- summarize team discussion
- track ongoing themes and blockers
- answer questions about what happened in selected channels

Best starting use cases:

- engineering recap
- product watch
- cross-team weekly summary

### Gmail

YARNNN can:

- summarize important email threads
- pull client or stakeholder context into agents
- combine inbox context with Slack, Notion, and Calendar

Best starting use cases:

- client communication digest
- inbox summary
- stakeholder status synthesis

### Notion

YARNNN can:

- reference docs and databases in grounded responses
- build status or research output from written project context
- combine formal docs with conversations from other platforms

Best starting use cases:

- project summary
- research brief
- status update grounded in current documentation

### Google Calendar

YARNNN can:

- generate meeting prep
- answer schedule-aware questions
- use upcoming events as timing context for other work

Calendar is especially useful when paired with Slack and Gmail.

## Refining coverage later

After the first sync, go to the Context area if you want to:

- add or remove Slack channels
- change Gmail labels
- narrow or expand Notion page coverage
- disconnect a platform entirely

The best pattern is to start with the defaults, judge the first result, then tighten only where needed.

## Security and privacy

- integrations are read-only
- data is encrypted in transit and at rest
- OAuth tokens are encrypted at rest
- your data is isolated to your account
- you can disconnect any integration at any time
