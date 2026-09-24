'use client';

/**
 * StartMark — a start's face, resolved the way every other connector surface
 * resolves one.
 *
 * ⚠️ A START'S `connector` IS A PLATFORM KEY (`slack` · `notion` · `github`),
 * not a URL and not a directory key — `_CONNECTOR_STARTS` in
 * `api/routes/standing_work.py` is keyed by the capture binding's platform.
 * That matters because the two resolvers take different inputs:
 *
 *   `connectorIdentity({url})`  → matches `DOMAIN_MARKS` by HOST.
 *   `connectorMeta(provider)`   → matches `CONNECTOR_REGISTRY` by PLATFORM.
 *
 * A first cut passed `connectorKey={s.connector}` to `ConnectorAvatar`, which
 * routes to `KEY_MARKS` — **an empty table**. It typechecked, built, and
 * rendered a derived LETTERMARK ("S" on a hashed tone) beside a card titled
 * "Keep a brief of your Slack channels current". Nothing failed; the member
 * simply never saw the Slack mark that the registry has held all along. So:
 * the platform key goes through `connectorMeta` → `override={meta.brand}`,
 * which is the same path Reach and the finder take (`ReachConnected.tsx:315`,
 * `FindConnectorModal.tsx:539`). One connector, one face, everywhere.
 *
 * A start with no connector (a web page, a workspace path) has no brand to
 * wear and takes a neutral chip carrying its own kind's glyph — honest rather
 * than a fabricated mark (`lib/connectors/marks.tsx` header).
 */

import { FolderOpen, Globe, Link2 } from 'lucide-react';
import { ConnectorAvatar } from '@/components/connectors/ConnectorAvatar';
import { connectorMeta } from '@/lib/connectors/registry';
import type { StandingStart } from '@/lib/api/client';
import { cn } from '@/lib/utils';

export function StartMark({ start, className }: { start: StandingStart; className?: string }) {
  if (start.connector) {
    const meta = connectorMeta(start.connector);
    return (
      <ConnectorAvatar
        size="sm"
        title={start.name}
        connectorKey={start.connector}
        override={meta ? meta.brand : undefined}
        className={className}
      />
    );
  }
  const Glyph = start.kind === 'path' ? FolderOpen : start.kind === 'browser' ? Globe : Link2;
  return (
    <span
      aria-hidden
      className={cn(
        'flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border/60 bg-muted/30',
        className,
      )}
    >
      <Glyph className="h-3.5 w-3.5 text-muted-foreground" />
    </span>
  );
}
