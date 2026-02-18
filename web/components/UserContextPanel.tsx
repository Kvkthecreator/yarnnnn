"use client";

/**
 * UserContextPanel
 * ADR-059: User Context Entries
 *
 * Displays user context entries (key-value pairs) and documents.
 * Supports both sidebar mode and inline mode.
 */

import { useState, useEffect } from "react";
import {
  User,
  Loader2,
  Trash2,
  ChevronDown,
  ChevronRight,
  X,
  Tag,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { DocumentList } from "@/components/DocumentList";

// ADR-059: User context entry format (from user_context table)
interface UserContextEntry {
  id: string;
  key: string;
  value: string;
  source: string;
  confidence: number;
  created_at: string;
  updated_at: string;
}

interface UserContextPanelProps {
  isOpen: boolean;
  onClose: () => void;
  inline?: boolean;
}

export function UserContextPanel({ isOpen, onClose, inline = false }: UserContextPanelProps) {
  const [entries, setEntries] = useState<UserContextEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());

  // Fetch user context entries on mount
  useEffect(() => {
    async function fetchEntries() {
      try {
        const data = await api.userMemories.list();
        setEntries(data);
        setError(null);

        // Auto-expand all sources that have items
        const sources = new Set<string>();
        data.forEach((e) => sources.add(e.source || "other"));
        setExpandedSources(sources);
      } catch (err) {
        console.error("Failed to fetch user context:", err);
        setError("Failed to load");
      } finally {
        setIsLoading(false);
      }
    }
    if (isOpen) {
      fetchEntries();
    }
  }, [isOpen]);

  const handleDelete = async (entryId: string) => {
    try {
      await api.memories.delete(entryId);
      setEntries((prev) => prev.filter((e) => e.id !== entryId));
    } catch (err) {
      console.error("Failed to delete entry:", err);
    }
  };

  const toggleSource = (source: string) => {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      if (next.has(source)) {
        next.delete(source);
      } else {
        next.add(source);
      }
      return next;
    });
  };

  // Group entries by source (or "other" if no source)
  const entriesBySource = entries.reduce(
    (acc, entry) => {
      const source = entry.source || "other";
      if (!acc[source]) {
        acc[source] = [];
      }
      acc[source].push(entry);
      return acc;
    },
    {} as Record<string, UserContextEntry[]>
  );

  // Sort sources by count (most items first)
  const sortedSources = Object.keys(entriesBySource).sort(
    (a, b) => entriesBySource[b].length - entriesBySource[a].length
  );

  if (!isOpen) {
    return null;
  }

  // Shared content rendering
  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex justify-center py-8">
          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      );
    }

    if (error) {
      return (
        <div className="text-sm text-destructive text-center py-4">
          {error}
        </div>
      );
    }

    if (entries.length === 0) {
      return (
        <div className="text-center py-8">
          <User className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground">Nothing learned yet</p>
          <p className="text-xs text-muted-foreground mt-1">
            Chat with your Thinking Partner and I&apos;ll learn about you
          </p>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        {sortedSources.map((source) => {
          const sourceEntries = entriesBySource[source];
          const isExpanded = expandedSources.has(source);

          return (
            <div key={source}>
              {/* Source Header */}
              <button
                onClick={() => toggleSource(source)}
                className="w-full flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground mb-1 py-1"
              >
                {isExpanded ? (
                  <ChevronDown className="w-3 h-3" />
                ) : (
                  <ChevronRight className="w-3 h-3" />
                )}
                <span className="p-1 rounded bg-primary/10 text-primary">
                  <Tag className="w-3 h-3" />
                </span>
                <span className="capitalize">{source}</span>
                <span className="ml-auto text-muted-foreground">
                  {sourceEntries.length}
                </span>
              </button>

              {/* Source Items */}
              {isExpanded && (
                <div className="space-y-1 ml-5">
                  {sourceEntries.map((entry) => (
                    <div
                      key={entry.id}
                      className="group relative p-2 text-xs rounded hover:bg-muted"
                    >
                      <p className="pr-6 font-medium text-muted-foreground">{entry.key}</p>
                      <p className="pr-6">{entry.value}</p>
                      {/* Confidence indicator */}
                      {entry.confidence >= 0.8 && (
                        <span className="text-[10px] text-primary ml-1">
                          high confidence
                        </span>
                      )}
                      <button
                        onClick={() => handleDelete(entry.id)}
                        className="absolute top-2 right-2 p-1.5 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-opacity"
                        title="Remove this"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  // Inline mode: render as full-width content without sidebar styling
  if (inline) {
    return (
      <div className="w-full">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-lg font-semibold">About You</h2>
        </div>

        {/* Documents Section */}
        <div className="mb-6">
          <DocumentList />
        </div>

        {/* Context Entries Section */}
        <div className="pt-4 border-t border-border">
          <h3 className="text-xs font-medium text-muted-foreground mb-3 flex items-center gap-2">
            <Tag className="w-3.5 h-3.5" />
            Context
          </h3>
          {renderContent()}
        </div>

        {entries.length > 0 && (
          <div className="mt-6 pt-4 border-t border-border">
            <p className="text-xs text-muted-foreground">
              {entries.length} things I know about you
            </p>
          </div>
        )}
      </div>
    );
  }

  // Sidebar mode (default)
  return (
    <aside className="w-72 lg:w-80 border-l border-border bg-muted/30 flex flex-col shrink-0">
      {/* Header */}
      <div className="p-3 border-b border-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium">About You</span>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 hover:bg-muted rounded text-muted-foreground"
          aria-label="Close panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {/* Documents Section */}
        <div className="mb-4">
          <DocumentList compact />
        </div>

        {/* Context Entries Section */}
        <div className="pt-3 border-t border-border">
          <h3 className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-2">
            <Tag className="w-3 h-3" />
            Context
          </h3>
          {renderContent()}
        </div>
      </div>

      {/* Footer */}
      {entries.length > 0 && (
        <div className="p-3 border-t border-border shrink-0">
          <p className="text-xs text-muted-foreground text-center">
            {entries.length} things I know about you
          </p>
        </div>
      )}
    </aside>
  );
}
