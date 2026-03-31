'use client';

import { FileText } from 'lucide-react';

interface PlatformContextFeedProps {
  platform: string;
  selectedResourceIds?: string[];
  sourceLabel?: string;
}

/**
 * ADR-153: Platform content sunset.
 * Platform data now flows through tasks into workspace context domains.
 * This component shows a deprecation notice.
 */
export function PlatformContextFeed({
  platform,
  sourceLabel = 'sources',
}: PlatformContextFeedProps) {
  return (
    <div className="border border-dashed border-border rounded-lg p-8 text-center">
      <FileText className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
      <p className="text-sm font-medium text-muted-foreground">
        Platform context has moved to tasks
      </p>
      <p className="text-xs text-muted-foreground mt-1">
        Create a monitoring task to track {platform} {sourceLabel} and build context automatically.
      </p>
    </div>
  );
}
