'use client';

/**
 * Connection Details Modal
 *
 * Displays detailed connection information for a platform integration.
 * Allows reconnection and disconnection without leaving the context page.
 */

import { useState } from 'react';
import {
  X,
  Check,
  RefreshCw,
  LogOut,
  AlertCircle,
  Calendar,
  User,
  Shield,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import { api } from '@/lib/api/client';

interface ConnectionDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  integration: {
    id: string;
    provider: string;
    status: string;
    workspace_name: string | null;
    created_at: string;
    last_used_at: string | null;
    metadata?: {
      email?: string;
      name?: string;
      team_id?: string;
      workspace_id?: string;
      authed_user_id?: string;
      [key: string]: unknown;
    };
  };
  platformLabel: string;
  platformIcon: React.ReactNode;
  onDisconnect?: () => void;
  tierInfo?: {
    tier: string;
    sync_frequency: string;
    next_sync?: string | null;
  };
}

export function ConnectionDetailsModal({
  isOpen,
  onClose,
  integration,
  platformLabel,
  platformIcon,
  onDisconnect,
  tierInfo,
}: ConnectionDetailsModalProps) {
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDisconnect = async () => {
    if (!confirm(`Disconnect ${platformLabel}? You'll need to reconnect to use ${platformLabel} context again.`)) {
      return;
    }

    setIsDisconnecting(true);
    setError(null);

    try {
      await api.integrations.disconnect(integration.provider);
      onDisconnect?.();
      onClose();
    } catch (err) {
      console.error('Failed to disconnect:', err);
      setError(err instanceof Error ? err.message : 'Failed to disconnect');
    } finally {
      setIsDisconnecting(false);
    }
  };

  const handleReconnect = async () => {
    setIsReconnecting(true);
    setError(null);

    try {
      const { authorization_url } = await api.integrations.getAuthorizationUrl(integration.provider);
      // Redirect to OAuth
      window.location.href = authorization_url;
    } catch (err) {
      console.error('Failed to get authorization URL:', err);
      setError(err instanceof Error ? err.message : 'Failed to reconnect');
      setIsReconnecting(false);
    }
  };

  const syncFrequencyLabels: Record<string, string> = {
    '1x_daily': 'Daily (8am)',
    '2x_daily': '2x daily (8am, 6pm)',
    '4x_daily': '4x daily (every 6 hours)',
    'hourly': 'Hourly',
  };

  const formatNextSync = (isoString: string | null | undefined) => {
    if (!isoString) return null;
    try {
      return formatDistanceToNow(new Date(isoString), { addSuffix: true });
    } catch {
      return null;
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-background border border-border rounded-lg shadow-lg w-full max-w-md max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 flex items-center justify-center">
              {platformIcon}
            </div>
            <h3 className="font-semibold text-foreground">{platformLabel} Connection</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-muted rounded transition-colors"
          >
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-8rem)]">
          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
                <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
              </div>
            </div>
          )}

          <div className="space-y-6">
            {/* Workspace Info */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Check className="w-4 h-4 text-green-500" />
                <span className="text-sm font-medium text-foreground">Connected</span>
              </div>
              {integration.workspace_name && (
                <p className="text-lg font-semibold text-foreground">{integration.workspace_name}</p>
              )}
              <p className="text-sm text-muted-foreground">
                Connected {formatDistanceToNow(new Date(integration.created_at), { addSuffix: true })}
              </p>
            </div>

            {/* Sync Status */}
            {tierInfo && (
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <RefreshCw className="w-4 h-4 text-muted-foreground" />
                  <span className="text-sm font-medium text-foreground">Sync Status</span>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Frequency</span>
                    <span className="text-foreground">
                      {syncFrequencyLabels[tierInfo.sync_frequency] || tierInfo.sync_frequency}
                    </span>
                  </div>
                  {tierInfo.next_sync && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Next sync</span>
                      <span className="text-foreground">
                        {formatNextSync(tierInfo.next_sync)}
                      </span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Plan</span>
                    <span className="text-foreground capitalize">{tierInfo.tier}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Connected Account */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <User className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium text-foreground">Connected Account</span>
              </div>
              <div className="space-y-2 text-sm">
                {integration.metadata?.email && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Email</span>
                    <span className="text-foreground">{integration.metadata.email}</span>
                  </div>
                )}
                {integration.metadata?.name && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Name</span>
                    <span className="text-foreground">{integration.metadata.name}</span>
                  </div>
                )}
                {integration.metadata?.authed_user_id && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">User ID</span>
                    <span className="text-foreground font-mono text-xs">
                      {integration.metadata.authed_user_id}
                    </span>
                  </div>
                )}
                {integration.metadata?.workspace_id && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Workspace ID</span>
                    <span className="text-foreground font-mono text-xs">
                      {integration.metadata.workspace_id}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Permissions */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Shield className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm font-medium text-foreground">Permissions</span>
              </div>
              <div className="space-y-1.5 text-sm">
                {getPermissionsForProvider(integration.provider).map((permission) => (
                  <div key={permission} className="flex items-center gap-2">
                    <Check className="w-3 h-3 text-green-500 shrink-0" />
                    <span className="text-muted-foreground">{permission}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-border flex items-center justify-between gap-3">
          <button
            onClick={handleReconnect}
            disabled={isReconnecting || isDisconnecting}
            className="flex items-center gap-2 px-4 py-2 text-sm text-muted-foreground hover:text-foreground disabled:opacity-50"
          >
            {isReconnecting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Reconnect
          </button>
          <button
            onClick={handleDisconnect}
            disabled={isDisconnecting || isReconnecting}
            className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-md text-sm font-medium disabled:opacity-50"
          >
            {isDisconnecting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <LogOut className="w-4 h-4" />
            )}
            Disconnect
          </button>
        </div>
      </div>
    </div>
  );
}

function getPermissionsForProvider(provider: string): string[] {
  switch (provider) {
    case 'slack':
      return [
        'Read channels',
        'Read messages',
        'Read user profiles',
        'Write messages (for deliverables)',
      ];
    case 'gmail':
      return [
        'Read email labels',
        'Read email messages',
        'Create drafts',
        'Read calendar events',
      ];
    case 'notion':
      return [
        'Read pages',
        'Read databases',
        'Create comments',
        'Create pages',
      ];
    case 'calendar':
      return [
        'Read calendar events',
        'Create calendar events',
        'Update calendar events',
      ];
    default:
      return ['Full access to connected workspace'];
  }
}