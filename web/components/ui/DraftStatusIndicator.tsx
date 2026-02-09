'use client';

/**
 * DraftStatusIndicator - ADR-032 Phase 2
 *
 * Shows where a draft was pushed after a version is approved.
 * Platform-centric drafts: drafts live in Gmail Drafts, Slack DMs, Notion Drafts DB.
 */

import {
  Mail,
  Slack,
  FileCode,
  Download,
  ExternalLink,
  CheckCircle2,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { DeliverableVersion, Destination } from '@/types';

interface DraftStatusIndicatorProps {
  version: DeliverableVersion;
  destination?: Destination;
  className?: string;
}

const PLATFORM_CONFIG: Record<string, {
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
  getDraftLocation: (format?: string, target?: string) => string;
  getDeepLink?: (externalUrl?: string, externalId?: string) => string | null;
}> = {
  gmail: {
    icon: Mail,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    getDraftLocation: () => 'Gmail Drafts folder',
    getDeepLink: () => 'https://mail.google.com/mail/u/0/#drafts',
  },
  slack: {
    icon: Slack,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    getDraftLocation: (format, target) =>
      format === 'dm_draft'
        ? `DM with draft for ${target || 'channel'}`
        : `Posted to ${target || 'channel'}`,
    getDeepLink: (externalUrl) => externalUrl || null,
  },
  notion: {
    icon: FileCode,
    color: 'text-gray-700',
    bgColor: 'bg-gray-100',
    getDraftLocation: (format) =>
      format === 'draft'
        ? 'YARNNN Drafts database'
        : 'Created in target location',
    getDeepLink: (externalUrl) => externalUrl || null,
  },
  download: {
    icon: Download,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    getDraftLocation: () => 'Available for download',
    getDeepLink: (externalUrl) => externalUrl || null,
  },
};

type DeliveryStatus = 'pending' | 'delivering' | 'delivered' | 'failed';

export function DraftStatusIndicator({
  version,
  destination,
  className,
}: DraftStatusIndicatorProps) {
  if (!destination) {
    return null;
  }

  const platform = destination.platform;
  const config = PLATFORM_CONFIG[platform];

  if (!config) {
    return null;
  }

  const Icon = config.icon;
  const deliveryStatus = (version.delivery_status || 'pending') as DeliveryStatus;
  const deliveryMode = version.delivery_mode;

  // Only show for draft mode deliveries
  if (deliveryMode !== 'draft' && deliveryStatus !== 'delivered') {
    return null;
  }

  const draftLocation = config.getDraftLocation(destination.format, destination.target);
  const deepLink = config.getDeepLink?.(
    version.delivery_external_url || undefined,
    version.delivery_external_id || undefined
  );

  // Status-specific rendering
  if (deliveryStatus === 'pending') {
    return (
      <div className={cn(
        "flex items-center gap-2 p-3 rounded-lg border border-border bg-muted/30",
        className
      )}>
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          Preparing draft for {platform}...
        </span>
      </div>
    );
  }

  if (deliveryStatus === 'delivering') {
    return (
      <div className={cn(
        "flex items-center gap-2 p-3 rounded-lg border border-border bg-muted/30",
        className
      )}>
        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          Creating draft in {platform}...
        </span>
      </div>
    );
  }

  if (deliveryStatus === 'failed') {
    return (
      <div className={cn(
        "flex items-center gap-2 p-3 rounded-lg border border-red-200 bg-red-50",
        className
      )}>
        <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium text-red-700">
            Draft delivery failed
          </span>
          {version.delivery_error && (
            <p className="text-xs text-red-600 mt-0.5 truncate">
              {version.delivery_error}
            </p>
          )}
        </div>
      </div>
    );
  }

  // Delivered state
  return (
    <div className={cn(
      "flex items-center gap-3 p-3 rounded-lg border",
      config.bgColor,
      "border-transparent",
      className
    )}>
      <div className={cn("shrink-0", config.color)}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <CheckCircle2 className="w-3.5 h-3.5 text-green-600 shrink-0" />
          <span className="text-sm font-medium">Draft ready</span>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">
          {draftLocation}
        </p>
      </div>
      {deepLink && (
        <a
          href={deepLink}
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            "flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors",
            "bg-background hover:bg-muted border border-border",
            config.color
          )}
        >
          Open
          <ExternalLink className="w-3 h-3" />
        </a>
      )}
    </div>
  );
}

/**
 * Compact version for list views
 */
export function DraftStatusBadge({
  version,
  destination,
}: {
  version: DeliverableVersion;
  destination?: Destination;
}) {
  if (!destination) return null;

  const platform = destination.platform;
  const config = PLATFORM_CONFIG[platform];
  if (!config) return null;

  const Icon = config.icon;
  const deliveryStatus = (version.delivery_status || 'pending') as DeliveryStatus;

  if (deliveryStatus === 'delivered') {
    return (
      <div className="flex items-center gap-1.5 text-xs">
        <Icon className={cn("w-3.5 h-3.5", config.color)} />
        <span className="text-muted-foreground">Draft ready</span>
      </div>
    );
  }

  if (deliveryStatus === 'delivering' || deliveryStatus === 'pending') {
    return (
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        <span>Creating draft...</span>
      </div>
    );
  }

  if (deliveryStatus === 'failed') {
    return (
      <div className="flex items-center gap-1.5 text-xs text-red-600">
        <AlertCircle className="w-3.5 h-3.5" />
        <span>Draft failed</span>
      </div>
    );
  }

  return null;
}
