'use client';

/**
 * ExportActionBar - Export deliverable versions to connected integrations
 *
 * Shows available export destinations (Slack, Notion) for approved versions.
 * Displays inline after approval or in the deliverable detail view.
 */

import { useState, useEffect } from 'react';
import {
  Loader2,
  Check,
  ExternalLink,
  Link2,
  AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api/client';

interface Integration {
  id: string;
  provider: string;
  status: string;
  workspace_name: string | null;
}

interface ExportActionBarProps {
  deliverableVersionId: string;
  deliverableTitle: string;
  onExportComplete?: (provider: string, url?: string) => void;
}

// Slack and Notion brand icons as inline SVGs
const SlackIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
  </svg>
);

const NotionIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.98-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466l1.823 1.447zm.793 3.08v13.904c0 .747.373 1.027 1.213.98l14.523-.84c.84-.046.934-.56.934-1.166V6.354c0-.606-.234-.933-.746-.886l-15.177.887c-.56.046-.747.326-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952l1.448.327s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.513.28-.886.747-.933l3.222-.187zM2.87.119l13.449-.933c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.046-1.448-.093-1.962-.747L1.945 18.79c-.56-.747-.793-1.306-.793-1.958V2.005C1.152.933 1.525.212 2.87.119z"/>
  </svg>
);

export function ExportActionBar({
  deliverableVersionId,
  deliverableTitle,
  onExportComplete,
}: ExportActionBarProps) {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportSuccess, setExportSuccess] = useState<{ provider: string; url?: string } | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    loadIntegrations();
  }, []);

  const loadIntegrations = async () => {
    try {
      const result = await api.integrations.list();
      // Filter to only active integrations
      setIntegrations(result.integrations.filter((i: Integration) => i.status === 'active'));
    } catch (err) {
      console.error('Failed to load integrations:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (provider: string) => {
    setExporting(provider);
    setExportError(null);

    try {
      // For now, we need to select a destination
      // In a full implementation, we'd show a destination picker modal
      // For MVP, we'll use a simple prompt or default destination

      let destination: Record<string, string> = {};

      if (provider === 'slack') {
        // For MVP: prompt for channel ID
        // In production: show channel picker
        const channelId = prompt('Enter Slack channel ID (e.g., C1234567890):');
        if (!channelId) {
          setExporting(null);
          return;
        }
        destination = { channel_id: channelId };
      } else if (provider === 'notion') {
        // For MVP: prompt for page ID
        // In production: show page picker
        const pageId = prompt('Enter Notion page ID:');
        if (!pageId) {
          setExporting(null);
          return;
        }
        destination = { page_id: pageId };
      }

      const result = await api.integrations.export(provider, {
        deliverable_version_id: deliverableVersionId,
        destination,
      });

      if (result.status === 'success') {
        setExportSuccess({ provider, url: result.external_url });
        onExportComplete?.(provider, result.external_url);
      } else {
        setExportError(result.error_message || 'Export failed');
      }
    } catch (err) {
      console.error(`Export to ${provider} failed:`, err);
      setExportError('Export failed. Please try again.');
    } finally {
      setExporting(null);
    }
  };

  // Don't render if no integrations connected
  if (loading) {
    return null; // Don't show anything while loading
  }

  if (integrations.length === 0) {
    return null; // No integrations connected
  }

  // Show success state
  if (exportSuccess) {
    return (
      <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
        <Check className="w-4 h-4 text-green-600" />
        <span className="text-sm text-green-800 dark:text-green-200">
          Exported to {exportSuccess.provider}
        </span>
        {exportSuccess.url && (
          <a
            href={exportSuccess.url}
            target="_blank"
            rel="noopener noreferrer"
            className="ml-auto text-xs text-green-700 dark:text-green-300 hover:underline flex items-center gap-1"
          >
            View <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    );
  }

  return (
    <div className="border border-border rounded-lg p-3">
      <div className="flex items-center gap-2 mb-2">
        <Link2 className="w-4 h-4 text-muted-foreground" />
        <span className="text-sm font-medium">Export to</span>
      </div>

      {exportError && (
        <div className="flex items-center gap-2 mb-2 text-xs text-red-600">
          <AlertCircle className="w-3 h-3" />
          {exportError}
        </div>
      )}

      <div className="flex items-center gap-2">
        {integrations.map((integration) => {
          const isSlack = integration.provider === 'slack';
          const isNotion = integration.provider === 'notion';
          const isExporting = exporting === integration.provider;

          return (
            <button
              key={integration.id}
              onClick={() => handleExport(integration.provider)}
              disabled={!!exporting}
              className={`
                inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md
                border border-border hover:bg-muted disabled:opacity-50
                ${isExporting ? 'bg-muted' : ''}
              `}
            >
              {isExporting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : isSlack ? (
                <SlackIcon className="w-3.5 h-3.5" />
              ) : isNotion ? (
                <NotionIcon className="w-3.5 h-3.5" />
              ) : (
                <ExternalLink className="w-3.5 h-3.5" />
              )}
              {isSlack ? 'Slack' : isNotion ? 'Notion' : integration.provider}
              {integration.workspace_name && (
                <span className="text-muted-foreground">
                  ({integration.workspace_name})
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
