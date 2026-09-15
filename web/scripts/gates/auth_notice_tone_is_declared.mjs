/**
 * Gate: a notice's TONE is declared, never sniffed from its words.
 *
 * FOUND 2026-09-15, beta-readiness pass, on the FIRST screen a new member
 * touches. `AuthForm` wrote its sign-up success — "Check your email for a
 * confirmation link." — into the `error` state, then picked the colour with
 *
 *     error.includes("Check your email") ? "text-emerald-600" : "text-red-600"
 *
 * Two meanings in one channel, discriminated by prose. The VOICE-AND-TONE pass
 * is actively re-wording served copy; the first re-word of that sentence turns
 * the only success message on the sign-up screen RED, telling every new member
 * their account failed when it did not. Nothing would have gone red: tsc is
 * blind to it, and the string still renders.
 *
 * THE RULE: a component that renders both success and failure through one slot
 * must carry the tone as DATA beside the text. Reading the message to decide how
 * to show the message is the defect.
 *
 * Run: node scripts/gates/auth_notice_tone_is_declared.mjs   (from web/)
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
let passed = 0;
let failed = 0;

const check = (label, ok) => {
  if (ok) {
    passed += 1;
    console.log(`PASS  ${label}`);
  } else {
    failed += 1;
    console.log(`FAIL  ${label}`);
  }
};

const FORM = join(WEB, "components/auth/AuthForm.tsx");
const src = readFileSync(FORM, "utf8");

// Strip comments before every substring check — a gate that matches its own
// documentation is the recurring defect this repo has hit twice (2026-09-07).
const code = src
  .replace(/\/\*[\s\S]*?\*\//g, "")
  .replace(/^\s*\/\/.*$/gm, "");

// 1. The tone must never be derived from the message text.
// Matches ANY `<expr>.includes(...) ? ...` / `.startsWith(...) ? ...` used to
// pick a class or a tone — `error.includes`, `notice.text.includes`,
// `msg?.body.includes`, anything. The first cut anchored on a bare identifier
// and stayed GREEN when the defect was reintroduced as `notice.text.includes`,
// which is precisely the "assert the construct, not one spelling of it" trap
// (BROWSER-CLICK-PASS-PLAYBOOK §5).
const SNIFFERS = [
  /\.(includes|startsWith|endsWith|match|test)\s*\([^)]*\)\s*\?[\s\S]{0,80}?text-(emerald|green|red|amber|yellow)/,
  /\.(includes|startsWith|endsWith)\s*\([^)]*\)\s*\?\s*["'`](success|error|warning)["'`]/,
];
check(
  "the notice colour is NOT chosen by matching the message text",
  !SNIFFERS.some((re) => re.test(code)),
);

// 2. The tone must exist as a declared field.
check(
  "a notice carries a declared tone field (success | error)",
  /tone\s*:\s*["'`]?(success|error)/.test(code) &&
    /tone\s*===\s*["'`](success|error)["'`]/.test(code),
);

// 3. The success path must SET the success tone — assert the assignment, not
//    the identifier (a bare /tone/ survives deleting the line that sets it).
const signupBlock = code.slice(code.indexOf("auth.signUp"));
check(
  "the sign-up success path sets tone: \"success\"",
  /setNotice\(\s*\{[\s\S]{0,200}?tone\s*:\s*["'`]success["'`]/.test(
    signupBlock.slice(0, 600),
  ),
);

// 4. The failure paths must set the error tone.
const catchCount = (code.match(/tone\s*:\s*["'`]error["'`]/g) || []).length;
check(
  `every failure path sets tone: "error" (found ${catchCount}, expected >= 2)`,
  catchCount >= 2,
);

// 5. The render must read the DECLARATION, not the words.
check(
  "the render branches on the tone field",
  /notice\.tone\s*===\s*["'`]success["'`]\s*\?/.test(code),
);

// 6. COMPLETENESS — no `setError` may survive in this file. The straggler that
//    resets state is exactly how half a refactor ships green.
check(
  "no setError call survives (the old single-channel state is fully gone)",
  !/setError\s*\(/.test(code),
);

console.log("=".repeat(62));
console.log(
  `auth notice-tone gate: ${passed}/${passed + failed} passed, ${failed} failed`,
);
console.log("=".repeat(62));
process.exit(failed ? 1 : 0);
