"use client";

import { useState, useEffect, useCallback } from "react";
import {
  X,
  Loader2,
  Download,
  Hash,
  FileText,
  Check,
  AlertTriangle,
  RefreshCw,
  Lock,
  Circle,
  CheckCircle2,
  Clock,
  EyeOff,
  ChevronDown,
  ChevronUp,
  Settings2,
  Brain,
  MessageSquare,
  ArrowRight,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { useRouter } from "next/navigation";
import { useDesk } from "@/contexts/DeskContext";
import { HOME_LABEL, HOME_ROUTE } from "@/lib/routes";

type Provider = "slack" | "notion" | "gmail" | "calendar";
type CoverageState = "uncovered" | "partial" | "covered" | "stale" | "excluded";

const getApiProvider = (provider: Provider): Provider => {
  return provider;
};

// ADR-030: Landscape resource with coverage state
interface LandscapeResource {
  id: string;
  name: string;
  resource_type: string;
  coverage_state: CoverageState;
  last_extracted_at: string | null;
  items_extracted: number;
  metadata: Record<string, unknown>;
}

interface CoverageSummary {
  total_resources: number;
  covered_count: number;
  partial_count: number;
  stale_count: number;
  uncovered_count: number;
  excluded_count: number;
  coverage_percentage: number;
}

// ADR-030: Progress details for real-time tracking
interface ProgressDetails {
  phase: "fetching" | "processing" | "storing";
  items_total: number;
  items_completed: number;
  current_resource: string | null;
  updated_at: string;
}

interface ImportJob {
  id: string;
  provider: string;
  resource_id: string;
  resource_name: string | null;
  status: string;
  progress: number;
  progress_details: ProgressDetails | null;
  result: {
    blocks_created: number;
    items_processed: number;
    items_filtered: number;
    summary: string;
    style_learned?: boolean;
    style_confidence?: string;
  } | null;
  error_message: string | null;
}

// ADR-030: Scope configuration
interface ImportScope {
  recency_days: number;
  max_items: number;
}

interface IntegrationImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  provider: Provider;
  /** Optional: Called when user clicks "View Context" after import */
  onNavigateToContext?: () => void;
}

/**
 * Coverage state indicator component.
 * ADR-030: Shows visual indicator for resource coverage state.
 */
function CoverageIndicator({ state, lastExtracted, itemsExtracted }: {
  state: CoverageState;
  lastExtracted: string | null;
  itemsExtracted: number;
}) {
  const config: Record<CoverageState, { icon: React.ReactNode; color: string; label: string }> = {
    uncovered: {
      icon: <Circle className="w-3 h-3" />,
      color: "text-muted-foreground",
      label: "Not imported",
    },
    partial: {
      icon: <Clock className="w-3 h-3" />,
      color: "text-amber-500",
      label: `${itemsExtracted} items`,
    },
    covered: {
      icon: <CheckCircle2 className="w-3 h-3" />,
      color: "text-green-500",
      label: `${itemsExtracted} items`,
    },
    stale: {
      icon: <Clock className="w-3 h-3" />,
      color: "text-orange-500",
      label: "Needs refresh",
    },
    excluded: {
      icon: <EyeOff className="w-3 h-3" />,
      color: "text-muted-foreground",
      label: "Excluded",
    },
  };

  const { icon, color, label } = config[state];

  return (
    <div className={`flex items-center gap-1 text-xs ${color}`}>
      {icon}
      <span>{label}</span>
      {lastExtracted && state !== "uncovered" && state !== "excluded" && (
        <span className="text-muted-foreground">
          · {new Date(lastExtracted).toLocaleDateString()}
        </span>
      )}
    </div>
  );
}

/**
 * Coverage summary bar component.
 * ADR-030: Shows overall coverage percentage.
 */
function CoverageSummaryBar({ summary }: { summary: CoverageSummary }) {
  const percentage = summary.coverage_percentage || 0;

  return (
    <div className="mb-4 p-3 bg-muted/30 rounded-lg border border-border">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">Coverage</span>
        <span className="text-sm text-muted-foreground">
          {Math.round(percentage)}% ({summary.covered_count + summary.partial_count} of {summary.total_resources - summary.excluded_count})
        </span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
        {summary.covered_count > 0 && (
          <span className="flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-green-500" />
            {summary.covered_count} covered
          </span>
        )}
        {summary.partial_count > 0 && (
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3 text-amber-500" />
            {summary.partial_count} partial
          </span>
        )}
        {summary.stale_count > 0 && (
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3 text-orange-500" />
            {summary.stale_count} stale
          </span>
        )}
        {summary.uncovered_count > 0 && (
          <span className="flex items-center gap-1">
            <Circle className="w-3 h-3" />
            {summary.uncovered_count} new
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * Scope configuration component.
 * ADR-030: Allows user to configure extraction scope.
 */
function ScopeConfiguration({ scope, onChange, provider }: {
  scope: ImportScope;
  onChange: (scope: ImportScope) => void;
  provider: Provider;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  const recencyOptions = [
    { value: 7, label: "Last 7 days" },
    { value: 14, label: "Last 14 days" },
    { value: 30, label: "Last 30 days" },
    { value: 90, label: "Last 90 days" },
  ];

  const maxItemsOptions = provider === "notion"
    ? [
        { value: 5, label: "5 pages" },
        { value: 10, label: "10 pages" },
        { value: 25, label: "25 pages" },
        { value: 50, label: "50 pages" },
      ]
    : [
        { value: 50, label: "50 items" },
        { value: 100, label: "100 items" },
        { value: 200, label: "200 items" },
        { value: 500, label: "500 items" },
      ];

  return (
    <div className="mt-4 border border-border rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2 text-sm">
          <Settings2 className="w-4 h-4 text-muted-foreground" />
          <span>Import Settings</span>
          <span className="text-muted-foreground">
            · {recencyOptions.find(o => o.value === scope.recency_days)?.label}, up to {scope.max_items} {provider === "notion" ? "pages" : "items"}
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </button>

      {isExpanded && (
        <div className="p-3 border-t border-border bg-muted/30 space-y-4">
          {/* Recency - only for time-based providers */}
          {provider !== "notion" && (
            <div>
              <label className="block text-xs font-medium text-muted-foreground mb-2">
                Time Range
              </label>
              <div className="flex flex-wrap gap-2">
                {recencyOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => onChange({ ...scope, recency_days: option.value })}
                    className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                      scope.recency_days === option.value
                        ? "bg-primary text-primary-foreground"
                        : "bg-background border border-border hover:bg-muted"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Max items */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-2">
              Maximum {provider === "notion" ? "Pages" : "Items"}
            </label>
            <div className="flex flex-wrap gap-2">
              {maxItemsOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => onChange({ ...scope, max_items: option.value })}
                  className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                    scope.max_items === option.value
                      ? "bg-primary text-primary-foreground"
                      : "bg-background border border-border hover:bg-muted"
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Modal for importing context from connected integrations.
 *
 * ADR-027: Integration Read Architecture - Phase 3 Onboarding UI
 * ADR-030: Context Extraction Methodology - Coverage visibility
 *
 * Flow:
 * 1. Load platform landscape with coverage state
 * 2. User selects resource and configures scope
 * 3. Start import job (async processing)
 * 4. Poll for completion, show result
 */
export function IntegrationImportModal({
  isOpen,
  onClose,
  onSuccess,
  provider,
  onNavigateToContext,
}: IntegrationImportModalProps) {
  const router = useRouter();
  // Try to get desk context (may not be available if rendered outside DeskProvider)
  let deskContext: ReturnType<typeof useDesk> | null = null;
  try {
    deskContext = useDesk();
  } catch {
    // Not in DeskProvider context - navigation will use router instead
  }

  // ADR-030: Landscape with coverage
  const [landscape, setLandscape] = useState<{
    resources: LandscapeResource[];
    coverage_summary: CoverageSummary;
    discovered_at: string | null;
  } | null>(null);
  const [isLoadingResources, setIsLoadingResources] = useState(false);
  const [resourceError, setResourceError] = useState<string | null>(null);

  // Selection state
  const [selectedResource, setSelectedResource] = useState<string | null>(null);
  const [instructions, setInstructions] = useState("");
  const [learnStyle, setLearnStyle] = useState(false);  // ADR-027 Phase 5

  // ADR-030: Scope configuration
  const [scope, setScope] = useState<ImportScope>({
    recency_days: 7,
    max_items: provider === "notion" ? 10 : 100,
  });

  // Gmail-specific state (ADR-029)
  const [gmailImportType, setGmailImportType] = useState<"inbox" | "query">("inbox");
  const [gmailQuery, setGmailQuery] = useState("");

  // Import state
  const [isImporting, setIsImporting] = useState(false);
  const [importJob, setImportJob] = useState<ImportJob | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  // Load landscape when modal opens
  const loadResources = useCallback(async (refresh = false) => {
    // Gmail doesn't need to load resources - uses predefined options
    if (provider === "gmail") {
      setIsLoadingResources(false);
      return;
    }

    setIsLoadingResources(true);
    setResourceError(null);

    try {
      // ADR-030: Use landscape endpoint for coverage data
      // ADR-046: Use API provider for backend calls (calendar → google)
      const apiProvider = getApiProvider(provider);
      const response = await api.integrations.getLandscape(apiProvider, refresh);
      setLandscape({
        resources: response.resources,
        coverage_summary: response.coverage_summary,
        discovered_at: response.discovered_at,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load resources";
      setResourceError(message);
    } finally {
      setIsLoadingResources(false);
    }
  }, [provider]);

  useEffect(() => {
    if (isOpen) {
      loadResources();
    }
  }, [isOpen, loadResources]);

  // Poll for job completion
  useEffect(() => {
    if (!importJob || importJob.status === "completed" || importJob.status === "failed") {
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        const updated = await api.integrations.getImportJob(importJob.id);
        setImportJob(updated);

        if (updated.status === "completed" || updated.status === "failed") {
          clearInterval(pollInterval);
        }
      } catch {
        // Silently retry on poll failure
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [importJob]);

  const handleImport = async () => {
    // Gmail uses different resource ID format
    const isGmailProvider = provider === "gmail";
    if (!isGmailProvider && !selectedResource) return;
    if (isGmailProvider && gmailImportType === "query" && !gmailQuery.trim()) return;

    setIsImporting(true);
    setImportError(null);

    try {
      // Get resource ID and name based on provider
      let resourceId: string;
      let resourceName: string | undefined;

      if (isGmailProvider) {
        // Gmail: "inbox" or "query:<search_query>"
        if (gmailImportType === "inbox") {
          resourceId = "inbox";
          resourceName = "Inbox";
        } else {
          resourceId = `query:${gmailQuery.trim()}`;
          resourceName = `Search: ${gmailQuery.trim().slice(0, 30)}${gmailQuery.length > 30 ? "..." : ""}`;
        }
      } else if (provider === "slack") {
        resourceId = selectedResource!;
        const resource = landscape?.resources.find((r) => r.id === selectedResource);
        resourceName = resource?.name;
      } else {
        resourceId = selectedResource!;
        const resource = landscape?.resources.find((r) => r.id === selectedResource);
        resourceName = resource?.name;
      }

      // ADR-030: Include scope parameters
      // ADR-046: Use API provider for backend calls (calendar → google)
      const apiProvider = getApiProvider(provider);
      const job = await api.integrations.startImport(apiProvider, {
        resource_id: resourceId,
        resource_name: resourceName,
        instructions: instructions.trim() || undefined,
        config: learnStyle ? { learn_style: true } : undefined,
        scope: {
          recency_days: scope.recency_days,
          max_items: scope.max_items,
        },
      });

      setImportJob(job as unknown as ImportJob);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start import";
      setImportError(message);
      setIsImporting(false);
    }
  };

  const handleClose = () => {
    if (isImporting && importJob?.status === "processing") return;

    // Reset state
    setSelectedResource(null);
    setInstructions("");
    setLearnStyle(false);
    setImportJob(null);
    setImportError(null);
    setLandscape(null);
    setScope({
      recency_days: 7,
      max_items: provider === "notion" ? 10 : 100,
    });
    // Reset Gmail state
    setGmailImportType("inbox");
    setGmailQuery("");

    onClose();

    // If import completed successfully, trigger refresh
    if (importJob?.status === "completed") {
      onSuccess();
    }
  };

  if (!isOpen) return null;

  const resources = landscape?.resources || [];
  // Filter out excluded resources for selection
  const selectableResources = resources.filter(r => r.coverage_state !== "excluded");
  const providerName = provider === "slack" ? "Slack" : provider === "notion" ? "Notion" : "Gmail";
  const resourceLabel = provider === "slack" ? "channel" : provider === "notion" ? "page" : "source";
  const isGmail = provider === "gmail";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={handleClose}
      />

      {/* Modal - enlarged for better content display (ADR-030) */}
      <div className="relative z-10 w-full max-w-2xl mx-4 bg-background border border-border rounded-lg shadow-lg max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border shrink-0">
          <div className="flex items-center gap-2">
            <Download className="w-5 h-5 text-primary" />
            <h2 className="font-semibold">Import from {providerName}</h2>
          </div>
          <div className="flex items-center gap-2">
            {!isGmail && landscape && (
              <button
                onClick={() => loadResources(true)}
                disabled={isLoadingResources}
                className="p-1.5 rounded hover:bg-muted disabled:opacity-50"
                title="Refresh resources"
              >
                <RefreshCw className={`w-4 h-4 ${isLoadingResources ? "animate-spin" : ""}`} />
              </button>
            )}
            <button
              onClick={handleClose}
              disabled={isImporting && importJob?.status === "processing"}
              className="p-1 rounded hover:bg-muted disabled:opacity-50"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto flex-1">
          {/* Show import result if job exists */}
          {importJob ? (
            <ImportJobStatus
              job={importJob}
              provider={provider}
              onViewContext={() => {
                // ADR-034: Context browser deprecated - go to chat instead
                if (onNavigateToContext) {
                  onNavigateToContext();
                } else if (deskContext?.clearSurface) {
                  deskContext.clearSurface();
                } else {
                  router.push(HOME_ROUTE);
                }
                handleClose();
              }}
              onStartChat={() => {
                // Navigate to Thinking Partner home
                if (deskContext?.setSurface) {
                  deskContext.setSurface({ type: 'idle' });
                } else {
                  router.push(HOME_ROUTE);
                }
                handleClose();
              }}
            />
          ) : (
            <>
              <p className="text-sm text-muted-foreground mb-4">
                {isGmail
                  ? "Import context from your inbox or search for specific emails. I'll extract key decisions, action items, and project context automatically."
                  : `Select a ${resourceLabel} to import context from. I'll extract key decisions, action items, and project context automatically.`}
              </p>

              {/* ADR-030: Coverage summary for non-Gmail providers */}
              {!isGmail && landscape?.coverage_summary && (
                <CoverageSummaryBar summary={landscape.coverage_summary} />
              )}

              {/* Gmail-specific UI (ADR-029) */}
              {isGmail ? (
                <div className="space-y-4">
                  {/* Import type selector */}
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setGmailImportType("inbox")}
                      className={`flex-1 p-3 rounded-lg border transition-colors ${
                        gmailImportType === "inbox"
                          ? "bg-primary/10 border-primary"
                          : "border-border hover:bg-muted"
                      }`}
                    >
                      <div className="font-medium text-sm">Recent Inbox</div>
                      <div className="text-xs text-muted-foreground mt-1">
                        Import your latest inbox messages
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setGmailImportType("query")}
                      className={`flex-1 p-3 rounded-lg border transition-colors ${
                        gmailImportType === "query"
                          ? "bg-primary/10 border-primary"
                          : "border-border hover:bg-muted"
                      }`}
                    >
                      <div className="font-medium text-sm">Search</div>
                      <div className="text-xs text-muted-foreground mt-1">
                        Find specific emails by query
                      </div>
                    </button>
                  </div>

                  {/* Query input (shown when search selected) */}
                  {gmailImportType === "query" && (
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Gmail Search Query
                      </label>
                      <input
                        type="text"
                        value={gmailQuery}
                        onChange={(e) => setGmailQuery(e.target.value)}
                        placeholder="e.g., from:sarah@company.com or subject:project update"
                        className="w-full p-3 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                      />
                      <p className="text-xs text-muted-foreground mt-2">
                        Uses Gmail search syntax. Examples: &quot;from:name@email.com&quot;, &quot;subject:weekly&quot;, &quot;after:2024/01/01&quot;
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                /* Resource list for Slack/Notion with coverage indicators */
                <>
                  {isLoadingResources ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                    </div>
                  ) : resourceError ? (
                    <div className="p-4 bg-destructive/10 text-destructive rounded-lg flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 shrink-0" />
                      <div>
                        <p className="font-medium">Failed to load {resourceLabel}s</p>
                        <p className="text-sm">{resourceError}</p>
                      </div>
                      <button
                        onClick={() => loadResources()}
                        className="ml-auto p-2 hover:bg-destructive/20 rounded"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                    </div>
                  ) : selectableResources.length === 0 ? (
                    <div className="p-4 bg-muted/50 rounded-lg text-center text-muted-foreground">
                      <p>No {resourceLabel}s found.</p>
                      <p className="text-sm mt-1">
                        Make sure the {providerName} integration has access to the {resourceLabel}s you want to import.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-80 overflow-y-auto border border-border rounded-lg p-2">
                      {selectableResources.map((resource) => (
                        <button
                          key={resource.id}
                          onClick={() => setSelectedResource(resource.id)}
                          className={`w-full p-3 text-left rounded-lg transition-colors ${
                            selectedResource === resource.id
                              ? "bg-primary/10 border border-primary"
                              : "hover:bg-muted border border-transparent"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            {provider === "slack" ? (
                              resource.metadata?.is_private ? (
                                <Lock className="w-4 h-4 text-muted-foreground" />
                              ) : (
                                <Hash className="w-4 h-4 text-muted-foreground" />
                              )
                            ) : (
                              <FileText className="w-4 h-4 text-muted-foreground" />
                            )}
                            <span className="font-medium">{resource.name}</span>
                            {provider === "slack" &&
                              typeof resource.metadata?.num_members === "number" && (
                                <span className="text-xs text-muted-foreground ml-auto">
                                  {resource.metadata.num_members} members
                                </span>
                              )}
                          </div>
                          {/* ADR-030: Coverage indicator */}
                          <div className="mt-1">
                            <CoverageIndicator
                              state={resource.coverage_state}
                              lastExtracted={resource.last_extracted_at}
                              itemsExtracted={resource.items_extracted}
                            />
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </>
              )}

              {/* ADR-030: Scope configuration */}
              {(isGmail || selectableResources.length > 0) && (
                <ScopeConfiguration
                  scope={scope}
                  onChange={setScope}
                  provider={provider}
                />
              )}

              {/* Instructions (optional) - shown for all providers */}
              {(isGmail || selectableResources.length > 0) && (
                <div className="mt-4">
                  <label className="block text-sm font-medium mb-2">
                    Instructions (optional)
                  </label>
                  <textarea
                    value={instructions}
                    onChange={(e) => setInstructions(e.target.value)}
                    placeholder="e.g., Focus on product decisions and technical requirements"
                    className="w-full h-20 p-3 text-sm border border-border rounded-md bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
              )}

              {/* Style Learning Toggle - ADR-027 Phase 5, ADR-029 */}
              {(isGmail || selectableResources.length > 0) && (
                <div className="mt-4 p-3 border border-border rounded-lg bg-muted/30">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={learnStyle}
                      onChange={(e) => setLearnStyle(e.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-border"
                    />
                    <div>
                      <span className="text-sm font-medium">Learn my writing style</span>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {provider === "gmail"
                          ? "Analyze your email writing to capture your professional communication style"
                          : provider === "slack"
                          ? "Analyze your messages to capture your casual communication style"
                          : "Analyze this content to capture your documentation style"}
                      </p>
                    </div>
                  </label>
                </div>
              )}

              {/* Error */}
              {importError && (
                <div className="mt-3 p-2 bg-destructive/10 text-destructive text-sm rounded">
                  {importError}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t border-border shrink-0">
          {importJob?.status === "completed" ? (
            <button
              onClick={handleClose}
              className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Done
            </button>
          ) : importJob?.status === "failed" ? (
            <>
              <button
                onClick={() => {
                  setImportJob(null);
                  setImportError(null);
                }}
                className="px-4 py-2 text-sm border border-border rounded-md hover:bg-muted"
              >
                Try Again
              </button>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                Close
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleClose}
                disabled={isImporting}
                className="px-4 py-2 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleImport}
                disabled={
                  isImporting ||
                  (isGmail ? (gmailImportType === "query" && !gmailQuery.trim()) : !selectedResource)
                }
                className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
              >
                {isImporting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Importing...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
                    Import Context
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Component to show import job status and result.
 * Enhanced with navigation CTAs for better post-import UX.
 */
function ImportJobStatus({
  job,
  provider,
  onViewContext,
  onStartChat,
}: {
  job: ImportJob;
  provider: Provider;
  onViewContext?: () => void;
  onStartChat?: () => void;
}) {
  const providerName = provider === "slack" ? "Slack" : provider === "notion" ? "Notion" : "Gmail";

  if (job.status === "pending" || job.status === "processing") {
    const details = job.progress_details;
    const phaseLabels: Record<string, string> = {
      fetching: "Fetching data",
      processing: "Extracting context",
      storing: "Saving memories",
    };

    return (
      <div className="py-6">
        {/* Progress bar */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">
              {job.status === "pending" ? "Starting..." : (details ? phaseLabels[details.phase] : "Processing...")}
            </span>
            <span className="text-sm text-muted-foreground">{job.progress}%</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-500"
              style={{ width: `${job.progress}%` }}
            />
          </div>
        </div>

        {/* Progress details */}
        <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="w-4 h-4 animate-spin" />
          {job.status === "pending" ? (
            <span>Waiting to start...</span>
          ) : details ? (
            <span>
              {details.items_completed} of {details.items_total} items
              {details.current_resource && ` · ${details.current_resource}`}
            </span>
          ) : (
            <span>Importing from {job.resource_name || providerName}...</span>
          )}
        </div>
      </div>
    );
  }

  if (job.status === "failed") {
    return (
      <div className="py-4">
        <div className="flex items-center gap-2 text-destructive mb-4">
          <AlertTriangle className="w-6 h-6" />
          <span className="font-medium">Import failed</span>
        </div>
        <p className="text-sm text-muted-foreground">
          {job.error_message || "An unexpected error occurred. Please try again."}
        </p>
      </div>
    );
  }

  // Completed - Enhanced with navigation CTAs
  const hasContent = job.result && job.result.blocks_created > 0;

  return (
    <div className="py-4">
      <div className="flex items-center gap-2 text-green-600 dark:text-green-400 mb-4">
        <CheckCircle2 className="w-6 h-6" />
        <span className="font-medium">Import complete!</span>
      </div>

      {job.result && (
        <div className="space-y-4">
          {/* Stats grid */}
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="p-3 bg-muted/50 rounded-lg">
              <div className="text-2xl font-bold text-primary">{job.result.blocks_created}</div>
              <div className="text-xs text-muted-foreground">Context extracted</div>
            </div>
            <div className="p-3 bg-muted/50 rounded-lg">
              <div className="text-2xl font-bold">{job.result.items_processed}</div>
              <div className="text-xs text-muted-foreground">Items processed</div>
            </div>
            <div className="p-3 bg-muted/50 rounded-lg">
              <div className="text-2xl font-bold">{job.result.items_filtered}</div>
              <div className="text-xs text-muted-foreground">Noise filtered</div>
            </div>
          </div>

          {/* Summary */}
          {job.result.summary && (
            <div className="p-3 bg-muted/30 rounded-lg text-sm text-muted-foreground">
              {job.result.summary}
            </div>
          )}

          {/* Style Learning Result - ADR-027 Phase 5 */}
          {job.result.style_learned && (
            <div className="p-3 bg-primary/10 border border-primary/20 rounded-lg">
              <div className="flex items-center gap-2 text-sm">
                <Check className="w-4 h-4 text-primary" />
                <span className="font-medium text-primary">Writing style captured</span>
                {job.result.style_confidence && (
                  <span className="text-xs text-muted-foreground ml-auto">
                    {job.result.style_confidence} confidence
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Your {providerName.toLowerCase()} communication style will be applied to future deliverables.
              </p>
            </div>
          )}

          {/* Navigation CTAs - only show if content was extracted */}
          {hasContent && (onViewContext || onStartChat) && (
            <div className="pt-2 space-y-2">
              <p className="text-xs text-muted-foreground text-center">
                Your new context is ready to use
              </p>
              <div className="flex gap-2">
                {onViewContext && (
                  <button
                    onClick={onViewContext}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm border border-border rounded-lg hover:bg-muted transition-colors"
                  >
                    <Brain className="w-4 h-4" />
                    View Context
                  </button>
                )}
                {onStartChat && (
                  <button
                    onClick={onStartChat}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                  >
                    <MessageSquare className="w-4 h-4" />
                    Try it in {HOME_LABEL}
                    <ArrowRight className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
