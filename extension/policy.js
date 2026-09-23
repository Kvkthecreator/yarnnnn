// ADR-662 D15 — which sites the agent may act on, in the member's own Chrome.
//
// The member's Chrome holds every session they have, so the agent reaches a
// site only after the member said yes to it, once (`consent.html`), and never a
// site in a default-denied category — money, credentials, account security —
// which stays denied whatever the member allowed (ADR-662 D1/D5). The member's
// own lists live in `chrome.storage.local`, on this machine, never in the
// workspace.

/** Categories denied by default, each a test on the hostname. Named so the
 *  popup can show them and the refusal can say which rule applied. */
export const DENIED_CATEGORIES = [
  { key: "banking", test: (h) => /bank/.test(h) || /(^|\.)(paypal|venmo|wise|revolut|toss)\./.test(h) },
  {
    key: "trading",
    test: (h) =>
      /(^|\.)(coinbase|binance|kraken|crypto|robinhood|schwab|fidelity|etrade|vanguard|interactivebrokers|upbit|bithumb|metamask)\./.test(h),
  },
  {
    key: "passwords",
    test: (h) =>
      /(^|\.)(1password|lastpass|bitwarden|dashlane|keeper|keepersecurity)\./.test(h) ||
      h === "passwords.google.com",
  },
  {
    key: "accountSecurity",
    test: (h) => h === "myaccount.google.com" || h === "account.apple.com" || h === "appleid.apple.com",
  },
];

/** The hostname of an http(s) address, lower-cased, or null for anything else
 *  (chrome://, file:, javascript:, a malformed string). */
export function hostOf(url) {
  try {
    const u = new URL(url);
    return u.protocol === "http:" || u.protocol === "https:" ? u.hostname.toLowerCase() : null;
  } catch {
    return null;
  }
}

/** A host and its parents: `mail.google.com` → mail.google.com, google.com. */
function withParents(host) {
  const parts = host.split(".");
  const out = [];
  for (let i = 0; i < parts.length - 1; i++) out.push(parts.slice(i).join("."));
  return out;
}

/**
 * The verdict for one host: `{ verdict: "allowed" | "denied" | "ask", category? }`.
 * A default-denied category wins over anything the member allowed; the
 * member's own denial wins over their allowance; an allowance covers
 * subdomains (allowing x.com covers mobile.x.com).
 */
export function verdictFor(host, { allowed = [], denied = [] } = {}) {
  if (!host) return { verdict: "denied", category: "notAWebPage" };
  const category = DENIED_CATEGORIES.find((c) => c.test(host));
  if (category) return { verdict: "denied", category: category.key };
  const chain = withParents(host);
  if (chain.some((h) => denied.includes(h))) return { verdict: "denied", category: "yours" };
  if (chain.some((h) => allowed.includes(h))) return { verdict: "allowed" };
  return { verdict: "ask" };
}

/** The pages allowed to hand this extension acts (mirrors the manifest's
 *  `externally_connectable`, which Chrome enforces first). */
export const YARNNN_ORIGINS = ["https://www.yarnnn.com", "https://yarnnn.com", "http://localhost:3000"];
