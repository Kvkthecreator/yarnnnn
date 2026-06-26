// The remember-receipt widget (ADR-372). A compact confirmation that the write
// landed: ✓ saved, where it was filed, and the attributed source. Renders
// RETURNED substrate only (D3). Deliberately small — the value is making the
// durable write *legible* (it really landed, here's the receipt), not a UI.

import type { RememberResult } from "./types";
import { provBucket } from "../shared/provenance";

export function RememberReceipt({ result }: { result: RememberResult | null }) {
  if (!result) {
    return <p className="yz-empty">Saving…</p>;
  }
  if (result.success === false) {
    return (
      <div className="yz-receipt">
        <span className="yz-check" style={{ color: "var(--yz-mcp)" }}>!</span>
        <div className="yz-receipt-body">
          <p className="yz-receipt-title">Not saved</p>
          <p className="yz-receipt-meta">{result.message || result.error || "The write did not complete."}</p>
        </div>
      </div>
    );
  }

  const source = result.provenance?.source || null;
  const bucket = provBucket(source);
  return (
    <div className="yz-receipt">
      <span className="yz-check">✓</span>
      <div className="yz-receipt-body">
        <p className="yz-receipt-title">Saved to your YARNNN memory</p>
        <p className="yz-receipt-meta">
          {source ? <span className={`yz-chip ${bucket}`}>{source}</span> : null}
          {result.written_to ? <> &nbsp;<code className="yz-path" style={{ display: "inline", marginTop: 0 }}>{result.written_to}</code></> : null}
        </p>
        <p className="yz-receipt-meta" style={{ marginTop: 4 }}>
          Your judgment seat will file it where it belongs and check it against what you already know.
        </p>
      </div>
    </div>
  );
}
