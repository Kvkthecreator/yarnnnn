"use client";

import { useState, useEffect } from "react";
import {
  User,
  Briefcase,
  Target,
  Clock,
  MessageSquare,
  AlertCircle,
  Users,
  Loader2,
  Trash2,
  ChevronDown,
  ChevronRight,
  X,
} from "lucide-react";
import { api } from "@/lib/api/client";
import type { UserContext, UserContextCategory } from "@/types";

// Category display config
const CATEGORY_CONFIG: Record<
  UserContextCategory,
  { label: string; icon: React.ReactNode; color: string }
> = {
  preference: {
    label: "Preferences",
    icon: <User className="w-3 h-3" />,
    color: "text-blue-600 bg-blue-50 dark:bg-blue-950 dark:text-blue-400",
  },
  business_fact: {
    label: "Business",
    icon: <Briefcase className="w-3 h-3" />,
    color: "text-purple-600 bg-purple-50 dark:bg-purple-950 dark:text-purple-400",
  },
  goal: {
    label: "Goals",
    icon: <Target className="w-3 h-3" />,
    color: "text-green-600 bg-green-50 dark:bg-green-950 dark:text-green-400",
  },
  work_pattern: {
    label: "Work Patterns",
    icon: <Clock className="w-3 h-3" />,
    color: "text-orange-600 bg-orange-50 dark:bg-orange-950 dark:text-orange-400",
  },
  communication_style: {
    label: "Communication",
    icon: <MessageSquare className="w-3 h-3" />,
    color: "text-cyan-600 bg-cyan-50 dark:bg-cyan-950 dark:text-cyan-400",
  },
  constraint: {
    label: "Constraints",
    icon: <AlertCircle className="w-3 h-3" />,
    color: "text-red-600 bg-red-50 dark:bg-red-950 dark:text-red-400",
  },
  relationship: {
    label: "Relationships",
    icon: <Users className="w-3 h-3" />,
    color: "text-pink-600 bg-pink-50 dark:bg-pink-950 dark:text-pink-400",
  },
};

// Order categories for display
const CATEGORY_ORDER: UserContextCategory[] = [
  "business_fact",
  "goal",
  "preference",
  "work_pattern",
  "communication_style",
  "constraint",
  "relationship",
];

interface UserContextPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function UserContextPanel({ isOpen, onClose }: UserContextPanelProps) {
  const [items, setItems] = useState<UserContext[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(CATEGORY_ORDER)
  );

  // Fetch user context on mount
  useEffect(() => {
    async function fetchUserContext() {
      try {
        const data = await api.userContext.list();
        setItems(data);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch user context:", err);
        setError("Failed to load");
      } finally {
        setIsLoading(false);
      }
    }
    fetchUserContext();
  }, []);

  const handleDelete = async (itemId: string) => {
    try {
      await api.userContext.delete(itemId);
      setItems((prev) => prev.filter((item) => item.id !== itemId));
    } catch (err) {
      console.error("Failed to delete item:", err);
    }
  };

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  // Group items by category
  const itemsByCategory = CATEGORY_ORDER.reduce(
    (acc, category) => {
      acc[category] = items.filter((item) => item.category === category);
      return acc;
    },
    {} as Record<UserContextCategory, UserContext[]>
  );

  if (!isOpen) {
    return null;
  }

  return (
    <aside className="w-72 lg:w-80 border-l border-border bg-muted/30 flex flex-col shrink-0">
      {/* Header */}
      <div className="p-3 border-b border-border flex items-center justify-between shrink-0">
        <span className="text-sm font-medium">About You</span>
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
        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="text-sm text-destructive text-center py-4">
            {error}
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-8">
            <User className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
            <p className="text-sm text-muted-foreground">Nothing learned yet</p>
            <p className="text-xs text-muted-foreground mt-1">
              Chat with your Thinking Partner and I&apos;ll learn about you
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {CATEGORY_ORDER.map((category) => {
              const categoryItems = itemsByCategory[category];
              if (categoryItems.length === 0) return null;

              const config = CATEGORY_CONFIG[category];
              const isExpanded = expandedCategories.has(category);

              return (
                <div key={category}>
                  {/* Category Header */}
                  <button
                    onClick={() => toggleCategory(category)}
                    className="w-full flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground mb-1 py-1"
                  >
                    {isExpanded ? (
                      <ChevronDown className="w-3 h-3" />
                    ) : (
                      <ChevronRight className="w-3 h-3" />
                    )}
                    <span className={`p-1 rounded ${config.color}`}>
                      {config.icon}
                    </span>
                    {config.label}
                    <span className="ml-auto text-muted-foreground">
                      {categoryItems.length}
                    </span>
                  </button>

                  {/* Category Items */}
                  {isExpanded && (
                    <div className="space-y-1 ml-5">
                      {categoryItems.map((item) => (
                        <div
                          key={item.id}
                          className="group relative p-2 text-xs rounded hover:bg-muted"
                        >
                          <p className="pr-6">{item.content}</p>
                          {item.confidence && item.confidence < 0.8 && (
                            <span className="text-muted-foreground text-[10px]">
                              (uncertain)
                            </span>
                          )}
                          <button
                            onClick={() => handleDelete(item.id)}
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
        )}
      </div>

      {/* Footer */}
      {items.length > 0 && (
        <div className="p-3 border-t border-border shrink-0">
          <p className="text-xs text-muted-foreground text-center">
            {items.length} things learned about you
          </p>
        </div>
      )}
    </aside>
  );
}
