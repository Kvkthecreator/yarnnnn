"use client";

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
import type { Memory } from "@/types";

interface UserContextPanelProps {
  isOpen: boolean;
  onClose: () => void;
  inline?: boolean;
}

export function UserContextPanel({ isOpen, onClose, inline = false }: UserContextPanelProps) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedTags, setExpandedTags] = useState<Set<string>>(new Set());

  // Fetch user memories on mount
  useEffect(() => {
    async function fetchMemories() {
      try {
        const data = await api.userMemories.list();
        setMemories(data);
        setError(null);

        // Auto-expand all tags that have items
        const tags = new Set<string>();
        data.forEach((m) => m.tags.forEach((t) => tags.add(t)));
        setExpandedTags(tags);
      } catch (err) {
        console.error("Failed to fetch user memories:", err);
        setError("Failed to load");
      } finally {
        setIsLoading(false);
      }
    }
    if (isOpen) {
      fetchMemories();
    }
  }, [isOpen]);

  const handleDelete = async (memoryId: string) => {
    try {
      await api.memories.delete(memoryId);
      setMemories((prev) => prev.filter((m) => m.id !== memoryId));
    } catch (err) {
      console.error("Failed to delete memory:", err);
    }
  };

  const toggleTag = (tag: string) => {
    setExpandedTags((prev) => {
      const next = new Set(prev);
      if (next.has(tag)) {
        next.delete(tag);
      } else {
        next.add(tag);
      }
      return next;
    });
  };

  // Group memories by their first tag (or "other" if no tags)
  const memoriesByTag = memories.reduce(
    (acc, memory) => {
      const primaryTag = memory.tags[0] || "other";
      if (!acc[primaryTag]) {
        acc[primaryTag] = [];
      }
      acc[primaryTag].push(memory);
      return acc;
    },
    {} as Record<string, Memory[]>
  );

  // Sort tags by count (most items first)
  const sortedTags = Object.keys(memoriesByTag).sort(
    (a, b) => memoriesByTag[b].length - memoriesByTag[a].length
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

    if (memories.length === 0) {
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
        {sortedTags.map((tag) => {
          const tagMemories = memoriesByTag[tag];
          const isExpanded = expandedTags.has(tag);

          return (
            <div key={tag}>
              {/* Tag Header */}
              <button
                onClick={() => toggleTag(tag)}
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
                <span className="capitalize">{tag}</span>
                <span className="ml-auto text-muted-foreground">
                  {tagMemories.length}
                </span>
              </button>

              {/* Tag Items */}
              {isExpanded && (
                <div className="space-y-1 ml-5">
                  {tagMemories.map((memory) => (
                    <div
                      key={memory.id}
                      className="group relative p-2 text-xs rounded hover:bg-muted"
                    >
                      <p className="pr-6">{memory.content}</p>
                      {/* Show additional tags */}
                      {memory.tags.length > 1 && (
                        <div className="flex gap-1 mt-1 flex-wrap">
                          {memory.tags.slice(1).map((t) => (
                            <span
                              key={t}
                              className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground"
                            >
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                      {/* Importance indicator */}
                      {memory.importance >= 0.8 && (
                        <span className="text-[10px] text-primary ml-1">
                          ★
                        </span>
                      )}
                      <button
                        onClick={() => handleDelete(memory.id)}
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
        {renderContent()}
        {memories.length > 0 && (
          <div className="mt-6 pt-4 border-t border-border">
            <p className="text-xs text-muted-foreground">
              {memories.length} memories about you
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
        {renderContent()}
      </div>

      {/* Footer */}
      {memories.length > 0 && (
        <div className="p-3 border-t border-border shrink-0">
          <p className="text-xs text-muted-foreground text-center">
            {memories.length} memories about you
          </p>
        </div>
      )}
    </aside>
  );
}
