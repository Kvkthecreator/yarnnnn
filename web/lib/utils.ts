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
  // Core primitives (ADR-080)
  Read: "Reading content",
  Write: "Writing content",
  Edit: "Editing content",
  List: "Listing resources",
  Search: "Searching",
  Execute: "Executing action",
  Todo: "Tracking progress",
  Respond: "Responding",
  Clarify: "Asking for clarification",

  // Agent lifecycle (ADR-111)
  CreateAgent: "Creating agent",
  AdvanceAgentSchedule: "Advancing schedule",

  // Intelligence (ADR-087/106)
  SaveMemory: "Saving to memory",
  GetSystemState: "Checking system state",
  WebSearch: "Searching the web",
  web_search: "Searching the web",  // Legacy alias

  // Platform tools (ADR-039)
  RefreshPlatformContent: "Refreshing platform data",
  list_integrations: "Checking connected platforms",
  list_platform_resources: "Listing resources",
  sync_platform_resource: "Syncing data",
  get_sync_status: "Checking sync status",

  // Workspace primitives (ADR-106)
  ReadWorkspace: "Reading workspace",
  WriteWorkspace: "Writing to workspace",
  SearchWorkspace: "Searching workspace",
  QueryKnowledge: "Querying knowledge base",
  ListWorkspace: "Listing workspace files",
  DiscoverAgents: "Discovering agents",
  ReadAgentContext: "Reading agent context",

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
  // Handle PascalCase (e.g., "ReadWorkspace" → "Read workspace")
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
