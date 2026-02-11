"use client";

import { useState, useEffect, useCallback } from "react";
import {
  X,
  Loader2,
  Search,
  Check,
  AlertTriangle,
  Hash,
  Tag,
  FileText,
  Lock,
  Calendar,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { cn } from "@/lib/utils";

type Provider = "slack" | "gmail" | "notion" | "google" | "calendar";

interface Source {
  id: string;
  name: string;
  resource_type: string;
  metadata?: {
    member_count?: number;
    message_count?: number;
    is_private?: boolean;
  };
}

interface SourceSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  provider: Provider;
}

const PROVIDER_CONFIG: Record<
  Provider,
  {
    label: string;
    resourceLabel: string;
    resourceLabelPlural: string;
    icon: React.ReactNode;
    limitField: "slack_channels" | "gmail_labels" | "notion_pages";
  }
> = {
  slack: {
    label: "Slack",
    resourceLabel: "Channel",
    resourceLabelPlural: "Channels",
    icon: <Hash className="w-4 h-4" />,
    limitField: "slack_channels",
  },
  gmail: {
    label: "Gmail",
    resourceLabel: "Label",
    resourceLabelPlural: "Labels",
    icon: <Tag className="w-4 h-4" />,
    limitField: "gmail_labels",
  },
  notion: {
    label: "Notion",
    resourceLabel: "Page",
    resourceLabelPlural: "Pages",
    icon: <FileText className="w-4 h-4" />,
    limitField: "notion_pages",
  },
  google: {
    label: "Google",
    resourceLabel: "Calendar",
    resourceLabelPlural: "Calendars",
    icon: <Calendar className="w-4 h-4" />,
    limitField: "gmail_labels", // Placeholder until calendar limits added
  },
  calendar: {
    label: "Calendar",
    resourceLabel: "Calendar",
    resourceLabelPlural: "Calendars",
    icon: <Calendar className="w-4 h-4" />,
    limitField: "gmail_labels", // Placeholder until calendar limits added
  },
};

/**
 * ADR-043: Source Selection Modal
 *
 * Allows users to select which sources (channels/labels/pages)
 * to sync for a platform, with limit enforcement.
 */
export function SourceSelectionModal({
  isOpen,
  onClose,
  onSuccess,
  provider,
}: SourceSelectionModalProps) {
  const [availableSources, setAvailableSources] = useState<Source[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [originalIds, setOriginalIds] = useState<Set<string>>(new Set());
  const [limit, setLimit] = useState<number>(5);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const config = PROVIDER_CONFIG[provider];

  // Load available sources and current selection
  useEffect(() => {
    if (isOpen) {
      loadSources();
    }
  }, [isOpen, provider]);

  const loadSources = async () => {
    setLoading(true);
    setError(null);

    try {
      // Load landscape (all available sources) and limits in parallel
      const [landscapeResult, limitsResult] = await Promise.all([
        api.integrations.getLandscape(provider),
        api.integrations.getLimits(),
      ]);

      // Extract sources from landscape
      const sources = landscapeResult.resources.map((r) => ({
        id: r.id,
        name: r.name,
        resource_type: r.resource_type,
        metadata: r.metadata as Source["metadata"],
      }));
      setAvailableSources(sources);

      // Get current selection from sources endpoint
      const sourcesResult = await api.integrations.getSources(provider);
      const currentIds = new Set(sourcesResult.sources.map((s) => s.id));
      setSelectedIds(currentIds);
      setOriginalIds(currentIds);

      // Set limit from tier
      const tierLimit = limitsResult.limits[config.limitField];
      setLimit(tierLimit);
    } catch (err) {
      console.error("Failed to load sources:", err);
      setError("Failed to load available sources");
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = (sourceId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(sourceId)) {
        next.delete(sourceId);
      } else {
        // Only add if under limit
        if (next.size < limit) {
          next.add(sourceId);
        }
      }
      return next;
    });
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      const result = await api.integrations.updateSources(
        provider,
        Array.from(selectedIds)
      );

      if (result.success) {
        onSuccess();
        onClose();
      } else {
        setError(result.message || "Failed to update sources");
      }
    } catch (err) {
      console.error("Failed to save sources:", err);
      setError("Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    // Reset to original selection
    setSelectedIds(originalIds);
    setSearchQuery("");
    onClose();
  };

  // Filter sources by search query
  const filteredSources = searchQuery
    ? availableSources.filter((s) =>
        s.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : availableSources;

  // Separate selected and available
  const selectedSources = filteredSources.filter((s) => selectedIds.has(s.id));
  const unselectedSources = filteredSources.filter(
    (s) => !selectedIds.has(s.id)
  );

  const atLimit = selectedIds.size >= limit;
  const hasChanges =
    selectedIds.size !== originalIds.size ||
    !Array.from(selectedIds).every((id) => originalIds.has(id));

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-background rounded-xl shadow-xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div>
            <h2 className="text-lg font-semibold">
              Select {config.resourceLabelPlural}
            </h2>
            <p className="text-sm text-muted-foreground">
              Choose which {config.label} {config.resourceLabelPlural.toLowerCase()} to sync
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {loading ? (
            <div className="flex-1 flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="flex-1 flex flex-col items-center justify-center py-12 px-4">
              <AlertTriangle className="w-8 h-8 text-amber-500 mb-2" />
              <p className="text-sm text-muted-foreground text-center">
                {error}
              </p>
              <button
                onClick={loadSources}
                className="mt-3 text-sm text-primary hover:underline"
              >
                Try again
              </button>
            </div>
          ) : (
            <>
              {/* Search */}
              <div className="p-4 border-b border-border">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder={`Search ${config.resourceLabelPlural.toLowerCase()}...`}
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              </div>

              {/* Selection count & limit warning */}
              <div className="px-4 py-2 bg-muted/30 border-b border-border">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">
                    Selected ({selectedIds.size} of {limit})
                  </span>
                  {atLimit && (
                    <span className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      Limit reached
                    </span>
                  )}
                </div>
              </div>

              {/* Source lists */}
              <div className="flex-1 overflow-y-auto">
                {/* Selected sources */}
                {selectedSources.length > 0 && (
                  <div className="p-2">
                    {selectedSources.map((source) => (
                      <SourceItem
                        key={source.id}
                        source={source}
                        isSelected={true}
                        onToggle={() => handleToggle(source.id)}
                        icon={config.icon}
                        disabled={false}
                      />
                    ))}
                  </div>
                )}

                {/* Divider */}
                {selectedSources.length > 0 && unselectedSources.length > 0 && (
                  <div className="px-4 py-2 border-t border-border">
                    <span className="text-xs text-muted-foreground">
                      Available
                    </span>
                  </div>
                )}

                {/* Available sources */}
                {unselectedSources.length > 0 && (
                  <div className="p-2">
                    {unselectedSources.map((source) => (
                      <SourceItem
                        key={source.id}
                        source={source}
                        isSelected={false}
                        onToggle={() => handleToggle(source.id)}
                        icon={config.icon}
                        disabled={atLimit}
                      />
                    ))}
                  </div>
                )}

                {/* Empty state */}
                {filteredSources.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-12 px-4">
                    <p className="text-sm text-muted-foreground">
                      {searchQuery
                        ? `No ${config.resourceLabelPlural.toLowerCase()} match "${searchQuery}"`
                        : `No ${config.resourceLabelPlural.toLowerCase()} available`}
                    </p>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Limit warning banner */}
        {atLimit && !loading && !error && (
          <div className="px-4 py-3 bg-amber-50 dark:bg-amber-950/30 border-t border-amber-200 dark:border-amber-900">
            <p className="text-sm text-amber-700 dark:text-amber-300">
              You've reached the {limit} {config.resourceLabel.toLowerCase()} limit.
              <span className="ml-1 text-amber-600 dark:text-amber-400">
                Upgrade to Pro for more.
              </span>
            </p>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-border">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            className={cn(
              "px-4 py-2 text-sm rounded-lg transition-colors",
              hasChanges
                ? "bg-primary text-primary-foreground hover:bg-primary/90"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            )}
          >
            {saving ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </span>
            ) : (
              "Save Changes"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Individual source item in the selection list
 */
function SourceItem({
  source,
  isSelected,
  onToggle,
  icon,
  disabled,
}: {
  source: Source;
  isSelected: boolean;
  onToggle: () => void;
  icon: React.ReactNode;
  disabled: boolean;
}) {
  const isPrivate = source.metadata?.is_private;
  const memberCount = source.metadata?.member_count;

  return (
    <button
      onClick={onToggle}
      disabled={disabled && !isSelected}
      className={cn(
        "w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors",
        isSelected
          ? "bg-primary/10 border border-primary/30"
          : disabled
            ? "opacity-50 cursor-not-allowed"
            : "hover:bg-muted border border-transparent"
      )}
    >
      {/* Checkbox */}
      <div
        className={cn(
          "w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0",
          isSelected
            ? "bg-primary border-primary text-primary-foreground"
            : "border-muted-foreground/30"
        )}
      >
        {isSelected && <Check className="w-3 h-3" />}
      </div>

      {/* Icon */}
      <span className="text-muted-foreground flex-shrink-0">{icon}</span>

      {/* Name and metadata */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{source.name}</span>
          {isPrivate && (
            <Lock className="w-3 h-3 text-muted-foreground flex-shrink-0" />
          )}
        </div>
        {memberCount !== undefined && (
          <span className="text-xs text-muted-foreground">
            {memberCount.toLocaleString()} members
          </span>
        )}
      </div>
    </button>
  );
}

export default SourceSelectionModal;
