"use client";

/**
 * Download Workspace — the portability affordance (ADR-328 D4, via ADR-510).
 *
 * The export engine and route (`GET /api/workspace/export`) shipped without a
 * caller, so the claim canon calls "the single sharpest technical
 * differentiator" (THESIS Commitment 4) was reachable only by hand-crafting an
 * authenticated request. This card is the doorway.
 *
 * It sits ABOVE the purges and the delete card deliberately. A member closing
 * out their workspace is exactly the member who needs the export, at exactly
 * the moment they would never go looking for it — and ADR-405 says the system
 * does not destroy work unwitnessed. Offering the copy before the destruction
 * is what makes the witness honest.
 *
 * Not gated on clear-authority: reading your own workspace is not a
 * destructive act, and the route is already grant-scoped server-side (a
 * narrowed principal's export omits ungranted paths AND declares the count in
 * the manifest — never silently).
 */

import { useCallback, useState } from "react";
import { Download, Loader2 } from "lucide-react";

import { api } from "@/lib/api/client";

export function WorkspaceExportCard() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      await api.workspace.exportWorkspace();
    } catch {
      setError("Couldn't build the download. Try again in a moment.");
    } finally {
      setPending(false);
    }
  }, []);

  return (
    <div className="rounded-lg border border-border p-4">
      <div className="flex items-start gap-3">
        <Download className="w-4 h-4 mt-0.5 text-muted-foreground shrink-0" />
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium">Download Workspace</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Get every file, plus every earlier version and who wrote it. Opens
            with any tool that reads folders — nothing here needs yarnnn.
          </p>

          {error && (
            <p className="text-sm text-destructive mt-2" role="alert">
              {error}
            </p>
          )}

          <div className="mt-3">
            <button
              type="button"
              disabled={pending}
              onClick={() => void run()}
              className="px-3 py-1.5 rounded-md border border-border text-sm disabled:opacity-50 inline-flex items-center gap-2"
            >
              {pending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {pending ? "Preparing…" : "Download"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
