/**
 * YARNNN API Client
 * ADR-005: Unified memory with embeddings
 */

import { createClient } from "@/lib/supabase/client";
import { sseEvents } from "@/lib/sse";
import type { StudioVocabulary } from "@/components/authoring/StudioToolbar";
import type {
  Memory,
  MemoryCreate,
  MemoryUpdate,
  BulkImportRequest,
  WorkspaceUpload,
  WorkspaceUploadResponse,
  WorkspaceUploadListResponse,
  DocumentDownloadResponse,
  DeleteResponse,
  SubscriptionStatus,
  ByokStatus,
  CheckoutResponse,
  PortalResponse,
  CancelResponse,
  // ADR-034: Context Domains
  ContextDomainSummary,
  ContextDomainDetail,
  ActiveDomainResponse,
  // ADR-231 D5 + ADR-235 D1.c: TaskCreate / TaskType / TaskTypesResponse
  // DELETED. Recurrence creation flows through ManageRecurrence(action='create');
  // the registry catalog is dissolved.
  ProcessStepsResponse,
  RunStatus,
  // ADR-152: Workspace Explorer
  WorkspaceTreeNode,
  WorkspaceFile,
  WorkspaceFileWithRevision,
  // ADR-219 Commit 4: narrative filter-over-substrate
  // ADR-250: per-invocation execution log
  ExecutionEvent,
} from "@/types";
import type {
  AdminOverviewStats,
  AdminExecutionStats,
  AdminUserRow,
  AdminAccountRow,
  AdminAccountDetail,
} from "@/types/admin";
// ADR-312 home-bundle: the bundle's `surfaces` field is the full compositor
// SurfacesResponse (including surfaces[]), so useComposition can be primed
// from it directly. Type-only import — erased at runtime, no layering cost.
import type { SurfacesResponse } from "@/lib/compositor/types";
import type { FocusWire } from "@/lib/shell/useSurfaceFocus";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** The API speaks TWO error wire shapes and every reader must accept both.
 *
 *  Raw FastAPI raises surface as `{detail}`; anything through the envelope
 *  middleware (`api/main.py`, which normalizes EVERY HTTPException) arrives as
 *  `{error: {code, message, hint}}`. A reader that knows only `detail` compiles,
 *  ships, and then silently misreads every enveloped error.
 *
 *  Observed 2026-08-26: ADR-499's stale-pin self-heal tested `data.detail` and
 *  so never fired in production — the envelope had moved the string to
 *  `error.message`. A member with a revoked grant kept a poisoned
 *  `X-Workspace-Id` pin with no clearing path, and the invite that would have
 *  restored their access 403'd on the pin itself: they could not rejoin the
 *  workspace they had been re-invited to.
 *
 *  One extractor, so the two shapes can never drift apart again. */
export function errorDetailFrom(data: unknown): unknown {
  const d = data as
    | { detail?: unknown; error?: { message?: unknown } | null }
    | null;
  if (d?.detail !== undefined && d.detail !== null) return d.detail;
  const enveloped = d?.error?.message;
  return typeof enveloped === "string" ? enveloped : undefined;
}

export class APIError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    // The server's own words come first. FastAPI puts the reason in
    // `detail` — a lane cap, a stale parent, a missing grant — and every
    // surface that renders `error.message` was showing "API Error: 409"
    // instead. `statusText` is empty over HTTP/2, so the status-only form
    // read as a bare number with no reason at all. Fall back to the status
    // line only when the body carries nothing legible.
    super(APIError.messageFrom(status, statusText, data));
    this.name = "APIError";
  }

  private static messageFrom(
    status: number,
    statusText: string,
    data: unknown
  ): string {
    const detail = errorDetailFrom(data);
    if (typeof detail === "string" && detail.trim()) return detail;
    // 422s arrive as a list of validation objects — surface the first `msg`
    // rather than "[object Object]".
    if (Array.isArray(detail)) {
      const first = detail.find(
        (d) => typeof (d as { msg?: unknown })?.msg === "string"
      ) as { msg?: string } | undefined;
      if (first?.msg) return first.msg;
    }
    return `API Error: ${status}${statusText ? ` ${statusText}` : ""}`;
  }
}

async function getAuthHeaders(): Promise<HeadersInit> {
  const supabase = createClient();

  // Try getSession first, fall back to refresh if needed
  let token: string | undefined;

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (session?.access_token) {
    token = session.access_token;
  } else {
    // Session might not be available, try to refresh
    const { data: refreshData } = await supabase.auth.refreshSession();
    token = refreshData.session?.access_token;
  }

  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  } else {
    console.warn("No auth token available for API request");
  }

  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (tz) (headers as Record<string, string>)["X-Timezone"] = tz;
  } catch {
    // Non-fatal — server falls back to UTC
  }

  // ADR-373 sweep spine: a member operating a workspace they don't own
  // binds it explicitly. Absent → the API uses the owner workspace
  // (byte-identical for owners). Set on invite-accept; validated
  // fail-closed server-side (403 when no active grant).
  try {
    const ws = window.localStorage.getItem(ACTIVE_WORKSPACE_KEY);
    if (ws) (headers as Record<string, string>)["X-Workspace-Id"] = ws;
  } catch {
    // SSR / storage unavailable — owner default applies
  }

  return headers;
}

/** localStorage key holding the explicitly-bound workspace id (member mode). */
export const ACTIVE_WORKSPACE_KEY = "yarnnn.active-workspace";

/** The currently pinned workspace id, or null. Reading it is how the
 *  self-heal below distinguishes "the pin is stale" from "you lack authority
 *  for this verb" — both are 403s, only one is fixable by dropping a header. */
export function getActiveWorkspaceId(): string | null {
  try {
    return window.localStorage.getItem(ACTIVE_WORKSPACE_KEY);
  } catch {
    return null; // storage unavailable — treat as unpinned
  }
}

export function setActiveWorkspace(workspaceId: string | null): void {
  try {
    if (workspaceId) window.localStorage.setItem(ACTIVE_WORKSPACE_KEY, workspaceId);
    else window.localStorage.removeItem(ACTIVE_WORKSPACE_KEY);
  } catch {
    // storage unavailable — non-fatal
  }
}

/** ADR-407 Phase 5 — "switch to my own workspace" CLEARS the binding rather
 *  than pinning the owner workspace id: absent header → server resolves the
 *  caller's owner workspace (the N=1 default, byte-identical for owners). */
export function clearActiveWorkspace(): void {
  setActiveWorkspace(null);
}

/** Internal-only: marks the single self-heal retry so it can never loop. */
type RequestOptions = RequestInit & { __retriedWithoutWorkspace?: boolean };

/** One reload per heal, not one per in-flight request. A page load fans out
 *  many parallel calls; with a revoked pin EVERY one of them 403s and heals, so
 *  an unguarded schedule would queue N reloads and could cut short the healed
 *  retries still resolving. Module-scoped because the heal is a page-level
 *  event, not a per-call one. */
let reloadScheduled = false;

/** The stale-pin 403 signature (ADR-499). The server raises this ONLY when an
 *  `X-Workspace-Id` header was present and the caller cannot reach it
 *  (`services/supabase.py::get_user_client`), so it is precisely "your pin is
 *  wrong" and never an ordinary authorization refusal. Exported so every
 *  transport that sends the pin tests the SAME condition — a second transport
 *  spelling this check itself is how the two drift. */
export function isStaleWorkspacePin(status: number, detail: unknown): boolean {
  return (
    status === 403 &&
    typeof detail === "string" &&
    detail.startsWith("No active grant into workspace") &&
    !!getActiveWorkspaceId()
  );
}

/** Clear the stale pin and schedule the page-level reload, once.
 *
 *  Exported for transports that do NOT go through `request()` — notably the
 *  chat/SSE transport, which hand-builds its headers, sends the pin, and
 *  returns a raw `Response`. Without this it surfaced a stale-pin 403 as an
 *  ordinary chat error: no heal, no retry, no reload, so the member stayed
 *  pinned to an unreachable workspace while `request()` callers around them
 *  healed. The reload guard is module-scoped and SHARED, so a heal here and a
 *  heal in `request()` still produce exactly one navigation.
 *
 *  Returns true if this call performed the heal (the caller may want to say
 *  "reconnecting" rather than print the raw server error). */
export function healStaleWorkspacePin(): boolean {
  clearActiveWorkspace();
  if (typeof window === "undefined" || reloadScheduled) return false;
  reloadScheduled = true;
  // Same 150ms rationale as the request() path: let other in-flight heals
  // settle so the reload is the last thing that happens, not a race.
  setTimeout(() => window.location.reload(), 150);
  return true;
}

async function request<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const headers = await getAuthHeaders();

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    credentials: "include",
    headers: {
      ...headers,
      ...options.headers,
    },
  });

  if (!response.ok) {
    let data;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    // ADR-499 — SELF-HEAL A STALE WORKSPACE PIN.
    //
    // `X-Workspace-Id` is a localStorage pin written on invite/share accept.
    // The server validates it fail-closed (`supabase.py`: "No active grant into
    // workspace …" → 403). If the grant is later REVOKED — or the workspace is
    // deleted — the pin survives in the browser with no clearing path, so every
    // subsequent request 403s: account stats, notification prefs, surfaces, all
    // of it. The member appears to have no workspace at all, even though their
    // OWN owner-workspace is sitting right there, reachable the moment the
    // header goes away.
    //
    // Observed 2026-07-29: a member whose invite grant was revoked was locked
    // out of their own account by a pin naming someone else's workspace.
    //
    // The pin is a client-side CACHE of a server-side fact. When the server
    // says the fact is gone, the cache must go too — then retry ONCE without
    // it, which falls back to the caller's owner workspace (the N=1 default).
    // Scoped narrowly to this one detail string so an ordinary authorization
    // 403 (owner-only verbs, etc.) is never swallowed.
    const staleWorkspacePin = isStaleWorkspacePin(
      response.status,
      errorDetailFrom(data),
    );

    if (staleWorkspacePin && !options.__retriedWithoutWorkspace) {
      clearActiveWorkspace();
      // THE ACTING WORKSPACE JUST CHANGED — so the page must reload.
      //
      // Clearing the pin rebinds every subsequent request to a DIFFERENT
      // workspace, but the mounted tree doesn't know: every surface above this
      // call fetched under the old binding and, being mount-only, never
      // refetches. The switcher states the rule outright ("a full reload is
      // required so every fetched surface rebinds to the new workspace" —
      // `UserMenu.tsx`), and both invite-accept flows obey it. This path was
      // the one rebind that didn't, and ~10 mount-only consumers are written
      // against the reload invariant: WorkspaceDangerZone's owner-only destructive
      // verbs, WorkspaceMembersCard's revoke menus, the shell window state and
      // attention cursor — the last two WRITE the old workspace's values into
      // the new workspace's server-side member_state key, so the corruption
      // outlives the tab.
      //
      // Keying each consumer to the binding was considered and rejected: it is
      // ~10 sites plus every future one, versus one line that restores an
      // invariant the codebase already assumes.
      //
      // Order matters. The in-flight retry runs FIRST and its result is
      // returned, so the call that triggered the heal still resolves normally
      // (the caller sees success, not a torn-down promise); the reload is
      // scheduled after, on a macrotask, so React can commit that result
      // before the navigation. This is also why the reload is not `await`ed.
      const healed = request<T>(endpoint, { ...options, __retriedWithoutWorkspace: true });
      if (typeof window !== "undefined" && !reloadScheduled) {
        reloadScheduled = true;
        // A short delay, not zero: a page load fans out many parallel calls
        // and they all heal at once. This lets the other in-flight retries
        // settle before the navigation, so the reload is the LAST thing that
        // happens rather than a race against them.
        void healed.finally(() => setTimeout(() => window.location.reload(), 150));
      }
      return healed;
    }

    throw new APIError(response.status, response.statusText, data);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null as T;
  }

  return response.json();
}

/** The lane SSE event vocabulary's handler set (ADR-441 D1 — deliberately
 *  separate from the steward's). Shared by send and regenerate (Phase A). */
type LaneStreamHandlers = {
  onDelta: (text: string) => void;
  /** WHO is answering this turn — arrives BEFORE the first delta so the
   *  in-flight bubble is attributed the moment it appears (ADR-495 D3
   *  addressing). Absent for a direct, agent-less conversation. */
  onSpeaker?: (s: { agent_slug: string; reason?: string }) => void;
  /** A tool round started. `subject` is the ONE short label the server chose
   *  for what the call is about (a path, a query) — never the raw arguments.
   *  Undefined for a verb with no meaningful subject, and for any frame from a
   *  server deployed before the step seam. */
  onTool?: (step: { name: string; subject?: string }) => void;
  /** A WriteFile/EditFile landed — render the file inline (artifact card). */
  onArtifact?: (a: { path: string; verb: string }) => void;
  onDone?: (info: {
    rounds: number;
    tools_called: string[];
    artifacts: string[];
    /** WHO answered — also on the terminal frame, because a tool-only turn
     *  yields no delta and would otherwise finalize unattributed. */
    agent_slug?: string;
    /** Present when the turn auto-named a default-named lane (Phase A). */
    lane_name?: string;
    /** True when the turn was a human-to-human broadcast (no engine reply) —
     *  the mount drops its reply placeholder instead of marking "[no reply]". */
    direct?: boolean;
  }) => void;
  onError?: (message: string) => void;
};

/** One lane-turn SSE reader over the shared transport (lib/sse, ADR-441 D4)
 *  — POST, dispatch the lane vocabulary, swallow member aborts (stop is a
 *  control act, not an error; the server persists the partial). */
async function streamLaneTurn(
  path: string,
  body: Record<string, unknown> | null,
  handlers: LaneStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const headers = await getAuthHeaders();
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
  } catch (err) {
    if ((err as Error)?.name === "AbortError") return; // member hit stop
    throw err;
  }
  if (!res.ok || !res.body) {
    handlers.onError?.(`Lane turn failed (${res.status})`);
    return;
  }
  try {
    for await (const evt of sseEvents(res.body)) {
      if (typeof evt.text_delta === "string") handlers.onDelta(evt.text_delta);
      else if (evt.speaker && typeof evt.speaker === "object") {
        handlers.onSpeaker?.(evt.speaker as { agent_slug: string; reason?: string });
      } else if (evt.tool_step && typeof evt.tool_step === "object") {
        const step = evt.tool_step as { name: string; subject?: string | null };
        handlers.onTool?.({ name: step.name, subject: step.subject ?? undefined });
      } else if (typeof evt.tool === "string") {
        // Pre-step-seam server: the name alone. Same handler, no subject.
        handlers.onTool?.({ name: evt.tool });
      }
      else if (evt.artifact && typeof evt.artifact === "object") {
        handlers.onArtifact?.(evt.artifact as { path: string; verb: string });
      } else if (typeof evt.error === "string") handlers.onError?.(evt.error);
      else if (evt.done) {
        handlers.onDone?.({
          rounds: (evt.rounds as number) ?? 0,
          tools_called: (evt.tools_called as string[]) ?? [],
          artifacts: (evt.artifacts as string[]) ?? [],
          agent_slug: typeof evt.agent_slug === "string" ? evt.agent_slug : undefined,
          lane_name: typeof evt.lane_name === "string" ? evt.lane_name : undefined,
          direct: evt.direct === true,
        });
      }
    }
  } catch (err) {
    if ((err as Error)?.name === "AbortError") return; // stopped mid-read
    throw err;
  }
}

/** ADR-495 D1 — a participant in a Conversation. Humans and Agents are one
 *  list: `member_kind` routes the identifier to the right field and pre-selects
 *  a default window; it never decides access (ADR-405 — no rule keys on
 *  species). `visible_from_sequence` is the window: 0 = full history. */
export interface Participant {
  member_kind: 'human' | 'agent';
  principal_id: string | null;
  agent_slug: string | null;
  visible_from_sequence: number;
  invited_by?: string;
  created_at?: string;
}

// ADR-569 — string shapes (mirror api/routes/strings.py). A STRING is the
// member's designation of one file as kept current: {folder}/_string.yaml +
// CONTRACT.md, the designated target leaf revised by the standing run.
export interface StringSource {
  id: string;
  /** An HTTP pull source. Exactly one of `url` / `connector`+`selector`. */
  url?: string | null;
  /** A connector slice (ADR-582 D6 / ADR-594): reach with a receipt. */
  connector?: string | null;
  selector?: string | null;
  /** ADR-595 D3 enrichment — the source as a party (desk view only; the
   *  roster list leaves these unset). */
  last_landed_at?: string | null;
  last_landed_path?: string | null;
  /** Connector sources: is the selector inside the connection's aperture?
   *  null/undefined for HTTP sources. */
  in_aperture?: boolean | null;
  last_contributed_at?: string | null;
}

export interface StringSummary {
  topic: string; // the folder path relative to /workspace/
  declaration_path: string;
  target: string; // the designated leaf, folder-relative
  target_path?: string | null; // absolute, present once the file exists
  format?: 'md' | 'csv' | 'json' | 'txt' | null;
  schedule?: string | string[] | null;
  paused: boolean;
  sources: StringSource[];
  /** ADR-569 D2 — what the file must stay true to (CONTRACT.md). */
  contract?: string | null;
  last_run_at?: string | null;
  next_run_at?: string | null;
  /** Parseable-but-cannot-run (D3, served loudly): missing_target |
   *  invalid_target | unsupported_format | sources_invalid. */
  problem?: string | null;
}

export interface StringView extends StringSummary {
  /** ADR-595 D1 — the tending surface never serves the maintained file's
   *  contents. Head FACTS ride instead; reading happens through the Open
   *  door at the file's own surface. */
  head_updated_at?: string | null;
  head_lines?: number | null;
  head_bytes?: number | null;
  /** The machine-checkable half of the contract (csv columns / json keys). */
  shape: { columns?: string[]; keys?: string[] };
  recent_runs: Array<{
    slug: string;
    status: string;
    created_at?: string | null;
    error_reason?: string | null;
  }>;
  /** The last write REFUSED (shape violation et al.) — read from the ledger,
   *  cleared by the next success. */
  repair?: { reason: string; detail?: string | null; at?: string | null } | null;
  /** D5 — which files cite this leaf (derived at read time, never stored). */
  consumers: string[];
}

/** A string topic is a meaning-folder path (ADR-565 D3) — encode each segment,
 *  keep the '/' separators so the server's `{topic:path}` param reads it. */
const encodeTopic = (topic: string) =>
  topic.split("/").map(encodeURIComponent).join("/");

export const api = {
  // ADR-411 (ADR-408 D6): chat lanes — model-pinned helper threads per
  // member over the shared workspace. `enabled` reflects MODEL_ROUTER_ENABLED
  // server-side; the drawer shows the lane strip only when true.
  // ADR-495 — the `rooms` client is GONE. A room was never a second object:
  // a Conversation is participants + turns, and the participant verbs live on
  // `lanes` below (`participants` / `addParticipant` / `removeParticipant`).

  lanes: {
    /** `includeBound` (2026-07-16): bound (Studio) lanes leave the /chat list —
     *  /chat is Think; a bound lane is Make-work with a text interface and
     *  lives where its artifact does. Studio passes true to see its own. */
    list: (includeBound = false) =>
      request<{
        enabled: boolean;
        /** ADR-460 D4 — the chooser: named colleagues, not a spec sheet. */
        agents: Array<{ slug: string; name: string; blurb: string; icon: string }>;
        /** ADR-562 — the app registry, served from the app's own declaration
         *  (`services/apps/*` → `register_app`). `name` is the app's label for
         *  its resident ("Writer" in Docs), empty when it did not rename one.
         *  Served rather than mirrored here: a TS copy is the second home
         *  ADR-562 deleted. */
        apps?: Array<{ slug: string; resident: string; name: string }>;
        /** ADR-600 D6 / ADR-601 D4 — every being, with provenance and the
         *  desks it serves. `agents` above is who may be INVITED (`offered`);
         *  this is who EXISTS. `kernel` = yarnnn authored it (rendered from
         *  the FIELD, never inferred from absence). `homes` is a LIST —
         *  many-to-one is ordinary, and empty means it serves no desk. */
        beings?: Array<{ slug: string; name: string; blurb: string; icon: string;
          offered: boolean; kernel: boolean; homes: string[]; model?: string }>;
        models: Array<{ id: string; label: string; vision?: boolean;
          /** ADR-559 D3 — false when the engine cannot run right now.
           *  Served (not filtered) so the door can grey it WITH a reason. */
          available?: boolean; unavailable_reason?: string | null }>;
        /** id → label for EVERY engine, retired included — the NAMING table.
         *  `models` above is the CHOOSER (offered rows only), so a lane pinned
         *  to a retired engine has no row there and used to render its RAW ID.
         *  Two audiences, two fields (ADR-559 D2). Optional: an older envelope
         *  must degrade to the previous behaviour, not crash. */
        model_names?: Record<string, string>;
        /** ADR-450 D5 — the Learn-from chooser payload (kernel recipes). */
        recipes: Array<{ slug: string; label: string; description: string; accepts: string[] }>;
        lanes: Array<{
          id: string;
          name: string;
          model: string;
          /** ADR-460 D4 — WHO this lane talks to (absent on pre-registry and
           *  Studio/derive lanes; the UI falls back to the model label). */
          agent?: string | null;
          /** Phase-A hygiene: pinned lanes sort first. */
          pinned?: boolean;
          /** ADR-440 D3 — the Studio binding (null for plain chat lanes). */
          artifact_path?: string | null;
          /** ADR-567 D4 — WHICH APP this lane belongs to. Served since 567 but
           *  absent from this type until 2026-08-28, so `DeskHousing` could
           *  only match a bound lane on its PATH — and two desks may legitimately
           *  bind the same file (a .md is both Text's document and Strings'
           *  maintained file). The Strings desk then adopted the Text lane and
           *  showed Editor where Supervisor belonged. */
          app?: string | null;
          /** ADR-450 D3 — the derive binding (null for plain chat lanes). */
          derive_recipe?: string | null;
          derive_source?: string | null;
          status: string;
          created_at: string;
          updated_at: string;
          summary?: string | null;
          /** ADR-495 D1 — the cast rides on every row: the list shows WHO is
           *  in each conversation. Absent only if the row predates the fold. */
          participants?: Participant[];
        }>;
        // The param has to REACH the server. It was accepted, typed, and
        // dropped — so Studio asked for its bound lanes, the API filtered
        // every one of them out, `boundLane` stayed null, and the create
        // effect fired again on each refresh: six duplicate lanes for one
        // document and a spinner that said "Preparing the authoring lane…"
        // forever, while six prepared lanes sat in the table.
      }>(`/api/lanes${includeBound ? '?include_bound=1' : ''}`),
    create: (data: {
      /** Optional since Phase A — a nameless lane auto-names on first turn. */
      name?: string;
      /** ADR-562 D3 — WHICH APP is creating this bound lane (`studio` |
       *  `docs` | `images`). The RESIDENT is resolved server-side from the
       *  app's own declaration (`services/apps/*`); the client never names a
       *  colleague. Bound lanes only — passing it unbound is a 422 (ADR-558). */
      app?: string;
      /** ADR-614 D1 — the colleague the member picked at the door. Chat lanes
       *  only: it SEEDS THE CAST (the same act as adding them from CastBar),
       *  and the engine is resolved from the being server-side. A bound lane's
       *  colleague is its app's resident and is never sent from here. */
      agent?: string;
      /** The engine directly. Optional when `agent` is given — the engine
       *  rides behind the name — and still the whole answer for a member who
       *  came for a raw engine. */
      model?: string;
      artifact_path?: string;
      /** ADR-450 D3 — the derive binding (pass both or neither). */
      derive_recipe?: string;
      derive_source?: string;
    }) =>
      request<{
        id: string;
        name: string;
        model: string;
        agent?: string | null;
        artifact_path?: string | null;
        status: string;
      }>("/api/lanes", { method: "POST", body: JSON.stringify(data) }),
    messages: (laneId: string) =>
      request<{
        messages: Array<{
          id: string;
          role: "user" | "assistant";
          content: string;
          created_at: string;
          metadata: Record<string, unknown>;
        }>;
      }>(`/api/lanes/${laneId}/messages`),
    // makeAgent/editAgent (the "make your own" hiring doors, /api/lane-agents)
    // are DELETED by ADR-599 D2 with the member-agent machinery. If member
    // agents return, they return app-paired (ADR-596 scaffold).
    /**
     * Streaming lane turn (ADR-412 D2), over the shared reader (ADR-441 D4).
     * Phase-A turn controls: `opts.signal` aborts the stream (stop — the
     * server persists the partial); `opts.replaceFromMessageId` is
     * edit-and-resend (transcript-tail truncate before the turn).
     */
    sendStream: (
      laneId: string,
      content: string,
      handlers: LaneStreamHandlers,
      opts?: {
        signal?: AbortSignal;
        replaceFromMessageId?: string;
        /** Phase-A attachments: raw upload refs this turn carries. */
        attachments?: Array<{ path: string; kind: "image" | "file"; name?: string }>;
        /** ADR-522 D2: what the member is looking at — per-turn, because focus
         *  is volatile. The durable lane↔artifact binding is separate. */
        focus?: FocusWire;
        /** ADR-579 D7: the gesture target this send carries (snake_case wire
         *  form) — stamped on the row, rendered into the frame. */
        seed?: Record<string, unknown>;
      },
    ): Promise<void> =>
      streamLaneTurn(
        `/api/lanes/${laneId}/messages`,
        {
          content,
          ...(opts?.replaceFromMessageId
            ? { replace_from_message_id: opts.replaceFromMessageId }
            : {}),
          ...(opts?.attachments?.length ? { attachments: opts.attachments } : {}),
          ...(opts?.focus ? { focus: opts.focus } : {}),
          ...(opts?.seed ? { seed: opts.seed } : {}),
        },
        handlers,
        opts?.signal,
      ),
    /** Phase-A turn controls: re-run the last user message's turn (the
     *  discarded reply's substrate writes stand — the no-rewind rule). */
    regenerateStream: (
      laneId: string,
      handlers: LaneStreamHandlers,
      opts?: { signal?: AbortSignal },
    ): Promise<void> =>
      streamLaneTurn(`/api/lanes/${laneId}/regenerate`, null, handlers, opts?.signal),
    /** Phase-A hygiene: rename / pin. */
    patch: (laneId: string, data: { name?: string; pinned?: boolean }) =>
      request<{ id: string; name: string; pinned: boolean }>(`/api/lanes/${laneId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    /** Phase-A hygiene: transcript search across the member's active lanes. */
    search: (q: string) =>
      request<{ matches: Array<{ lane_id: string; snippet: string }> }>(
        `/api/lanes/search?q=${encodeURIComponent(q)}`,
      ),
    archive: (laneId: string) =>
      request<{ success: boolean }>(`/api/lanes/${laneId}/archive`, {
        method: "POST",
      }),
    /** ADR-495 D1 — the cast. One list: humans and Agents together. */
    participants: (laneId: string) =>
      request<{ participants: Participant[] }>(`/api/lanes/${laneId}/participants`),
    /** ADR-495 D3 — ONE species-blind invite. `visibleFromSequence` is the
     *  visibility window (omit → the class default: Agent full history, human
     *  from now); 0 is an explicit "share everything". */
    addParticipant: (
      laneId: string,
      data: {
        kind: "human" | "agent";
        principal_id?: string;
        agent_slug?: string;
        visible_from_sequence?: number;
      },
    ) =>
      request<{ added: boolean; participant: Participant; participants: Participant[] }>(
        `/api/lanes/${laneId}/participants`,
        { method: "POST", body: JSON.stringify(data) },
      ),
    /** Ends FUTURE read access; it does not un-read what was already seen. */
    removeParticipant: (
      laneId: string,
      sel: { principal_id?: string; agent_slug?: string },
    ) => {
      const qs = sel.principal_id
        ? `principal_id=${encodeURIComponent(sel.principal_id)}`
        : `agent_slug=${encodeURIComponent(sel.agent_slug || "")}`;
      return request<{ removed: boolean; participants: Participant[] }>(
        `/api/lanes/${laneId}/participants?${qs}`,
        { method: "DELETE" },
      );
    },
  },

  // ADR-612 — which of the member's granted connectors a being works against.
  // NOT an edit to the being (its row is kernel data, ADR-460 D3.a): this is
  // the member's own preference, keyed (workspace, principal).
  agentConnectors: {
    /** Every being's opt-in, plus the platforms there are to opt INTO. A being
     *  absent from `opt_in` is NOT scoped — it reaches everything granted. */
    get: () =>
      request<{
        available: string[];
        opt_in: Record<string, string[]>;
      }>("/api/agent-connectors"),
    /** `platforms: null` clears the scoping (back to everything granted);
     *  `[]` is the different, real choice of "reaches nothing". */
    set: (agentSlug: string, platforms: string[] | null) =>
      request<{ saved: boolean; opt_in: Record<string, string[]> }>(
        `/api/agent-connectors/${encodeURIComponent(agentSlug)}`,
        { method: "PUT", body: JSON.stringify({ platforms }) },
      ),
  },

  // ADR-569 — strings, the maintained file kept under contract. Declarations
  // are conversational (the desk's colleague authors them through its lane —
  // no create route);
  // these are the projections the desk reads plus the direct switches.
  strings: {
    list: () => request<StringSummary[]>("/api/strings"),
    get: (topic: string) =>
      request<StringView>(`/api/strings/${encodeTopic(topic)}`),
    update: (topic: string, data: { paused?: boolean }) =>
      request<StringSummary>(`/api/strings/${encodeTopic(topic)}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    /** Run now — the manual fire (D7). */
    run: (topic: string) =>
      request<{ success: boolean; no_change?: boolean; error_reason?: string; detail?: string }>(
        `/api/strings/${encodeTopic(topic)}/run`,
        { method: "POST" },
      ),
  },

  // ADR-440 — the Studio (the first authoring app). Templates are kernel
  // constants server-side; creation writes the skeleton as the artifact's
  // first revision (authored_by=operator). Everything after creation flows
  // through existing machinery (bound lanes + GET /api/workspace/file).
  studio: {
    /** ADR-473 D2/D3: each row carries the app that OWNS the type, so a
     *  surface offers only its own shapes without hardcoding a slug list. */
    templates: () =>
      request<{
        templates: Array<{
          slug: string;
          label: string;
          description: string;
          app: string;
        }>;
      }>("/api/studio/templates"),
    // ADR-459: `name` + `kind` are COMPUTED server-side, never stored — the
    // kind lifted from the artifact's own `data-template`, the name titleized
    // from its meaning folder. `kind` is an opaque slug (a bundle may ship one
    // the FE has no icon for; `kind_label` still reads correctly).
    /** ADR-473 D4: `app` scopes to the types that app owns (the Finder/Preview
     *  behavior). Omitted → every artifact, which is what Files wants. */
    artifacts: (app?: string) =>
      request<{
        artifacts: Array<{
          path: string;
          updated_at: string | null;
          summary: string | null;
          name: string;
          kind: string | null;
          kind_label: string;
        }>;
      }>(`/api/studio/artifacts${app ? `?app=${encodeURIComponent(app)}` : ""}`),
    // `head_version_id` is the citation's PIN (ADR-440 D5) — carried here so a
    // mechanical insert can stamp it at the moment the citation is made. Null
    // for a file predating the ADR-209 chain.
    citable: () =>
      request<{
        images: Array<{ path: string; updated_at: string | null; head_version_id: string | null }>;
        tables: Array<{ path: string; updated_at: string | null; head_version_id: string | null }>;
        // ADR-583 — the component library (`*.component.html` fragments).
        components: Array<{
          path: string;
          updated_at: string | null;
          head_version_id: string | null;
        }>;
      }>("/api/studio/citable"),
    // ADR-479 D1: the re-arrangement's PLACEMENT decision, as judgment. Sends
    // the page's blocks + the target arrangement's declared slots; gets back a
    // slot per block — never markup. `placements: null` is a REFUSAL, not an
    // error: the caller falls back to the mechanical ladder (ADR-468 D4, a
    // re-arrangement must never dead-end). Validated server-side against the
    // closed slot vocabulary with total block coverage (D2), so a plan can no
    // longer lose content.
    // ADR-544 D6 — the wire speaks AREAS (roles heading|body|media|aside), the
    // same vocabulary the served registry hands the FE. No `slots` alias: the
    // only caller is our own surface, shipped from the same commit.
    planArrangement: (body: {
      blocks: Array<{ id: string; kind: string; text: string }>;
      areas: Array<{ name: string; role: string; place?: string }>;
      arrangement?: string;
    }) =>
      request<{ placements: Array<{ block_id: string; area: string }> | null }>(
        "/api/studio/arrangement/plan",
        { method: "POST", body: JSON.stringify(body) },
      ),
    // ADR-443 R4 + ADR-444 + ADR-447 + ADR-453: the ONE kernel vocabulary
    // (blocks + layouts + arrangements + property TOKENS + the marked kernel
    // style element + design-system discovery) — palette, galleries, and the
    // Design tab render AND EXECUTE from the same source the posture teaches
    // from. `fragment` is the deterministic insertion payload; `grain`/`slots`
    // carry the arrangement's composition shape (thumbnails derive from them;
    // slot `role` gates what can land in a slot).
    // The type is the ONE StudioVocabulary (ADR-461 D4 added `measures`) —
    // hand-restating it here let the two drift, which is how a served field can
    // exist on the endpoint and be invisible to its own consumer.
    vocabulary: () => request<StudioVocabulary>("/api/studio/vocabulary"),
    // ADR-453 D4 (the Design tab's Apply): compose one design system's MARKED
    // skin element server-side (ADR-449 contract); the FE lands it through the
    // mechanical write door (applySkin) — the endpoint never writes.
    resolveDesignSystem: (manifestPath: string) =>
      request<{
        name: string;
        manifest_path: string;
        skin_element: string;
        // DESIGN-SYSTEMS.md §6 — the manage panel reads these (additive; Apply
        // only uses skin_element).
        sources: string[];
        maps: Record<string, string>;
        warnings: string[];
      }>(
        `/api/studio/design-systems/resolve?manifest=${encodeURIComponent(manifestPath)}`,
      ),
    /** ADR-487 D5 — set/clear the workspace-default design system (null
     *  clears). An inheritance rule at creation; nothing existing is touched. */
    setDefaultDesignSystem: (manifestPath: string | null) =>
      request<{ ok: boolean; default_design_system: string | null }>(
        "/api/studio/design-systems/default",
        { method: "POST", body: JSON.stringify({ manifest: manifestPath }) },
      ),
    /** ADR-462 D14 — import a design-system export (.zip) → a conforming
     *  meaning-folder. Multipart, so it cannot ride `request` (which sets a
     *  JSON content-type); the boundary must be the browser's own. Returns
     *  the receipt WITH its warnings — an import that half-lands silently is
     *  the failure this arc exists to prevent, so the caller shows them. */
    importDesignSystem: async (file: File, name?: string) => {
      const headers = await getAuthHeaders();
      delete (headers as Record<string, string>)["Content-Type"];
      const formData = new FormData();
      formData.append("file", file);
      if (name) formData.append("name", name);
      const response = await fetch(`${API_BASE_URL}/api/studio/design-systems/import`, {
        method: "POST",
        credentials: "include",
        headers,
        body: formData,
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new APIError(response.status, response.statusText, data);
      }
      return response.json() as Promise<{
        ok: boolean;
        name: string;
        manifest_path: string;
        entry: string;
        written: string[];
        sources: string[];
        fonts: string[];
        skipped: string[];
        warnings: string[];
      }>;
    },
    // ADR-444/447: the mechanical write door — deterministic structural ops
    // (insert block / add arrangement / re-arrange) computed FE-side, landed
    // as ONE operator-attributed CAS-guarded revision (409 on a stale base).
    writeArtifact: (path: string, content: string, expectedHeadVersionId: string | null, message: string) =>
      request<{ success: boolean; path: string; head_version_id: string }>("/api/studio/artifacts/write", {
        method: "POST",
        body: JSON.stringify({
          path,
          content,
          expected_head_version_id: expectedHeadVersionId,
          message,
        }),
      }),
    /** Create an artifact. Two doors (ADR-470):
     *   • IMMEDIATE — `template` only. The server places it and the skeleton's
     *     "Untitled ‹kind›" placeholder stands; the member names it from the
     *     work (or never).
     *   • DELIBERATE — `path` + `name` too, for the member who arrives knowing.
     *
     *  `name` is what they TYPED (ADR-469): it becomes the <title> verbatim, so
     *  `IR deck v3` and `한글 문서` read back exactly as typed while the path
     *  stays an ASCII key. */
    /** ADR-472 D3: a stage carries real dimensions at birth (preset OR explicit
     *  W×H). Ignored by flow/paged document layouts, which have no pixel box. */
    createArtifact: (
      template: string,
      opts?: {
        path?: string;
        name?: string;
        preset?: string;
        width?: number;
        height?: number;
      },
    ) =>
      request<{ success: boolean; path: string; template: string }>(
        "/api/studio/artifacts",
        { method: "POST", body: JSON.stringify({ template, ...opts }) },
      ),
    /** Rename an artifact by its NAME — which is its MEANING FOLDER, not the
     *  leaf (the leaf is a TYPE marker naming the layout). Moves every file in
     *  the folder, then retitles so the h1 follows. Server-side because the
     *  folder-is-the-name knowledge lives with the layout registry. */
    renameArtifact: (path: string, name: string) =>
      request<{ success: boolean; path: string; renamed: boolean; moved?: number; name?: string }>(
        "/api/studio/artifacts/rename",
        { method: "POST", body: JSON.stringify({ path, name }) },
      ),
    /** Retitle an artifact FROM its filename — the rename half of "the name is
     *  one fact". Server-side because the knowledge that an h1 IS a title lives
     *  with the layout registry. No-ops (retitled:false) on a paged layout or
     *  an already-authored title; a no-op writes no revision. */
    retitleArtifact: (path: string) =>
      request<{ success: boolean; retitled: boolean; reason?: string }>(
        "/api/studio/artifacts/retitle",
        { method: "POST", body: JSON.stringify({ path }) },
      ),
  },

  // ADR-108: User context entries (user-scoped, stored in /system/notes.md)
  userMemories: {
    list: () => request<Array<{
      id: string;
      key: string;
      value: string;
      source: string;
      confidence: number;
      created_at: string;
      updated_at: string;
    }>>("/api/memory/user/memories"),
    create: (data: { content: string; entry_type?: string }) =>
      request<{
        id: string;
        key: string;
        value: string;
        source: string;
        confidence: number;
        created_at: string;
        updated_at: string;
      }>("/api/memory/user/memories", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    importBulk: (data: BulkImportRequest) =>
      request<{ memories_extracted: number }>("/api/memory/user/memories/import", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  // Memory/Entries management
  memories: {
    update: (memoryId: string, data: MemoryUpdate) =>
      request<Memory>(`/api/memory/memories/${memoryId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (memoryId: string) =>
      request<DeleteResponse>(`/api/memory/memories/${memoryId}`, {
        method: "DELETE",
      }),
  },

  // ADR-133: Profile — reads/writes /workspace/IDENTITY.md
  profile: {
    get: () =>
      request<{
        name?: string;
        role?: string;
        company?: string;
        timezone?: string;
        summary?: string;
      }>("/api/memory/profile"),
    update: (data: {
      name?: string;
      role?: string;
      company?: string;
      timezone?: string;
      summary?: string;
    }) =>
      request<{
        name?: string;
        role?: string;
        company?: string;
        timezone?: string;
        summary?: string;
      }>("/api/memory/profile", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  },

  // ADR-244 (2026-05-01): api.onboarding deleted — `getState` migrated into
  // the existing api.workspace namespace below (workspace lifecycle is the
  // canonical name; the OnboardingModal lived for the duration of signup,
  // the surface lives forever). Singular implementation: one canonical
  // state read, one canonical namespace.

  // ADR-432 D1c (2026-07-09): the `api.brand` namespace is DELETED. Brand is
  // retired — operation/BRAND.md was read by no producing path (its home is
  // per-agent output-styling when a hired agent needs it, ADR-432 D1b).

  // ADR-144: Identity (workspace IDENTITY.md — replaces profile fields)
  identity: {
    get: () =>
      request<{ content: string | null; exists: boolean }>(
        "/api/memory/user/identity"
      ),
    save: (content: string) =>
      request<{ exists: boolean }>(
        "/api/memory/user/identity",
        { method: "POST", body: JSON.stringify({ content }) },
      ),
  },

  // Document endpoints (ADR-249: persistent uploads → /workspace/uploads/*.md)
  documents: {
    // List workspace uploads
    list: () => request<WorkspaceUploadListResponse>("/api/documents"),

    // ADR-331 D5: persistent upload — one or more files (+ .zip) in one call.
    // Accepts a single File or a File[]; returns a batch result (per-file
    // success/error). A .zip is expanded server-side. Non-transactional.
    // `destination` (ADR-555) — the workspace-relative folder the member
    // dropped on. Omitted, the arrival lands in the intake lane exactly as
    // before, so every existing caller is unchanged.
    upload: async (fileOrFiles: File | File[], destination?: string | null) => {
      const files = Array.isArray(fileOrFiles) ? fileOrFiles : [fileOrFiles];
      const headers = await getAuthHeaders();
      delete (headers as Record<string, string>)["Content-Type"];
      const formData = new FormData();
      for (const f of files) formData.append("files", f);
      if (destination) formData.append("destination", destination);
      const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
        method: "POST",
        credentials: "include",
        headers,
        body: formData,
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new APIError(response.status, response.statusText, data);
      }
      return response.json() as Promise<WorkspaceUploadResponse>;
    },

    // Get signed download URL — documentPath is the workspace path e.g. /workspace/uploads/foo.md
    download: (documentPath: string) =>
      request<DocumentDownloadResponse>(`/api/documents${documentPath}/download`),

    // ADR-395: resolve a raw upload's content_url (/api/documents/blob?storage_path=…)
    // to a fresh signed URL via an AUTHENTICATED fetch (the Bearer header rides on
    // `request`). The FE then points img/iframe/download `src` at the returned
    // signed URL directly — a browser-native element request can't send the header,
    // so it must resolve the URL here first. `contentUrl` is the stored relative
    // reference; we forward its storage_path query verbatim.
    blobUrl: (contentUrl: string) => {
      const qs = contentUrl.includes("?") ? contentUrl.slice(contentUrl.indexOf("?")) : "";
      // Only the ?storage_path= form is resolvable (ADR-395). A content_url
      // that lacks it — a retired ?token= reference, an empty string, an
      // absolute URL that slipped through — would hit the endpoint with a
      // param it 404s on, and the BROWSER logs that failed request to the
      // console whether or not the promise is caught (a network-layer log, not
      // a JS throw). So don't send it: reject locally with a shape the caller
      // already try/catches into a graceful fallback (operator-observed console
      // flood on an open deck, 2026-07-24).
      if (!/[?&]storage_path=/.test(qs)) {
        return Promise.reject(new Error("blobUrl: content_url has no storage_path"));
      }
      return request<{ url: string; expires_in: number }>(`/api/documents/blob${qs}`);
    },

    // ADR-448: the reference edge, read outward — which files' head revision
    // was made FROM this path. Serves the delete-confirm "N other files were
    // made from this one" line. Best-effort: the backend returns {count: 0}
    // on any lookup failure, never an error the FE must handle.
    dependents: (path: string) =>
      request<{ path: string; dependents: Array<{ path: string }>; count: number }>(
        `/api/workspace/file/dependents?path=${encodeURIComponent(path)}`
      ),

    // Delete an uploaded file (operator-facing 'Delete'). Trash-semantics,
    // not erasure: the backend archives via lifecycle (ADR-209 retention,
    // reversible) and scopes to operator-owned uploads/ (ADR-320 topology).
    delete: (documentPath: string) =>
      request<{ success: boolean; message: string; archived?: boolean }>(
        `/api/documents${documentPath}`,
        { method: "DELETE" }
      ),

    // ADR-400: the Trash surface — list operator-owned archived files.
    // TWO SHAPES, because there are two acts: a file trashed on its own is an
    // `item`; a FOLDER trashed is a `group` (one restorable unit naming its
    // deleted root). Members of a group are NOT repeated in `items` — Trash
    // shows one row per thing the operator deleted, not per file the fan wrote.
    trash: () =>
      request<{
        items: Array<{ path: string; filename: string; archived_at: string; authored_by: string | null }>;
        groups: Array<{ root: string; name: string; count: number; archived_at: string }>;
      }>("/api/documents/trash"),

    // ADR-400 D8: restore a file from Trash (un-archive → active).
    restore: (path: string) =>
      request<{ success: boolean; message: string; path: string }>(
        "/api/documents/restore",
        { method: "POST", body: JSON.stringify({ path }) }
      ),

    // ADR-478: permanently delete ONE trashed file. Unrecoverable, owner-gated,
    // refused if a live file cites it (409 with the dependents named).
    permanentDelete: (path: string) =>
      request<{ success: boolean; message: string; path: string; revisions: number; blobs: number }>(
        "/api/documents/permanent-delete",
        { method: "POST", body: JSON.stringify({ path }) }
      ),

    // ADR-478: empty the trash — permanently delete every archived file in reach.
    // Cited files are skipped (not fatal) and reported back.
    emptyTrash: () =>
      request<{ success: boolean; message: string; deleted: number; skipped: string[] }>(
        "/api/documents/trash/empty",
        { method: "POST" }
      ),

    // ADR-400 D2: move or rename an operator-owned file (both roots scoped).
    move: (path: string, newPath: string) =>
      request<{ success: boolean; path: string }>(
        "/api/documents/move",
        { method: "POST", body: JSON.stringify({ path, new_path: newPath }) }
      ),

    // ADR-514 D2.4: bind this file's default handler (the Get Info "Open
    // with:" row). Per-FILE only — per-type config is deferred. Pass null to
    // clear and fall back to the registry default. Metadata-only: no revision
    // is minted, because a launch preference is not an authored act.
    setLaunchHandler: (path: string, handlerId: string | null) =>
      request<{ success: boolean; path: string; handler_id: string | null }>(
        "/api/documents/launch-handler",
        { method: "POST", body: JSON.stringify({ path, handler_id: handlerId }) }
      ),

    // ADR-514 D1: duplicate a file as an attributed derivation. The caller
    // names only the source — the kernel resolves the free `-copy` sibling and
    // writes derived_from, so the copy traces back to its original.
    duplicate: (path: string) =>
      request<{ success: boolean; path: string; new_path: string }>(
        "/api/documents/duplicate",
        { method: "POST", body: JSON.stringify({ path }) }
      ),

    // ADR-424 D2: create a folder — a top-level PEER (no parent) or INSIDE an
    // existing folder (parent = its workspace-relative path, sent verbatim so
    // the backend never re-sanitizes existing segments).
    // ADR-588 D1: the backend writes a FOLDER MARKER row, not a seeded file, so
    // there is nothing to open afterwards — `path` is the folder itself. The
    // `seeded` field is GONE; the caller stays where it is and selects `path`.
    createFolder: (path: string, parent?: string | null) =>
      request<{ success: boolean; path: string }>(
        "/api/documents/folder",
        { method: "POST", body: JSON.stringify(parent ? { path, parent } : { path }) }
      ),

    // ── FOLDER VERBS (2026-08-21) — a folder verb is a FAN-OUT ────────────
    //
    // Since ADR-588 a folder is a marker row plus whatever files share its path
    // prefix, so Rename / Move / Move-to-Trash on a folder cannot be one row
    // update — the backend fans out over the subtree, one attributed revision
    // per file through the ONE write path (ADR-209).

    // What the verb WOULD touch. Resolved when the menu OPENS, so the label can
    // name the blast radius before the click ("Move to Trash (40 items)"). The
    // count and the act share one enumeration server-side, so the number shown
    // is the number performed. `locked` names the files a carve will leave in
    // place — reported, never silently skipped.
    folderPreflight: (path: string) =>
      request<{
        path: string;
        count: number;
        locked: string[];
        folders: number;
        too_large: boolean;
      }>(`/api/documents/folder/preflight?path=${encodeURIComponent(path)}`),

    // Move a FOLDER to Trash — one archive revision per file, restorable as ONE
    // unit (the fan stamps a grouping key Trash reads back). A POST, not a
    // DELETE on the path: the single-file DELETE already claims that shape.
    trashFolder: (path: string) =>
      request<{
        success: boolean;
        message: string;
        root: string;
        archived: string[];
        locked: string[];
      }>("/api/documents/folder/trash", {
        method: "POST",
        body: JSON.stringify({ path }),
      }),

    // Move or RENAME a folder — the same fan-out, addressed differently (rename
    // is a move to a sibling path). Reports the honest partial.
    moveFolder: (path: string, newPath: string) =>
      request<{
        success: boolean;
        message: string;
        path: string;
        moved: string[];
        failed: string[];
        locked: string[];
      }>("/api/documents/folder/move", {
        method: "POST",
        body: JSON.stringify({ path, new_path: newPath }),
      }),

    // Restore a whole trashed folder in one act — addressed by the grouping key,
    // never by a path prefix (a file trashed separately AFTER the folder went
    // would match the prefix but was not part of that act).
    restoreTrashGroup: (root: string) =>
      request<{ success: boolean; message: string; root: string; restored: string[] }>(
        "/api/documents/trash/restore-group",
        { method: "POST", body: JSON.stringify({ root }) }
      ),

    // ADR-127: Share file to global user_shared/ staging area
    shareFile: (filename: string, content: string) =>
      request<{ success: boolean; path: string; filename: string; message: string }>(
        "/api/share",
        { method: "POST", body: JSON.stringify({ filename, content }) }
      ),
  },

  // Chat endpoints (streaming handled separately in useChat hook)
  chat: {
    // Commit H (2026-05-11): cooperative cancellation of an in-flight
    // Reviewer Loop. Sets chat_sessions.cancellation_requested=true on
    // the operator's active workspace session; the Reviewer's tool-use
    // loop checks the flag at the top of every round and exits early
    // with stand_down on true.
    cancel: () =>
      request<{ ok: boolean; applied: boolean; session_id?: string; reason?: string }>(
        "/api/feed/cancel",
        { method: "POST" },
      ),

    // Ephemeral file attach — ADR-249. Returns {type, file_id?, filename, mime_type?}
    // or {type: "text_block", filename, content} for DOCX.
    attach: async (file: File): Promise<{
      type: "file_id" | "text_block";
      file_id?: string;
      filename: string;
      mime_type?: string;
      content?: string;
    }> => {
      const headers = await getAuthHeaders();
      delete (headers as Record<string, string>)["Content-Type"];
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE_URL}/api/feed/attach`, {
        method: "POST",
        credentials: "include",
        headers,
        body: formData,
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new APIError(response.status, response.statusText, data);
      }
      return response.json();
    },

    // Get global chat history
    globalHistory: (limit: number = 1, agentId?: string, taskSlug?: string) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (agentId) params.set('agent_id', agentId);
      if (taskSlug) params.set('task_slug', taskSlug);
      return request<{
        sessions: Array<{
          id: string;
          created_at: string;
          messages: Array<{
            id: string;
            role: string;
            content: string;
            sequence_number: number;
            created_at: string;
            metadata?: {
              tool_history?: Array<{
                type: string;
                name?: string;
                input_summary?: string;
                result_summary?: string;
                content?: string;
                /** ADR-399: interim reasoning segments (type='reasoning') */
                text?: string;
              }>;
              tools_used?: string[];
              // ADR-124: Author attribution for meeting room messages
              author_agent_id?: string;
              author_agent_slug?: string;
              author_role?: string;
              // ADR-179: System event cards
              system_card?: string;
              agents_created?: number;
              tasks_created?: string[];
              task_slug?: string;
              task_title?: string;
              output_path?: string;
              run_at?: string;
              // ADR-212: Reviewer verdict cards (role === 'freddie')
              proposal_id?: string;
              verdict?: string;
              occupant?: string;
              action_type?: string;
              // ADR-219 Commit 2: narrative envelope stamped on every
              // session_messages row by services.narrative.write_narrative_entry.
              // Loader pulls these into TPMessage.narrative; renderer
              // dispatches on `weight` per ADR-219 D5.
              summary?: string;
              pulse?: 'periodic' | 'reactive' | 'addressed' | 'heartbeat';
              // ADR-277: housekeeping retired (no live emission path).
              // Pre-ADR-277 stored rows with weight='housekeeping' coerce
              // to 'routine' on read in ConversationPanel; surfacing the
              // legacy value in the wire type would re-leak it into the FE.
              weight?: 'material' | 'routine';
              invocation_id?: string;
              // ADR-377: boundary-direction signal. `written_to` is the
              // substrate path a foreign/inbound write landed at (MCP
              // `remember`, connector sync, upload) — its presence marks an
              // INBOUND crossing. `tool` is the MCP verb (remember/recall/
              // trace) so reads can be told from writes. `outcome` is the
              // success/failure of the boundary act. Surfaced so the Context
              // In/Out/Flow views can derive direction FE-side.
              written_to?: string;
              tool?: string;
              outcome?: string;
              // Actor identity (2026-06-30): the ADR-209 authored_by taxonomy,
              // stamped on every narrative row by write_narrative_entry. The FE
              // attribution module + PrincipalBadge map it to the actor's label
              // + icon so chat/Flow/Notifications show who acted by name.
              authored_by?: string;
              // ADR-219 Commit 3: narrative_digest rollup card
              rolled_up_count?: number;
              rolled_up_window_hours?: number;
              rolled_up_ids?: string[];
              counts?: { material?: number; routine?: number; housekeeping?: number };
            };
          }>;
        }>;
      }>(`/api/feed/history?${params.toString()}`);
    },

  },

  // Billing endpoints (Lemon Squeezy)
  // ADR-396: Type-B subscription over the metered balance. The plan tier
  // (starter/pro) grants a monthly allowance; a dynamic top-up (any amount) is
  // the overage pool beneath it. Draw order: allowance → balance → hard-stop.
  subscription: {
    getStatus: () => request<SubscriptionStatus>("/api/subscription/status"),

    // Dynamic top-up: any dollar amount (server bounds it $5–$500), priced via
    // Lemon Squeezy custom_price.
    createTopup: (amountUsd: number) =>
      request<CheckoutResponse>("/api/subscription/checkout", {
        method: "POST",
        body: JSON.stringify({ checkout_type: "topup", topup_amount: amountUsd }),
      }),

    // Subscribe to a plan tier.
    createSubscription: (tier: "starter" | "pro") =>
      request<CheckoutResponse>("/api/subscription/checkout", {
        method: "POST",
        body: JSON.stringify({ checkout_type: "subscription", tier }),
      }),

    // The LS customer portal. Scoped 2026-07-22 to what the processor genuinely
    // owns — the payment INSTRUMENT (card on file, invoices, receipts). Plan
    // lifecycle is in-app (`cancel` below + `createSubscription` above).
    getPortal: () => request<PortalResponse>("/api/subscription/portal"),

    // Cancel the plan at period end (in-app; no portal bounce). Access runs to
    // `ends_at`; the tier flips on the `subscription_expired` webhook, never here.
    cancel: () =>
      request<CancelResponse>("/api/subscription/cancel", { method: "POST" }),
  },

  // Admin endpoints (requires admin access)
  admin: {
    stats: () => request<AdminOverviewStats>("/api/admin/stats"),
    executionStats: () => request<AdminExecutionStats>("/api/admin/execution-stats"),
    users: () => request<AdminUserRow[]>("/api/admin/users"),
    // ADR-429 §12.3a — toggle a workspace's billing-exempt (comp) state.
    setBillingExempt: (workspaceId: string, exempt: boolean) =>
      request<{ workspace_id: string; billing_exempt: boolean }>(
        `/api/admin/workspace/${encodeURIComponent(workspaceId)}/billing-exempt`,
        { method: "POST", body: JSON.stringify({ exempt }) },
      ),
    accounts: () => request<AdminAccountRow[]>("/api/admin/accounts"),
    accountDetail: (slug: string) =>
      request<AdminAccountDetail>(`/api/admin/accounts/${encodeURIComponent(slug)}`),
    exportUsers: async () => {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/api/admin/export/users`, {
        credentials: "include",
        headers,
      });
      if (!response.ok) {
        throw new APIError(response.status, response.statusText);
      }
      const contentDisposition = response.headers.get("Content-Disposition");
      const filenameMatch = contentDisposition?.match(/filename=(.+)/);
      const filename = filenameMatch ? filenameMatch[1] : "yarnnn_users.xlsx";
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
    exportReport: async () => {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/api/admin/export/report`, {
        credentials: "include",
        headers,
      });
      if (!response.ok) {
        throw new APIError(response.status, response.statusText);
      }
      const contentDisposition = response.headers.get("Content-Disposition");
      const filenameMatch = contentDisposition?.match(/filename=(.+)/);
      const filename = filenameMatch ? filenameMatch[1] : "yarnnn_report.xlsx";
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
  },

  // The `agents` client block is DELETED (2026-08-26). It called the
  // pre-ADR-596 agent model at /api/agents — ADR-109 Scope x Role x Trigger
  // over the `agents` + `agent_runs` tables. Both tables were EMPTY in
  // production and every method here had ZERO call sites. The router is
  // deleted server-side; what an agent IS now is a BEING, served on the lane
  // envelope as `beings` and rendered by components/agents/AgentsSurface.tsx.


  // ADR-225 + ADR-240: Programs — composition surfaces (ADR-225) +
  // activation lifecycle (ADR-240 FE consumption of ADR-226 backend).
  programs: {
    getSurfaces: () => request<{
      schema_version: 1;
      active_bundles: Array<{
        slug: string;
        title: string;
        tagline?: string;
        current_phase?: string | null;
        current_phase_label?: string | null;
        phases: Array<{ key: string; label: string; description?: string }>;
      }>;
      composition: {
        tabs: Record<string, unknown>;
        chat_chips: string[];
      };
    }>("/api/programs/surfaces"),

    // ADR-240 D1: list bundles the operator may activate at signup.
    listActivatable: () =>
      request<{
        schema_version: number;
        programs: Array<{
          slug: string;
          title: string;
          tagline: string | null;
          status: 'active' | 'deferred';
          deferred: boolean;
          oracle: Record<string, unknown>;
          current_phase: string | null;
          current_phase_label?: string | null;
          // ADR-338 D4.5 — installer four-flow preview (see workspace.getState).
          flow_preview: {
            flows: Array<{
              key: 'perception' | 'work_out' | 'outcomes' | 'loop';
              label: string;
              present: boolean;
              summary?: string;
              rationale?: string | null;
            }>;
            capabilities: string[];
            watch_count: number;
            ground_truth: string | null;
          } | null;
        }>;
      }>("/api/programs/activatable"),

    // ADR-240 D1: fork the bundle's reference-workspace into the
    // operator's workspace via the standard authored-substrate path.
    activate: (programSlug: string) =>
      request<{
        schema_version: number;
        activated_program: string;
        files_written: string[];
        files_skipped: string[];
      }>("/api/programs/activate", {
        method: "POST",
        body: JSON.stringify({ program_slug: programSlug }),
      }),

    // ADR-244 D3: soft deactivation — drops the bundle marker on MANDATE.md
    // first heading; operator-authored content stays. Idempotent.
    deactivate: () =>
      request<{
        schema_version: number;
        deactivated: boolean;
        prior_program_slug: string | null;
        reason?: string;
      }>("/api/programs/deactivate", {
        method: "POST",
      }),

    // ADR-312 D9: alpha-trader program data (Home sections). Folded from
    // the legacy /api/cockpit/* namespace into program scope. Auth-scoped
    // only — endpoints derive user_id from session, no path param.
    // ADR-242 + ADR-243 Phase C (live brokerage) + ADR-273 D3 (substrate).
    alphaTrader: {
      moneyTruth: () =>
      request<{
        live: boolean;
        provider?: string;
        paper?: boolean;
        equity?: number;
        cash?: number;
        buying_power?: number;
        day_pnl?: number;
        day_pnl_pct?: number;
        positions_count?: number;
        as_of?: string;
        fallback_reason?: 'no_platform_connection' | 'alpaca_unreachable' | 'no_credentials';
      }>("/api/programs/alpha-trader/money-truth"),

    // ADR-243 Phase C: portfolio equity history for TraderPortfolio chart.
    portfolioHistory: (period = '1M', timeframe = '1D') =>
      request<{
        live: boolean;
        paper?: boolean;
        period?: string;
        timeframe?: string;
        data?: {
          timestamps: number[];
          equity: number[];
          profit_loss: number[];
          profit_loss_pct: number[];
          base_value: number;
        } | null;
        fallback_reason?: string;
      }>(`/api/programs/alpha-trader/portfolio-history?period=${period}&timeframe=${timeframe}`),

    // ADR-243 Phase C: open positions for TraderPositions.
    positions: () =>
      request<{
        live: boolean;
        paper?: boolean;
        positions: Array<{
          symbol: string;
          qty: string;
          side: string;
          market_value: string;
          cost_basis: string;
          avg_entry_price: string;
          current_price: string;
          unrealized_pl: string;
          unrealized_plpc: string;
          change_today: string;
        }>;
        fallback_reason?: string;
      }>("/api/programs/alpha-trader/positions"),

    // ADR-243 Phase C: recent orders for TraderOrders.
    recentOrders: (limit = 10) =>
      request<{
        live: boolean;
        paper?: boolean;
        orders: Array<{
          id: string;
          symbol: string;
          side: string;
          qty: string;
          filled_qty: string;
          type: string;
          time_in_force: string;
          limit_price?: string | null;
          filled_avg_price?: string | null;
          status: string;
          created_at: string;
          filled_at?: string | null;
        }>;
        fallback_reason?: string;
      }>(`/api/programs/alpha-trader/recent-orders?limit=${limit}`),

    // ADR-273 D3: substrate reads — accumulated trading intelligence.
    // Zero LLM, zero platform calls. Each route reads workspace_files
    // directly and parses YAML/markdown frontmatter.
    regime: () =>
      request<{
        live: boolean;
        as_of?: string;
        trend_regime?: 'uptrend' | 'downtrend' | 'chop' | string;
        vix_regime_active?: boolean;
        deactivation_streak_days?: number;
        vixy_close?: number;
        vixy_sma_20?: number;
        spy_close?: number;
        spy_sma_20?: number;
        spy_sma_50?: number;
        data_stale?: boolean;
        fallback_reason?: 'no_substrate' | 'parse_failed' | 'read_failed';
      }>("/api/programs/alpha-trader/regime"),

    indicators: (ticker: string) =>
      request<{
        live: boolean;
        ticker: string;
        as_of?: string;
        price?: number;
        sma_20?: number;
        sma_50?: number;
        sma_200?: number;
        rsi_14?: number;
        atr_14?: number;
        volume_20d_avg?: number;
        fallback_reason?: 'no_substrate' | 'parse_failed' | 'read_failed';
      }>(`/api/programs/alpha-trader/indicators?ticker=${encodeURIComponent(ticker)}`),

    signals: (limit = 10) =>
      request<{
        live: boolean;
        signals: Array<{
          slug: string;
          path: string;
          updated_at?: string;
          ticker?: string;
          direction?: 'long' | 'short' | string;
          expectancy?: number | string;
          status?: string;
          rationale?: string;
          reviewer_decision?: {
            verdict: 'approved' | 'rejected' | 'deferred' | null;
            excerpt: string;
          } | null;
        }>;
        fallback_reason?: 'no_substrate' | 'read_failed';
        evaluator_last_run_at?: string | null;
      }>(`/api/programs/alpha-trader/signals?limit=${limit}`),
    },
  },

  // ADR-327: budget is the KERNEL governance dial (supersedes the retired
  // pace dial). The operation's dollar spend envelope + window-to-date
  // utilization (summed from the execution_events cost ledger) + live queue
  // depth. Budget is the Trigger-dimension dial of the Budget+Autonomy+Identity
  // trifecta. /api/pace → /api/budget.
  budget: () =>
    request<{
      amount_usd: number;
      window: 'monthly' | 'weekly' | 'daily';
      window_spend_usd: number;
      remaining_usd: number;
      per_wake_ceiling_usd: number;
      queue_depth: number;
      // ADR-338 D4.4 — runway framing (null until there's enough spend signal).
      daily_burn_usd: number | null;
      runway_days: number | null;
    }>('/api/budget'),

  // ADR-370: emissions — the operation's outbound boundary (Context → Out
  // lens). Read-only union over destination_delivery_log + notifications
  // (email): what the operation shipped to the outside world, to whom, when.
  // Legibility only — never a send affordance (ADR-299/304: operator-
  // addressing writes are system infrastructure).
  emissions: (limit = 100) =>
    request<Array<{
      id: string;
      channel: string;            // email | slack | notion | in_app
      status: string;             // pending | delivering | delivered | sent | failed
      destination: string | null;
      external_url: string | null;
      error_message: string | null;
      source: 'delivery' | 'notification';
      created_at: string;
      completed_at: string | null;
    }>>(`/api/emissions?limit=${limit}`),

  // ADR-338 D4.1: the standing-watch "drivers" view — declared web sources
  // (_sources.yaml) paired with observed per-source health (_watch_signal.yaml),
  // the Check-7 declared-vs-observed shape. Kernel-agnostic: declaration_path
  // comes from the active bundle's watch declaration, not a kernel constant.
  sources: () =>
    request<{
      watches: Array<{
        watch_id: string;
        program_slug: string | null;
        shape: string | null;
        recurrence: string | null;
        declaration_path: string;
        signal_path: string | null;
        declared: Array<{ id: string; url: string; attestation: string; max_entries: number }>;
        observed: Array<{
          id: string;
          status: string;
          observed_at: string | null;
          entry_count: number;
          error: string | null;
        }>;
        observed_at: string | null;
        source_cap: number;
      }>;
    }>('/api/sources'),

  // The `recurrences` + `narrative` namespaces are DELETED (ADR-603 D5,
  // executed 2026-08-24 — recurrences retired; production counted 0 live
  // declarations). Run receipts read through workspace.timeline (the
  // Activity ledger's `invocation` kind).

  // Workspace Explorer (ADR-152) + Workspace Lifecycle (ADR-244)
  workspace: {
    // ADR-244: canonical workspace-state read. Replaces the legacy
    // memory-user-onboarding-state endpoint with extended shape
    // (substrate_status + capability_gaps + available_programs). Triggers
    // lazy roster scaffolding when no agents exist (idempotent first-login
    // side-effect preserved from the legacy endpoint).
    getState: () =>
      request<{
        has_agents: boolean;
        activation_state: 'none' | 'post_fork_pre_author' | 'operational';
        active_program_slug: string | null;
        available_programs: Array<{
          slug: string;
          title: string;
          tagline: string | null;
          status: 'active' | 'deferred';
          deferred: boolean;
          oracle: Record<string, unknown>;
          current_phase: string | null;
          // ADR-266 D5/D6: human label for the phase, derived from the
          // bundle MANIFEST's phases[].label. FE renders this — never the
          // bare enum slug.
          current_phase_label: string | null;
          // ADR-338 D4.5: the installer "what this program will do" preview —
          // the program's four-flow declaration (DP26) BEFORE activation.
          flow_preview: {
            flows: Array<{
              key: 'perception' | 'work_out' | 'outcomes' | 'loop';
              label: string;
              present: boolean;
              summary?: string;
              rationale?: string | null;
            }>;
            capabilities: string[];
            watch_count: number;
            ground_truth: string | null;
          } | null;
        }>;
        substrate_status: {
          mandate: { path: string; state: 'skeleton' | 'authored' | 'missing'; last_revised_at: string | null };
          identity: { path: string; state: 'skeleton' | 'authored' | 'missing'; last_revised_at: string | null };
          // ADR-432 D1c: `brand` removed (Brand retired).
          autonomy: { path: string; state: 'skeleton' | 'authored' | 'missing'; last_revised_at: string | null };
          principles: { path: string; state: 'skeleton' | 'authored' | 'missing'; last_revised_at: string | null };
        };
        capability_gaps: Array<{
          capability: string;
          requires_platform: string;
          connected: boolean;
        }>;
        // Account-level inventory of active platform connections, independent
        // of the active program's declared requirements. Lets the header chip
        // show what's connected even when the program declares no required
        // platforms — keeps it consistent with the Connectors pane.
        connected_platforms: string[];
      }>("/api/workspace/state"),

    // ADR-266 D8: bundled read for /workspace page mount.
    // Replaces 7 round-trips (state + 6 file reads) with 1. The four
    // concept cards still self-fetch as a fallback for /agents reuse —
    // when WorkspaceConfigSection passes data props, cards skip self-fetch.
    getSetupBundle: () =>
      request<{
        state: Awaited<ReturnType<typeof api.workspace.getState>>;
        mandate: WorkspaceFileWithRevision;
        autonomy_yaml: WorkspaceFileWithRevision;
        principles_prose: WorkspaceFileWithRevision;
        principles_yaml: WorkspaceFileWithRevision;
        identity: WorkspaceFileWithRevision;
        // ADR-432 D1c: `brand` removed (Brand retired).
      }>("/api/workspace/setup-bundle"),

    // ADR-435 (2026-07-10): getHomeBundle DELETED with the Home surface — the
    // one composition in a registry of mirrors. It was the single bundled read
    // for the Home page mount; the concerns it aggregated (proposals, artifacts,
    // judgment log, mandate, autonomy) are each read by their own mirror surface
    // (queue, files, activity, workspace-settings).

    // ADR-154: Structured navigation for Agent OS workfloor.
    // ADR-236 Item 6 (2026-04-29): `mode` and `essential` removed from
    // the contract — both were dropped from `tasks` by ADR-231
    // migration 164. The recurrence label (Recurring vs One-time) is
    // derived from `schedule` per ADR-163 / web/types/index.ts
    // recurrenceLabel().
    getNav: () =>
      request<{
        tasks: Array<{
          slug: string; title: string; status: string;
          schedule: string | null;
          next_run_at: string | null; last_run_at: string | null;
        }>;
        domains: Array<{
          key: string; display_name: string; entity_count: number;
          entity_type: string | null; path: string;
        }>;
        uploads: Array<{
          name: string; path: string; updated_at: string | null;
        }>;
        settings: Array<{
          name: string; filename: string; path: string; updated_at: string | null;
        }>;
        readiness: {
          identity: 'empty' | 'sparse' | 'rich';
          has_domains: boolean;
          has_tasks: boolean;
          phase: 'setup' | 'ready' | 'active';
        };
      }>(`/api/workspace/nav`),

    // ADR-154: Domain entity listing for domain browser view
    getDomainEntities: (domainKey: string) =>
      request<{
        domain_key: string; domain_path: string; display_name: string; entity_type: string | null;
        synthesis_files: Array<{
          name: string; filename: string; path: string; updated_at: string | null; preview: string | null;
        }>;
        entities: Array<{
          slug: string; name: string; last_updated: string | null;
          preview: string | null; files: Array<{ name: string; path: string; updated_at: string | null }>;
        }>;
        entity_count: number;
      }>(`/api/workspace/domain/${domainKey}`),

    // Legacy tree (still used by raw file viewer)
    getTree: (root: string = "/workspace") =>
      request<WorkspaceTreeNode[]>(`/api/workspace/tree?root=${encodeURIComponent(root)}`),

    // ADR-388 D1: the explorer tree SPINE — the actual top-level directories
    // under /workspace/ (filesystem-literal, never a hardcoded list). Known
    // roots carry friendly label/icon from WORKSPACE_ROOTS; unknown/new roots
    // still appear (raw name). Subtrees lazy-load per root via getTree.
    getRoots: () =>
      request<
        Array<{
          name: string;
          path: string;
          display_name: string;
          semantic_class: string;
          description: string;
          icon: string;
          file_count: number;
          exists: boolean;
        }>
      >(`/api/workspace/roots`),

    getFile: (path: string) =>
      request<WorkspaceFile>(`/api/workspace/file?path=${encodeURIComponent(path)}`),

    // ADR-312 Home slot #5: recent delivered outputs across the whole
    // workspace (not per-recurrence). Kernel-universal — every workspace.
    recentArtifacts: (limit: number = 5) =>
      request<{
        artifacts: Array<{
          slug: string;
          date: string;
          path: string;
          summary: string | null;
          updated_at: string | null;
        }>;
      }>(`/api/workspace/recent-artifacts?limit=${limit}`),

    // ADR-329 D2: recently authored substrate changes across the whole
    // workspace (Layer-1 revisions per ADR-209), with authored_by
    // attribution. Distinct from recentArtifacts (delivered outputs) —
    // this is the substrate-change feed: "what did the system author, by
    // whom." Powers the Files "Recently authored" section.
    recentRevisions: (limit: number = 20) =>
      request<{
        revisions: Array<{
          path: string;
          authored_by: string | null;
          message: string | null;
          created_at: string | null;
          // Explorer icon-view thumbnail material (per-format preview).
          content_url?: string | null;
          content_type?: string | null;
          preview?: string | null;
          // Inline SVG markup (no blob) → drawn as the tile thumbnail.
          svg_text?: string | null;
        }>;
      }>(`/api/workspace/recent-revisions?limit=${limit}`),

    // ADR-408 D5.1: the workspace timeline — ONE chronological, attributed
    // stream across the three act ledgers (revisions + invocations +
    // proposals). Distinct from recentRevisions (substrate-only): this is
    // "what happened across the workspace, by whom" — every actor, every
    // kind of act. Powers the Home Timeline slot, the bell's ACTIVITY
    // (ADR-410 D1), and the Notifications workbench (ADR-410 D5 — `before`
    // is the full-history paging cursor the endpoint already supports).
    timeline: (limit: number = 40, before?: string) =>
      request<{
        entries: Array<{
          kind: 'revision' | 'invocation' | 'proposal' | 'membership';
          // ADR-410 D6 — stable derived id (kind:natural-key:at) for row
          // keys + read-state derivation.
          id: string;
          at: string | null;
          // ADR-410/412 viewer pass — the acting principal's uuid where the
          // ledger records one; lets surfaces resolve "You" vs a peer name.
          actor_id: string | null;
          // authored_by-taxonomy string / principal id — render via the
          // shared attribution module (lib/workspace/attribution.ts).
          actor: string | null;
          title: string | null;
          detail: string | null;
          path: string | null;
          slug: string | null;
          proposal_id: string | null;
          status: string | null;
          decided_by: string | null;
          // Proposal rows only — structured primitive/family for the shared
          // labeler (proposalActionLabel); no title parsing.
          primitive: string | null;
          family: string | null;
          // ADR-489 — attention weight, derived at read time (Axiom 9
          // rendering-weight taxonomy). Bell mounts material only; the
          // workbench defaults to material + routine.
          weight?: 'material' | 'routine' | 'housekeeping';
        }>;
        has_more: boolean;
      }>(
        `/api/workspace/timeline?limit=${limit}${before ? `&before=${encodeURIComponent(before)}` : ''}`,
      ),

    // ADR-373 D2: the workspace's principals — WHO can write here, and WHAT
    // write-regions they hold. Read-only legibility over principal_grants; the
    // grant-consult (the gate) authorizes per-principal, this surfaces the same
    // facts. An MCP connector from an external LLM is a *member* (a foreign-llm
    // principal), so this lists humans AND foreign-LLM/3rd-party principals.
    // ADR-407 Phase 5 — every workspace the CALLER can act in (their owner
    // workspace + any member grants). Powers the UserMenu workspace switcher;
    // N=1 users get exactly one membership (the switcher stays hidden).
    memberships: () =>
      request<{
        memberships: Array<{
          workspace_id: string;
          role: 'owner' | 'member' | 'viewer';
          label: string;
          is_active: boolean;
          /** Workspace identity phase 1 — owner-chosen glyph (emoji); null →
           *  the default org glyph. */
          icon: string | null;
        }>;
        /** ADR-501: the caller's workspace-clear authority in the ACTING
         *  workspace, server-derived from the grant (owner OR the
         *  `workspace:clear` scope) — read this, never predict from role. */
        can_clear: boolean;
      }>("/api/workspace/memberships"),

    // Workspace identity phase 1 — rename / re-glyph the acting workspace.
    // Owner-gated server-side (RLS UPDATE policy; a member's PATCH 403s).
    // `icon: null` clears the glyph; omit a field to leave it unchanged.
    updateIdentity: (body: { name?: string; icon?: string | null; timezone?: string | null }) =>
      request<{ workspace_id: string; name: string; icon: string | null }>(
        "/api/workspace",
        { method: "PATCH", body: JSON.stringify(body) },
      ),

    // Create a NEW owned workspace (ADR-465 D2 deliberate genesis). Name-only
    // by scope; future genesis steps are added server-side in
    // services/workspace_genesis.py, not by widening this call. The caller must
    // rebind (setActiveWorkspace) + hard-navigate afterwards — a bind change
    // requires a full reload (ADR-407 D9).
    create: (name: string) =>
      request<{ workspace_id: string; name: string; icon: string | null }>(
        "/api/workspace",
        { method: "POST", body: JSON.stringify({ name }) },
      ),

    // ADR-328 D4 / ADR-510 — download the workspace as a git repo in a zip
    // (working tree + the full attributed history, plus a manifest declaring
    // every omission). A streamed attachment, so it takes the blob path here
    // rather than `request` (which assumes JSON).
    exportWorkspace: async () => {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/api/workspace/export`, {
        credentials: "include",
        headers,
      });
      if (!response.ok) {
        throw new APIError(response.status, response.statusText);
      }
      const contentDisposition = response.headers.get("Content-Disposition");
      const filenameMatch = contentDisposition?.match(/filename="?([^"]+)"?/);
      const filename = filenameMatch ? filenameMatch[1] : "yarnnn-export.zip";
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },

    // ADR-578 — the delete LIFECYCLE (delete → restore → purge). Namespaced
    // under /lifecycle/ because a bare /workspace/{id} route is a catch-all
    // that shadows every literal /workspace/* sibling (DELETE /workspace/byok
    // resolved to delete_workspace before this prefix existed).
    deletePreview: (id: string) =>
      request<{
        workspace_id: string;
        name: string;
        is_last_owned: boolean;
        // `label` is the resolved display name (ADR-578 D4 — the confirmation
        // must be readable). OPTIONAL: resolution is best-effort server-side,
        // so an unresolved principal keeps only its id and the card falls back.
        other_principals: Array<{ principal_id: string; role: string; label?: string }>;
        deleted_at: string | null;
      }>(`/api/workspace/lifecycle/${id}/preview`),
    softDelete: (id: string) =>
      request<{ workspace_id: string; name: string; deleted: boolean }>(
        `/api/workspace/lifecycle/${id}`,
        { method: "DELETE" },
      ),
    restore: (id: string) =>
      request<{ workspace_id: string; restored: boolean }>(
        `/api/workspace/lifecycle/${id}/restore`,
        { method: "POST" },
      ),
    purge: (id: string) =>
      request<{ workspace_id: string; purged: boolean; deleted: Record<string, number> }>(
        `/api/workspace/lifecycle/${id}/purge`,
        { method: "POST" },
      ),

    // ADR-439 — BYOK (enterprise-tier). GET is readable on any tier (the FE
    // shows availability); the write verbs are owner + enterprise-gated server-side.
    getByok: () => request<ByokStatus>("/api/workspace/byok"),
    setByok: (provider: string, apiKey: string) =>
      request<{ success: boolean } & ByokStatus>("/api/workspace/byok", {
        method: "PUT",
        body: JSON.stringify({ provider, api_key: apiKey }),
      }),
    toggleByok: (enabled: boolean) =>
      request<{ success: boolean } & ByokStatus>("/api/workspace/byok", {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      }),
    clearByok: () =>
      request<{ success: boolean } & ByokStatus>("/api/workspace/byok", {
        method: "DELETE",
      }),

    // ADR-512 D6 Get-Info: pass `path` to additionally get each principal's
    // reach over that file (can_read / can_write, computed by the gate's own
    // powerbox matcher server-side — never re-derived here).
    getMembers: (path?: string) =>
      request<{
        members: Array<{
          principal_id: string;
          role: string; // owner | member | own-agent | foreign-llm | platform | a2a
          label: string | null; // humanized name (email / LLM provider / slug)
          write_regions: string[]; // raw write-scope prefixes (the wire truth)
          write_zones: string[]; // ADR-424 operator zones (Documents/Downloads/System files) — what the roster shows
          scopes_explicit: boolean; // true if narrowed on the WRITE axis
          // powerbox (2026-07-10) — TWO INDEPENDENT AXES, path prefixes at
          // arbitrary depth. Each axis has a three-way state:
          //   'all' (NULL → class default) | 'scoped' ([..]) | 'none' ([] deny-all)
          read_scopes: string[]; // raw read-scope prefixes
          read_state: 'all' | 'scoped' | 'none';
          write_state: 'all' | 'scoped' | 'none';
          access_state: 'all' | 'scoped' | 'none'; // combined operator glance (wider axis)
          status: string;
          granted_by: string | null;
          created_at: string | null;
          connected_by: string | null; // ADR-431 — the member who authorized an AI connection
          connected_by_label: string | null; // the authorizing member's email (or the viewer's own)
          connected_by_is_you: boolean; // true when the viewer authorized this connection
          spend_cap_usd: number | null; // ADR-445 §7 Phase 4 — owner-set cap on the shared pool (null = uncapped)
          can_read?: boolean | null; // ADR-512 D6 — only when ?path= was passed
          can_write?: boolean | null;
          // ADR-563 — the CONNECTION's verb tier, a different axis from the
          // path regions above: those say WHERE, this says WHAT VERBS the
          // OAuth token authorizes. foreign-llm only; null = no live token.
          connection_scopes?: string[] | null;
          connection_legacy_full?: boolean;
        }>;
        grant_consult_active: boolean;
        // ADR-445 §6 — proactive seat awareness at the members surface.
        human_seats: number; // active human members
        included_seats: number; // the tier's billing baseline (Free = 1, solo)
        seats_available: boolean; // whether another human may be invited without an upgrade (paid = always true)
      }>(`/api/workspace/members${path ? `?path=${encodeURIComponent(path)}` : ""}`),

    // NARROW (ADR-386 D2; powerbox 2026-07-10) — set a member's read + write
    // scope axes. Path prefixes at arbitrary depth; `[]` on an axis is a
    // deliberate deny-all. `readScopes` omitted → read ⊇ write (read mirrors
    // write). The narrowed set bounds BOTH reads and writes. Owner grant is
    // immutable (403). ADR-431: `connectedBy` targets a specific member's AI
    // connection when a provider is connected by several members.
    narrowMember: (
      principalId: string,
      writeScopes: string[],
      opts?: { readScopes?: string[]; connectedBy?: string | null },
    ) =>
      request<{ success: boolean; principal_id: string; action: string; scopes: string[] | null }>(
        `/api/workspace/members/${encodeURIComponent(principalId)}/narrow`,
        {
          method: "POST",
          body: JSON.stringify({
            write_scopes: writeScopes,
            read_scopes: opts?.readScopes ?? null,
            connected_by: opts?.connectedBy ?? null,
          }),
        },
      ),

    // ADR-386 D2/D3 — REVOKE = full eviction: grant revoked + OAuth tokens
    // deleted. The member must re-authorize from scratch. Owner is immutable (403).
    // ADR-431: `connectedBy` targets a specific member's AI connection.
    revokeMember: (principalId: string, connectedBy?: string | null) =>
      request<{ success: boolean; principal_id: string; action: string; tokens_deleted: number | null }>(
        `/api/workspace/members/${encodeURIComponent(principalId)}/revoke${connectedBy ? `?connected_by=${encodeURIComponent(connectedBy)}` : ""}`,
        { method: "POST" },
      ),

    // ADR-445 §7 Phase 4 — owner sets/clears a member's spend cap on the shared
    // pool. `capUsd: null` (or ≤0) clears the cap (uncapped). Owner-only (403 else).
    capMember: (principalId: string, capUsd: number | null) =>
      request<{ success: boolean; principal_id: string; action: string }>(
        `/api/workspace/members/${encodeURIComponent(principalId)}/cap`,
        { method: "POST", body: JSON.stringify({ cap_usd: capUsd }) },
      ),

    // ADR-404 step 5 — member invites (the ADR-373 D4 provisioning UX).
    inviteMember: (email: string) =>
      request<{
        id: string; email: string; role: string; status: string;
        created_at?: string; expires_at?: string; invite_link?: string;
      }>(`/api/workspace/members/invite`, {
        method: "POST", body: JSON.stringify({ email }),
      }),

    listInvites: () =>
      request<{ invites: Array<{
        id: string; email: string; role: string; status: string;
        created_at?: string; expires_at?: string;
      }> }>(`/api/workspace/invites`),

    revokeInvite: (inviteId: string) =>
      request<{ success: boolean; id: string }>(
        `/api/workspace/invites/${encodeURIComponent(inviteId)}/revoke`,
        { method: "POST" },
      ),

    previewInvite: (token: string) =>
      request<{
        workspace_name: string | null; email: string; role: string;
        status: string; expires_at?: string;
      }>(`/api/invites/${encodeURIComponent(token)}`),

    acceptInvite: (token: string) =>
      request<{
        success: boolean; workspace_id: string;
        workspace_name: string | null; role: string;
      }>(`/api/invites/${encodeURIComponent(token)}/accept`, { method: "POST" }),

    // ADR-437 D4 — the shared-artifact wedge. A share is the invite's
    // link-based, broad-by-default sibling: create a link on an artifact,
    // anyone who opens it and accepts joins the commons as a member.
    // ADR-465 D3: role picks the grant shape — "member" (broad, default) |
    // "viewer" (birth-narrowed read-only grant on accept).
    createShare: (
      artifactPath?: string, label?: string, ttlDays?: number,
      role: "member" | "viewer" = "member",
    ) =>
      request<{
        id: string; artifact_path: string | null; label: string | null;
        role: string; status: string; created_at?: string;
        expires_at?: string | null; share_link?: string | null;
      }>(`/api/workspace/shares`, {
        method: "POST",
        body: JSON.stringify({ artifact_path: artifactPath, label, ttl_days: ttlDays, role }),
      }),

    // ADR-534 D2 — the list carries each link's URL, so a live link can be
    // re-copied rather than only revoked. Authenticated + grant-gated; the
    // PUBLIC projection never carries a token.
    listShares: () =>
      request<{ shares: Array<{
        id: string; artifact_path: string | null; label: string | null;
        role: string; status: string; created_at?: string; expires_at?: string | null;
        share_link?: string | null;
        // ADR-537 D4 — when the link was last redeemed (never a redeemer NAME:
        // the column is overwritten on every accept, so one name would imply a
        // complete list).
        last_accepted_at?: string | null;
      }> }>(`/api/workspace/shares`),

    revokeShare: (shareId: string) =>
      request<{ success: boolean; id: string }>(
        `/api/workspace/shares/${encodeURIComponent(shareId)}/revoke`,
        { method: "POST" },
      ),

    // ADR-513: public (no auth) — the token is the read capability. Returns
    // the artifact's current content + the attribution walk for the landing
    // page; 410 when revoked/expired.
    previewShare: (token: string) =>
      request<{
        workspace_name: string | null; artifact_path: string | null;
        label: string | null; role: string; status: string;
        artifact_name?: string | null; artifact_kind?: string | null;
        artifact_content?: string | null; truncated?: boolean;
        walk?: Array<{ authored_by: string | null; when: string | null; change: string | null }>;
      }>(`/api/s/${encodeURIComponent(token)}`),

    acceptShare: (token: string) =>
      request<{
        success: boolean; workspace_id: string;
        workspace_name: string | null; artifact_path: string | null; role: string;
      }>(`/api/s/${encodeURIComponent(token)}/accept`, { method: "POST" }),

    // ADR-406 D2: pass expectedHeadVersionId (the head_version_id the file
    // was loaded with) to make the save conditional — the API returns 409
    // with the intervening revision's attribution when the base has moved.
    // Omitted → unconditional (appenders, config-dial writes).
    editFile: (
      path: string,
      content: string,
      summary?: string,
      message?: string,
      expectedHeadVersionId?: string | null,
    ) =>
      request<{ success: boolean; path: string; updated_at: string }>(
        `/api/workspace/file`,
        {
          method: "PATCH",
          body: JSON.stringify({
            path,
            content,
            summary,
            message,
            ...(expectedHeadVersionId != null
              ? { expected_head_version_id: expectedHeadVersionId }
              : {}),
          }),
        }
      ),

    // ADR-209 Phase 4 + ADR-329 (amended): the revision chain for a node.
    // Node Details (ADR-329) renders both scopes off this one route:
    //   - { path }        → FILE Details: exact-path chain (revert/diff).
    //   - { pathPrefix }   → FOLDER Details: recent revisions across the
    //                        subtree, each row carrying the file it changed
    //                        (revisions[].path populated). Read-only aggregate.
    // Exactly one of { path, pathPrefix } must be provided.
    listRevisions: (
      scope: { path: string; pathPrefix?: never } | { path?: never; pathPrefix: string },
      limit: number = 10,
    ) => {
      const q =
        scope.path !== undefined
          ? `path=${encodeURIComponent(scope.path)}`
          : `path_prefix=${encodeURIComponent(scope.pathPrefix)}`;
      return request<{
        path: string;
        count: number;
        revisions: Array<{
          id: string;
          authored_by: string;
          author_identity_uuid: string | null;
          message: string;
          created_at: string;
          parent_version_id: string | null;
          // Populated only in the folder (pathPrefix) case.
          path?: string | null;
        }>;
      }>(`/api/workspace/revisions?${q}&limit=${limit}`);
    },

    readRevision: (path: string, revisionId: string) =>
      request<{
        id: string;
        path: string;
        authored_by: string;
        author_identity_uuid: string | null;
        message: string;
        created_at: string;
        parent_version_id: string | null;
        blob_sha: string;
        content: string | null;
      }>(
        `/api/workspace/revisions/${encodeURIComponent(revisionId)}?path=${encodeURIComponent(path)}`
      ),

    diffRevisions: (path: string, fromRev: string, toRev: string) =>
      request<{
        path: string;
        from_revision: {
          id: string; authored_by: string; message: string; created_at: string;
          parent_version_id: string | null; author_identity_uuid: string | null;
        };
        to_revision: {
          id: string; authored_by: string; message: string; created_at: string;
          parent_version_id: string | null; author_identity_uuid: string | null;
        };
        diff: string;
        identical: boolean;
      }>(
        `/api/workspace/revisions/diff/two?path=${encodeURIComponent(path)}&from_rev=${encodeURIComponent(fromRev)}&to_rev=${encodeURIComponent(toRev)}`
      ),
  },

  // ADR-437 (2026-07-10) — the `harvest` client block was removed with the
  // /setup wizard (its only consumer, HarvestPicker, is deleted). The backend
  // /api/harvest/* route is retained as a real capability an anytime-harvest
  // surface would re-wire to (ADR-437 §9 — deferred until demanded).

  // Account management
  account: {
    // ADR-489 D5 — the notification-preference methods are deleted (no UI
    // ever consumed them); the one prefs store is
    // member_state['notification_prefs'] via api.memberState.get/put.

    // Data & Privacy — ADR-122 Phase 5 + 2026-04-24 streamline (docs/features/data-privacy.md Phase 5)
    getDangerZoneStats: () =>
      request<{
        workspace_files: number;
        // 2026-08-26 — `agents` + `agent_runs` REMOVED (migration 248 drops
        // both tables). `work_history_files` counts what L1 actually clears,
        // and is what the card is gated on.
        work_history_files: number;
        tasks: number;
        chat_sessions: number;
        platform_connections: number;
        // ADR-194 Reviewer queue — pending proposals surfaced for L2/L4 confirmation copy
        action_proposals: number;
      }>("/api/account/danger-zone/stats"),

    // L1: Clear work history (docs/features/data-privacy.md). Lightest
    // layer — wipes dated output folders + per-run logs only. Tasks,
    // identity, accumulated context, chat sessions all preserved.
    clearWorkHistory: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/work-history",
        { method: "DELETE" }
      ),

    clearWorkspace: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/workspace",
        { method: "DELETE" }
      ),

    // ADR-425 §2 (2026-08-20) — `clearIntegrations` is DELETED with the bulk
    // /api/account/integrations endpoint. Disconnecting is per-connector
    // (api.integrations.disconnect), the path that owns its own teardown.

    resetAccount: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/reset",
        { method: "DELETE" }
      ),

    deactivateAccount: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/deactivate",
        { method: "DELETE" }
      ),
  },

  // ADR-025: Slash commands
  commands: {
    // List available slash commands for autocomplete/picker
    list: () =>
      request<{
        commands: Array<{
          name: string;
          description: string;
          command: string;
          tier: "core" | "beta";
          trigger_patterns: string[];
        }>;
        total: number;
      }>("/api/commands"),
  },

  // ADR-026: Integrations (Slack, Notion, etc.)
  integrations: {
    // List user's connected integrations
    list: () =>
      request<{
        integrations: Array<{
          id: string;
          provider: string;
          status: string;
          workspace_name: string | null;
          // WHERE the connection points, resolved server-side across the
          // per-provider metadata shapes (GitHub has an ACCOUNT, not a
          // workspace). Null when nothing identifies the target — render
          // nothing rather than an empty label.
          target?: string | null;
          last_used_at: string | null;
          created_at: string;
        }>;
      }>("/api/integrations"),

    // Get specific integration
    get: (provider: string) =>
      request<{
        id: string;
        provider: string;
        status: string;
        workspace_name: string | null;
        last_used_at: string | null;
        created_at: string;
      }>(`/api/integrations/${provider}`),

    // Disconnect an integration
    disconnect: (provider: string) =>
      request<{ success: boolean; message: string }>(
        `/api/integrations/${provider}`,
        { method: "DELETE" }
      ),

    // Get authorization URL to initiate OAuth
    // Pass redirectTo to control where user lands after OAuth (e.g. "/system")
    getAuthorizationUrl: (provider: string, redirectTo?: string) =>
      request<{ authorization_url: string }>(
        `/api/integrations/${provider}/authorize${redirectTo ? `?redirect_to=${encodeURIComponent(redirectTo)}` : ''}`
      ),

    // ADR-030: Landscape discovery. (The coverage half died with the sync
    // lane — 2026-08-19 sweep: nothing wrote sync_registry any more, so
    // coverage_state was permanently "uncovered" and nothing read it.)
    getLandscape: (provider: "slack" | "notion" | "github", refresh?: boolean) =>
      request<{
        provider: string;
        discovered_at: string | null;
        resources: Array<{
          id: string;
          name: string;
          resource_type: string;
          metadata: Record<string, unknown>;
          recommended?: boolean;
        }>;
      }>(`/api/integrations/${provider}/landscape${refresh ? "?refresh=true" : ""}`),

    // ADR-033: Get integrations summary for Dashboard platform cards
    getSummary: () =>
      request<{
        platforms: Array<{
          provider: string;
          status: string;
          workspace_name: string | null;
          connected_at: string;
          resource_count: number;
          resource_type: string;

        }>;
      }>("/api/integrations/summary"),

    // ADR-396: usage + subscription tier. Per-role split (2026-07-29): the
    // WALLET dollars are null unless the caller holds billing authority in the
    // acting workspace — the same authority /subscription/status 403s on, so
    // the menu glance and the Billing pane can never disagree. The boolean
    // balance states ship to everyone (an empty pool stops every member's
    // work); spend/tier stay commons-legible (DP29).
    getLimits: () =>
      request<{
        balance_usd: number | null;
        spend_usd: number;
        raw_balance_usd: number | null;
        allowance_usd: number | null;
        topup_balance_usd: number | null;
        // `enterprise` is a real TIER_CONFIG key that `normalize_tier` can
        // return, so the union must admit it — a value the type says is
        // impossible still arrives at runtime, it just stops being checked.
        tier: "free" | "starter" | "pro" | "enterprise";
        is_subscriber: boolean;
        subscription_plan: string | null;
        next_refill: string | null;
        billing_authority: boolean;
        balance_exhausted: boolean;
        balance_low: boolean;
      }>("/api/user/limits"),

    // Usage tab expansion — spend breakdown + trend + activity (ADR-172)
    getUsageDetail: () =>
      request<{
        // `pct` is share of SPEND, `pct_runs` share of RUNS — two denominators,
        // each named (they used to render fused as one row).
        by_work: Array<{
          slug: string;
          runs: number;
          cost_usd: number;
          pct: number;
          // Fields added after the original contract are OPTIONAL: the API is a
          // separately-deployed service, so a newer FE can meet an older
          // payload. Optional here makes TypeScript enforce the guard rather
          // than leaving it to whoever edits the component next.
          pct_runs?: number;
        }>;
        // Covers the whole spend window (see trend_days), not a fixed 14 days —
        // the same window by_work/activity sum, so the chart and the header
        // can no longer disagree. Carries runs so a day with work but no
        // billable spend does not read as an empty day.
        trend: Array<{
          date: string;
          cost_usd: number;
          runs?: number;
          failed?: number;
        }>;
        trend_days?: number;
        by_model?: Array<{
          model: string;
          runs: number;
          cost_usd: number;
          pct: number;
        }>;
        activity: {
          runs: number;
          success_rate: number | null;
          avg_cost_usd: number;
          failed: number;
          spend_usd?: number;
        };
      }>("/api/user/usage-detail"),

    // ADR-429 Phase 1 — per-member usage attribution. "Who spent what" over the
    // acting workspace's shared pool (rows sum to the pool's spend-since-anchor).
    // Legibility only; the hard-stop stays workspace-summed. principal_id is a
    // member user_id / foreign-LLM host-id / agent slug — humanize via the
    // workspace roster (useWorkspaceRoster). Backend: GET /api/budget/spend-by-principal.
    getSpendByPrincipal: () =>
      request<{
        rows: Array<{ principal_id: string; spend_usd: number; event_count: number }>;
      }>("/api/budget/spend-by-principal"),

    // Get selected sources for a platform
    getSources: (provider: "slack" | "notion" | "github") =>
      request<{
        sources: Array<{
          id: string;
          type: string;
          name: string;
          last_sync_at: string | null;
          metadata?: {
            member_count?: number;
            message_count?: number;
          };
        }>;
        limit: number;
        can_add_more: boolean;
      }>(`/api/integrations/${provider}/sources`),

    // Update selected sources for a platform
    updateSources: (
      provider: "slack" | "notion" | "github",
      sourceIds: string[]
    ) =>
      request<{
        success: boolean;
        selected_sources: Array<{ id: string; name: string; type: string }>;
        message: string;
      }>(`/api/integrations/${provider}/sources`, {
        method: "PUT",
        body: JSON.stringify({ source_ids: sourceIds }),
      }),

    // ADR-404 D2 (2026-07-04 amendment): the deploy-level capture-lane flag,
    // workspace-level (no provider needed). The Channels surface derives
    // whether the Connections + Sources panes render from this — hide-not-
    // delete while the lane is dormant; flipping the env flag re-lights them
    // with zero FE work.
    getCaptureLane: () =>
      request<{ connector_capture_enabled: boolean }>(
        "/api/integrations/capture-lane"
      ),

    // ADR-393 D3 / ADR-392 Phase B: declared × observed for a connector's
    // capture lane. `declared` = the watch declaration (which selectors are in
    // scope); `observed` = the capture lane's per-declaration health blocks
    // (freshness). The "observed" half of the enriched selection surface.
    // ADR-401 Phase 1: also carries the Manage drill-in's ACCESS + CADENCE
    // facts — granted OAuth scopes, connection header facts, the connector's
    // capture entry (schedule/paused), and the deploy-level agent gate.
    getCaptureSignal: (provider: "slack" | "notion" | "github") =>
      request<{
        provider: string;
        declared: Array<{ id: string; name: string | null; selected: boolean }>;
        observed: Record<
          string,
          {
            status?: string;
            observed_at?: string;
            items?: number;
            target?: string;
            last_error?: string;
          }
        >;
        workspace_capture_count: number;
        granted_scopes: string[];
        connection: {
          workspace_name: string | null;
          // Same server-side resolver the list row uses, so both faces of one
          // connection name their target identically.
          target?: string | null;
          connected_at: string | null;
        } | null;
        // ADR-591 — the `capture` field is GONE. It carried `schedule` off the
        // cadence this ADR deleted, and no caller ever read it; the server
        // emitter raised KeyError for every connected provider.
        // ADR-594 D1 — settings are GONE (the destination dial was the last
        // one; the landing grammar is fixed). Served as null until no
        // deployed client reads it.
        settings?: null;
        // The capability facts (reads / writes / agents), derived server-side
        // from the machinery that enacts them. OPTIONAL for the same reason.
        does?: {
          reads: string;
          writes: string;
          // ADR-585 — present once the API serves turn-reach facts.
          chat?: string;
          agents: string;
        } | null;
        agent_enabled: boolean;
        // ADR-591: permanently false — there is no capture schedule. Kept
        // while older clients still read it; nothing gates on it here.
        connector_capture_enabled?: boolean;
      }>(`/api/integrations/${provider}/capture-signal`),

    // The connector-settings door is DELETED (ADR-594 D1): the destination
    // dial was the last setting, and the landing grammar is fixed — a
    // connection is a rail (consent + credential + aperture).

    // ADR-401 D6: health is DERIVED, never stored — this runs the real
    // validate probe (for Slack it actually reads the platform). The stored
    // `status` column is a connect-time fact only and is not liveness.
    getHealth: (provider: string, validate = false) =>
      request<{
        provider: string;
        status: "healthy" | "degraded" | "unhealthy" | "unknown";
        validated_at?: string | null;
        capabilities?: Record<string, unknown>;
        errors?: string[];
        recommendations?: string[];
      }>(
        `/api/integrations/${provider}/health${validate ? "?validate=true" : ""}`,
      ),

    // ADR-392 D8: the workspace-level raw-capture retention window
    // (governance/_retention.yaml). One window for all connectors.
    // NO FE CONSUMER since 2026-08-20 — the RetentionDial was removed
    // (unreachable behind ADR-591's pinned flag, and its "pruned on a window"
    // copy described a GC that no longer exists). Kept deliberately: the
    // backend routes and the tier ceiling are live, so these are the ready
    // wiring if ADR-392 restores retention as a real mechanism. Delete them
    // if that decision goes the other way.
    getRetention: () =>
      request<{
        retention_days: number;
        default_days: number;
        presets: number[];
      }>("/api/integrations/retention"),

    updateRetention: (retentionDays: number) =>
      request<{ retention_days: number; success: boolean }>(
        "/api/integrations/retention",
        { method: "PUT", body: JSON.stringify({ retention_days: retentionDays }) },
      ),

    // Dead pre-582 surface DELETED (2026-08-19 sweep): syncPlatform/triggerSync
    // (the API route was a deprecated stub), getSyncStatus, updateCoverage,
    // listSlackChannels/listNotionPages (sole caller was the unmounted
    // SourcePicker), export/getHistory (zero callers), and the Notion
    // designated-page trio (zero callers; agents still READ the stored
    // metadata key — only the setter surface is gone).

    // ADR-183: Commerce connection (API key auth, not OAuth)
    connectCommerce: (apiKey: string) =>
      request<{
        success: boolean;
        connection_id: string;
        platform: string;
        provider: string;
        status: string;
        store_name: string;
      }>("/api/integrations/commerce/connect", {
        method: "POST",
        body: JSON.stringify({ api_key: apiKey }),
      }),

    // ADR-187: Trading connection (API key + secret auth)
    connectTrading: (apiKey: string, apiSecret: string, paper: boolean = true, marketDataKey?: string) =>
      request<{
        success: boolean;
        connection_id: string;
        platform: string;
        provider: string;
        status: string;
        paper: boolean;
        account_number: string;
      }>("/api/integrations/trading/connect", {
        method: "POST",
        body: JSON.stringify({
          api_key: apiKey,
          api_secret: apiSecret,
          paper,
          market_data_key: marketDataKey,
        }),
      }),

  },

  // ADR-034: Context Domains (Context v2)
  domains: {
    // List user's domains with summary stats
    list: () =>
      request<{
        domains: ContextDomainSummary[];
        total: number;
      }>("/api/domains"),

    // Get active domain for current context
    getActive: (agentId?: string) => {
      const params = agentId ? `?agent_id=${agentId}` : "";
      return request<ActiveDomainResponse>(`/api/domains/active${params}`);
    },

    // Get domain details
    get: (domainId: string) =>
      request<ContextDomainDetail>(`/api/domains/${domainId}`),

    // Rename a domain
    rename: (domainId: string, name: string) =>
      request<{ success: boolean; name: string }>(`/api/domains/${domainId}`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      }),

    // Manually trigger domain recomputation (admin/debug)
    recompute: () =>
      request<{ success: boolean; changes: Record<string, number> }>(
        "/api/domains/recompute",
        { method: "POST" }
      ),

    // Domain memories (Context v2 - replaces projectMemories)
    memories: {
      // List memories in a domain
      list: (domainId: string) =>
        request<Memory[]>(`/api/domains/${domainId}/memories`),

      // Create a memory in a domain
      create: (domainId: string, data: MemoryCreate) =>
        request<Memory>(`/api/domains/${domainId}/memories`, {
          method: "POST",
          body: JSON.stringify(data),
        }),
    },
  },

  // System/Operations status (ADR-141/153/156: streamlined)
  system: {
    getStatus: () =>
      request<{
        platform_sync: Array<{
          platform: string;
          connected: boolean;
          last_synced_at: string | null;
          next_sync_at: string | null;
          source_count: number;
          status: "healthy" | "stale" | "pending" | "disconnected" | "unknown";
          resources: Array<{
            resource_id: string;
            resource_name: string | null;
            last_synced_at: string | null;
            item_count: number;
            has_cursor: boolean;
            status: "fresh" | "recent" | "stale" | "never_synced" | "unknown";
          }>;
        }>;
        background_jobs: Array<{
          job_type: string;
          last_run_at: string | null;
          last_run_status: "success" | "failed" | "never_run" | "unknown";
          last_run_summary: string | null;
          items_processed: number;
          schedule_description: string | null;
        }>;
        tier: string;
        sync_frequency: string;
      }>("/api/system/status"),

    // Lightweight endpoint for polling sync completion during pipeline runs
    getSyncTimestamps: () =>
      request<{
        timestamps: Record<string, string>;
      }>("/api/system/sync-timestamps"),

    // executionEvents DELETED (ADR-603 D5) — the /activity Runs lens is
    // gone; receipts read through workspace.timeline.
  },

  // ADR-193: Action proposals (approval loop)
  proposals: {
    /** List the user's proposals (default: pending only). */
    list: (status: string = "pending", limit: number = 50) =>
      request<{
        proposals: Array<{
          id: string;
          // ADR-307: generic gated-action queue shape.
          primitive: string;
          family: "capital" | "substrate";
          inputs: Record<string, unknown>;
          decision_context: Record<string, unknown> | null;
          status: string;
          task_slug: string | null;
          agent_slug: string | null;
          source: string | null;
          expires_at: string;
          created_at: string;
          approved_at: string | null;
          executed_at: string | null;
          execution_result: Record<string, unknown> | null;
          rejection_reason: string | null;
          approved_by: string | null;
          /** Canon attribution fields (naming-drift boundary-map — mapped from
           * the internal `reviewer_*` columns by the serializer). Read these. */
          agent_identity?: string | null;
          agent_reasoning?: string | null;
          /** @deprecated read `agent_identity`/`agent_reasoning` instead. */
          reviewer_identity?: string | null;
          reviewer_reasoning?: string | null;
        }>;
        /**
         * ADR-211 D7 prospective-attribution contract (Invariant I1):
         * the current occupant of the Reviewer seat. Frontend displays
         * this alongside pending proposals so the operator knows who
         * is set to render the verdict. Empty object for pre-Phase-4
         * workspaces (treat as "unknown — default human occupant").
         */
        current_occupant: {
          occupant: string;
          occupant_class: "human" | "ai" | "external" | "impersonated" | "";
          display_label: string;
        } | Record<string, never>;
      }>(`/api/proposals?status=${encodeURIComponent(status)}&limit=${limit}`),

    /**
     * Fetch a single proposal by id. Response is enveloped per ADR-211
     * D7 Invariant I1 + I2 — `current_occupant` sits alongside `proposal`
     * so the frontend can display seat attribution for both pending and
     * rendered verdicts (for rendered, use proposal.reviewer_identity;
     * for pending, use current_occupant).
     */
    get: (id: string) =>
      request<{
        proposal: {
          id: string;
          // ADR-307: generic gated-action queue shape.
          primitive: string;
          family: "capital" | "substrate";
          inputs: Record<string, unknown>;
          decision_context: Record<string, unknown> | null;
          status: string;
          /** ADR-307 D6 / ADR-408 D5.2: who queued this (authored_by-taxonomy
           * string) — drives the witness-dial line on pending proposals. */
          source: string | null;
          expires_at: string;
          created_at: string;
          /** Canon attribution fields (naming-drift boundary-map — the
           * serializer maps these from the internal `reviewer_*` columns;
           * see docs/analysis/naming-drift-policy-2026-07-08.md). Read these. */
          agent_identity?: string | null;
          agent_reasoning?: string | null;
          /** @deprecated legacy field names — retained additively during the
           * FE migration; read `agent_identity`/`agent_reasoning` instead. */
          reviewer_identity?: string | null;
          reviewer_reasoning?: string | null;
        };
        current_occupant: {
          occupant: string;
          occupant_class: "human" | "ai" | "external" | "impersonated" | "";
          display_label: string;
        } | Record<string, never>;
      }>(`/api/proposals/${id}`),

    /** Approve + execute. Optional modified_inputs merged over proposal.inputs. */
    approve: (id: string, modified_inputs?: Record<string, unknown>) =>
      request<{
        success: boolean;
        proposal_id?: string;
        execution_result?: Record<string, unknown>;
        error?: string;
      }>(`/api/proposals/${id}/approve`, {
        method: "POST",
        body: JSON.stringify({ modified_inputs: modified_inputs ?? null }),
      }),

    /** Reject with optional reason. */
    reject: (id: string, reason?: string) =>
      request<{
        success: boolean;
        proposal_id?: string;
        status?: string;
      }>(`/api/proposals/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason: reason ?? null }),
      }),
  },

  // ADR-407 Phase 3: per-(workspace, user) member-experience state. Arbitrary
  // JSON under a short key ('shell', 'attention', ...), scoped server-side to
  // (acting workspace, authenticated user). GET returns value=null when unset;
  // PUT body is the raw JSON value. Presentation state only — never authored
  // substrate; localStorage stays the local cache in front of this store.
  memberState: {
    get: (key: string) =>
      request<{ key: string; value: any; updated_at: string | null }>(
        `/api/member-state/${encodeURIComponent(key)}`
      ),
    put: (key: string, value: any): Promise<void> =>
      request<{ key: string; saved: boolean }>(
        `/api/member-state/${encodeURIComponent(key)}`,
        {
          method: "PUT",
          body: JSON.stringify(value),
        }
      ).then(() => undefined),
  },

  // ADR-593 D1 — the declared notification-kind registry. Backend-driven
  // vocabulary for the Notifications settings pane (a hand-kept FE copy is
  // the drift ADR-592 exists to prevent). `email_default: null` = declared
  // but not wired: render the `email_note` refusal, never a dead dial.
  notificationKinds: () =>
    request<{
      kinds: Array<{
        key: string;
        owner: string; // 'kernel' | an app slug
        label: string;
        description: string;
        email_default: 'all' | 'high' | 'none' | null;
        email_note: string | null;
      }>;
      email_defaults: Record<string, 'all' | 'high' | 'none'>;
    }>("/api/notification-kinds"),

  // ADR-605 — mentions: the To-do second source (ADR-492 D3). `list` is a
  // per-viewer DERIVATION over the conversation substrate (cast ∩ visibility
  // window ∩ the write-time stamp) — no inbox table. `resolve` advances the
  // viewer's per-conversation resolution cursor (monotonic, server-merged),
  // so a mention clears by being dealt with, never by scroll-by.
  mentions: {
    list: (limit = 20) =>
      request<{
        mentions: Array<{
          conversation_id: string;
          conversation_name: string;
          sequence: number;
          at: string | null;
          excerpt: string;
          author: string;
        }>;
      }>(`/api/mentions?limit=${limit}`),
    resolve: (conversationId: string, sequence: number): Promise<void> =>
      request<{ resolved: boolean }>("/api/mentions/resolve", {
        method: "POST",
        body: JSON.stringify({ conversation_id: conversationId, sequence }),
      }).then(() => undefined),
  },

  // ADR-310 D4: MCP OAuth login handoff. The web /mcp/authorize page calls
  // this with the operator's JWT to bind the real user to the pending auth
  // code, then navigates the browser to the returned redirect_url (back to
  // the OAuth client — Claude.ai / ChatGPT / etc.).
  mcp: {
    // Read-only: describe the client behind a pending code for the consent
    // screen. Binds nothing (security 2026-08-01 — no auto-bind on page load).
    // Describes the pending connection: who you'd approve as, which workspace
    // it reaches, and what it may do (ADR-563 scopes, ADR-373 D6 workspace).
    consentInfo: (code: string) =>
      request<{
        client_name: string | null;
        client_id: string;
        redirect_host: string;
        account_email: string | null;
        workspace_name: string | null;
        workspace_id: string | null;
        grants: string[];
        legacy_full_access: boolean;
      }>(`/api/mcp/oauth-consent?code=${encodeURIComponent(code)}`),
    // Binds the operator to the code — POST, called only on explicit Approve.
    // ADR-573: `workspaceId` binds the connection to a specific workspace the
    // operator reaches. Omitted → the principal's default (ADR-373 D6).
    completeAuthorize: (code: string, workspaceId?: string | null) =>
      request<{ redirect_url: string }>(
        `/api/mcp/oauth-callback?code=${encodeURIComponent(code)}` +
          (workspaceId ? `&workspace_id=${encodeURIComponent(workspaceId)}` : ""),
        { method: "POST" }
      ),
  },

};

export default api;
