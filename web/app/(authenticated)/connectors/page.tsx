'use client';

/**
 * Connectors — atomic Connectors surface (ADR-297 D19.4).
 *
 * D19.4 (2026-05-22) refactor: window-shaped per the OS metaphor.
 * Promoted from legacy page to atomic kernel surface (15th content
 * surface). Reverses D19.7 — Connectors lives inside the authenticated
 * workspace as a window on the Desktop, NOT as a page that erases the
 * workspace. Pre-D19.4 chrome (PageHeader + useBreadcrumb) DELETED;
 * the WindowFrame title bar is now the only chrome.
 *
 * Connectors is the operator's view of platform integrations:
 * Slack, Notion, GitHub, Lemon Squeezy, Alpaca. Live OAuth state,
 * sync status, per-platform substrate. Operator declined the
 * "fold into Settings as a tab" option (D19.4 §D19.4.2) — integrations
 * are workspace-level concerns more than account-shaped preferences,
 * earning their own atomic surface.
 */

import { ConnectedIntegrationsSection } from '@/components/settings/ConnectedIntegrationsSection';

export default function ConnectorsPage() {
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6">
        <ConnectedIntegrationsSection
          title="Connectors"
          description="Connect platforms to give your agents data. Platforms are infrastructure — connect once, agents read automatically."
          redirectTo="/connectors"
        />
      </div>
    </div>
  );
}
