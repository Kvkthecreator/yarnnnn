/**
 * The modifier key's NAME, for copy that has to say it out loud.
 *
 * ADR-661 §7.6 — the shell is packaged per platform, and the copy must not
 * assume which one. Three member-facing strings shipped `⌘` hardcoded
 * (`studio.pagedNavigator.undoHint`, `studio.designTab.bold`,
 * `studio.designTab.italic`, in BOTH catalogs), so a Windows member read a key
 * their keyboard does not have — a live defect on the web product, found while
 * scoping the desktop shell.
 *
 * This is the ONLY place the product decides which glyph to print. It is a
 * NAME, never a behaviour: every key HANDLER in the client already accepts
 * `e.metaKey || e.ctrlKey` and must keep doing so. Branching a handler on the
 * platform is the mistake this file exists to make unnecessary — the handler
 * takes both, and only the word shown to the member changes.
 *
 * Resolution is deliberately narrow. `navigator.platform` is deprecated but is
 * the one signal available synchronously in every engine we serve;
 * `userAgentData.platform` is Chromium-only and async-shaped, so it is read
 * first when already present and never awaited. The fallback is Ctrl, because
 * a Mac member reading "Ctrl" understands it, while a Windows member reading
 * "⌘" does not.
 *
 * Server-safe: during SSR/prerender there is no `navigator`, and the fallback
 * is returned. Copy that must be exact on first paint should not use this — no
 * such copy exists today (all three strings are a tooltip or a toast body,
 * rendered after mount).
 */

/**
 * What the member's platform calls the primary modifier, INCLUDING the
 * separator the platform's own convention uses before the letter.
 *
 * The separator is part of the name, not of the catalog string. Apple prints
 * `⌘Z` closed up; Windows and Linux print `Ctrl+Z`. A catalog that said
 * `"{mod}Z"` and a name that was bare `Ctrl` would render **`CtrlZ`** — which
 * is what the first cut of this did, caught by rendering both arms rather than
 * by reading the diff. Keeping the `+` here means no catalog string, in any
 * language, has to know which platform it is describing.
 */
export type ModifierKeyName = "⌘" | "Ctrl+";

function isApplePlatform(): boolean {
  if (typeof navigator === "undefined") return false;

  // Chromium's replacement for the deprecated `platform`, when already
  // materialised. Never awaited: `getHighEntropyValues` is async and this must
  // stay synchronous for use in a render.
  const data = (
    navigator as Navigator & { userAgentData?: { platform?: string } }
  ).userAgentData;
  if (typeof data?.platform === "string" && data.platform) {
    return /mac/i.test(data.platform);
  }

  // Deprecated, still universally implemented. `MacIntel` covers Apple Silicon
  // too (the value is frozen for compatibility), and iPadOS reports `MacIntel`
  // — which is correct here, since an iPad keyboard carries Command.
  const legacy = navigator.platform;
  if (typeof legacy === "string" && legacy) return /mac/i.test(legacy);

  return /mac/i.test(navigator.userAgent ?? "");
}

/**
 * The glyph to print for the primary modifier: `⌘` on Apple platforms,
 * `Ctrl+` everywhere else (and when the platform cannot be read), each
 * carrying its own platform's separator convention.
 *
 * Pass it into a catalog string as the `mod` argument — never concatenate it
 * onto one, or the word order stops being the catalog's to choose (ADR-660).
 */
export function modifierKeyName(): ModifierKeyName {
  return isApplePlatform() ? "⌘" : "Ctrl+";
}
