import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// =============================================================================
// Tool Display Names (ADR-039: Claude Code-style status messages)
// =============================================================================

/**
 * Maps internal tool names to user-facing status messages.
 *
 * Tool names match backend primitives (api/services/primitives/*.py).
 * Pattern follows Claude Code:
 * - Present participle ("Checking...", "Creating...")
 * - Describes the action, not the tool
 * - Brief and scannable
 */
const TOOL_DISPLAY_NAMES: Record<string, string> = {
  // Entity layer (ADR-168 Commit 4: renamed from Read/List/Search/Edit)
  LookupEntity: "Looking up entity",
  ListEntities: "Listing entities",
  SearchEntities: "Searching entities",
  EditEntity: "Editing entity",
  Todo: "Tracking progress",
  Respond: "Responding",
  Clarify: "Asking for clarification",

  // Agent lifecycle (ADR-156)
  ManageAgent: "Managing agent",

  // Task lifecycle (ADR-138, ADR-146, ADR-168: CreateTask folded into ManageTask)
  ManageTask: "Managing task",

  // Domain management (ADR-155)
  ManageDomains: "Managing domains",

  // Context (ADR-146)
  UpdateContext: "Updating context",
  GetSystemState: "Checking system state",
  WebSearch: "Searching the web",
  web_search: "Searching the web",  // Legacy alias

  // Platform tools
  list_integrations: "Checking connected platforms",
  list_platform_resources: "Listing resources",
  sync_platform_resource: "Syncing data",
  get_sync_status: "Checking sync status",

  // File layer (ADR-106, ADR-168 Commit 4: renamed from ReadWorkspace/etc.)
  ReadFile: "Reading file",
  WriteFile: "Writing file",
  SearchFiles: "Searching files",
  QueryKnowledge: "Querying knowledge base",
  ListFiles: "Listing files",
  DiscoverAgents: "Discovering agents",
  ReadAgentFile: "Reading agent file",

  // Notification
  send_notification: "Sending notification",

  // Todo tracking
  todo_write: "Updating progress",
};

/**
 * Platform-specific resource messages for list_platform_resources.
 */
const PLATFORM_RESOURCE_MESSAGES: Record<string, string> = {
  slack: "Listing Slack channels",
  notion: "Listing Notion pages",
};

/**
 * Platform-specific sync messages for sync_platform_resource.
 */
const PLATFORM_SYNC_MESSAGES: Record<string, string> = {
  slack: "Syncing Slack messages",
  notion: "Syncing Notion content",
};

/**
 * Get a human-readable status message for a tool call.
 *
 * @param toolName - The internal tool name
 * @param input - Optional tool input for context-aware messages
 * @returns User-facing status message
 */
export function getToolDisplayMessage(
  toolName: string,
  input?: Record<string, unknown>
): string {
  // Check for platform-specific messages
  if (toolName === "list_platform_resources" && input?.platform) {
    const platform = input.platform as string;
    return PLATFORM_RESOURCE_MESSAGES[platform] || `Listing ${platform} resources`;
  }

  if (toolName === "sync_platform_resource" && input?.platform) {
    const platform = input.platform as string;
    const resourceName = input.resource_name as string;
    if (resourceName) {
      return `Syncing ${resourceName}`;
    }
    return PLATFORM_SYNC_MESSAGES[platform] || `Syncing ${platform} data`;
  }

  if (toolName === "list_integrations") {
    return "Checking connected platforms";
  }

  if (toolName === "get_sync_status" && input?.platform) {
    const platform = input.platform as string;
    return `Checking ${platform} sync status`;
  }

  // Default: look up in mapping or format the tool name
  return TOOL_DISPLAY_NAMES[toolName] || formatToolName(toolName);
}

/**
 * Fallback formatter for unknown tools.
 * Converts PascalCase or snake_case to readable format.
 */
function formatToolName(toolName: string): string {
  // Handle PascalCase (e.g., "LookupEntity" → "Lookup entity")
  if (toolName.includes("_")) {
    return toolName
      .split("_")
      .map((word, i) => i === 0 ? word.charAt(0).toUpperCase() + word.slice(1) : word)
      .join(" ");
  }
  // PascalCase split
  return toolName
    .replace(/([A-Z])/g, " $1")
    .trim()
    .replace(/^./, (c) => c.toUpperCase());
}
