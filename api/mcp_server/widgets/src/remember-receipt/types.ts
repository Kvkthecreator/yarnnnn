// The `remember` result shape (server.py remember, api/services/mcp_composition).
// The widget renders a compact confirmation receipt of the durable write.

export interface RememberResult {
  success?: boolean;
  written_to?: string;
  captured?: boolean;
  provenance?: { source?: string } | null;
  error?: string;
  message?: string;
}

export function isRememberResult(v: Record<string, unknown>): boolean {
  return "written_to" in v || "captured" in v || ("success" in v && "provenance" in v);
}
