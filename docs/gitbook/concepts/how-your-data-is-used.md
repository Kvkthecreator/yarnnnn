# How Your Data Is Used

YARNNN connects to your work tools to provide context-aware AI. Here's exactly what happens with your data.

## What YARNNN reads

| Platform | What's accessed | What's NOT accessed |
|---|---|---|
| **Slack** | Messages from channels you select | DMs, channels you don't select |
| **Gmail** | Emails from labels you select | Drafts, attachments, labels you don't select |
| **Notion** | Pages and databases you select | Pages you don't select |
| **Calendar** | Upcoming events (next 7 days) | Historical events |

**You control exactly what YARNNN can see.** Nothing is synced without your explicit selection.

## What YARNNN does with your data

### Powers the AI assistant

When you ask a question, the assistant searches your synced content to give you answers grounded in your actual work — not generic internet results.

### Produces deliverables

When a deliverable runs (e.g., your weekly digest), YARNNN reads the relevant synced content and generates a draft.

### Learns your preferences

YARNNN extracts preferences from your interactions (like "prefers bullet points") and stores them so it can personalize future output. You can review and edit these anytime.

## What YARNNN does NOT do

- **Never posts or sends anything** on your behalf in Slack, Gmail, or Notion
- **Never shares your data** with other users
- **Never trains external AI models** on your data
- **Never accesses content** you haven't explicitly selected
- **Never stores your OAuth passwords** — only encrypted access tokens

## Data retention

Your synced content is kept as long as it's useful:

- Content actively used by deliverables or the AI assistant is kept long-term
- Content that's never referenced naturally expires
- When you disconnect a platform, syncing stops and content expires on its own

## Your controls

| Action | How |
|---|---|
| See what's synced | **Context** page shows all connected sources |
| Change what's synced | Update source selection per platform |
| Delete preferences | Edit or remove from the **Context** page |
| Disconnect a platform | One-click disconnect from the **Context** page |
| Delete your account | Contact support — all data is permanently removed |

## Security

- All data is encrypted in transit and at rest
- OAuth tokens are encrypted with industry-standard encryption
- Your data is isolated — no other user can access it
- YARNNN uses row-level security to scope all queries to your account
- You can revoke platform access at any time
