// Provenance bucketing shared by all widgets (ADR-372). Maps an authored_by /
// source-tag string to a stable color bucket — the cross-LLM attribution made
// visual, the same in trace nodes and recall cards.

export type ProvBucket = "operator" | "reviewer" | "mcp" | "agent" | "system";

export function provBucket(tag: string | null | undefined): ProvBucket {
  const a = (tag || "").toLowerCase();
  if (a.startsWith("operator")) return "operator";
  if (a.startsWith("reviewer")) return "reviewer";
  if (a.includes("mcp")) return "mcp"; // yarnnn:mcp:<client> | mcp:<client>
  if (a.startsWith("agent")) return "agent";
  return "system";
}

export function fmtWhen(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}
