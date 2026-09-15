/**
 * Gate: the first screen a beta user touches has working doors.
 *
 * Every claim here was found by DRIVING www.yarnnn.com as a first-time visitor
 * on 2026-09-15, not by reading the code.
 *
 * 1. UNDELIVERABLE ADDRESS. `<input type="email">` and the auth provider both
 *    accept a bare, TLD-less domain (`me@gmail`). Resend then refuses it and
 *    signup returns HTTP 500 `unexpected_failure` / "Error sending confirmation
 *    email" — reproduced 3/3. The visitor reads their own typo as OUR outage
 *    and leaves. (Verified on prod: a real address and even a nonexistent
 *    well-formed domain both return 200 — only the TLD-less form 500s, so the
 *    check must be structural and must NOT try to guess at real domains.)
 *
 * 2. NO PASSWORD RESET EXISTED. Not a missing link — a missing FEATURE: no
 *    `resetPasswordForEmail` call and no route anywhere in the product. A
 *    member who forgot their password was locked out of their own substrate
 *    permanently, with no self-service door.
 *
 * 3. AND THE RESET MUST LAND SOMEWHERE. A recovery link verifies as an OTP,
 *    which signs the member in — so without a set-password step it would drop
 *    them into the app still holding the password they forgot, with no pane
 *    anywhere to change it. A door onto nothing is not a fix.
 *
 * 4. THE RESET MUST NOT BE AN ACCOUNT ORACLE. The reply has to be identical
 *    whether or not the address has an account, or the box enumerates members.
 *
 * Run: node scripts/gates/auth_first_screen_doors.mjs   (from web/)
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
const strip = (s) =>
  s.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");

const form = strip(readFileSync(join(WEB, "components/auth/AuthForm.tsx"), "utf8"));
const callback = strip(readFileSync(join(WEB, "app/auth/callback/page.tsx"), "utf8"));
const pwd = strip(readFileSync(join(WEB, "lib/auth/password.ts"), "utf8"));

// ── 1. Undeliverable address is refused BEFORE the provider call ────────────
check(
  "a deliverability check exists and is applied before submit",
  /function looksDeliverable/.test(form) &&
    /if\s*\(\s*!looksDeliverable\(\s*email\s*\)\s*\)/.test(form),
);

// Behavioural, not textual: run the real predicate over the observed cases.
// A regex-shaped assertion would go green on a check that accepts everything.
const src = readFileSync(join(WEB, "components/auth/AuthForm.tsx"), "utf8");
const body = src.match(/function looksDeliverable\([\s\S]*?\n\}/);
let looksDeliverable = null;
// A gate that CRASHES reports nothing (the 43babc0 class). Compiling extracted
// source is the step most likely to throw here, so it is wrapped: a failure to
// build the predicate must show up as a red CHECK, never as a stack trace that
// skips every assertion below it.
try {
  if (body) {
    const js = body[0]
      .replace(/\(\s*email\s*:\s*string\s*\)/, "(email)") // drop the param type
      .replace(/\)\s*:\s*boolean\s*\{/, ") {"); // drop the return type
    // eslint-disable-next-line no-new-func
    looksDeliverable = new Function(`${js}; return looksDeliverable;`)();
  }
} catch (err) {
  console.log(`      (could not compile looksDeliverable: ${err.message})`);
  looksDeliverable = null;
}
const CASES = [
  ["notanemail@notanemail", false],
  ["me@gmail", false],
  ["you@localhost", false],
  ["beta-cold-01@yarnnn.com", true],
  ["probe@thisdomaindoesnotexist-zzz.com", true],
  ["a.b+tag@sub.domain.co.uk", true],
  ["noatsign.com", false],
  ["@nolocal.com", false],
];
check(
  "the deliverability check is extractable and runnable",
  typeof looksDeliverable === "function",
);
if (typeof looksDeliverable === "function") {
  const wrong = CASES.filter(([addr, want]) => looksDeliverable(addr) !== want);
  check(
    `it classifies all ${CASES.length} observed cases correctly${
      wrong.length ? ` (wrong: ${wrong.map(([a]) => a).join(", ")})` : ""
    }`,
    wrong.length === 0,
  );
}

// ── 2. The mail failure is re-said in words a person can act on ────────────
check(
  "a provider mail failure is translated, not shown raw",
  /sending confirmation email\|unexpected_failure/.test(form) &&
    /couldn't send to that address/i.test(form),
);

// ── 3. Password reset exists, and is wired to a real call ──────────────────
check(
  "the form calls resetPasswordForEmail",
  /supabase\.auth\.resetPasswordForEmail\(/.test(form),
);
check(
  "a Forgot-your-password control is rendered in login mode",
  /Forgot your password\?/.test(form) &&
    /onClick=\{handlePasswordReset\}/.test(form),
);

// ── 4. The reset is not an account-existence oracle ────────────────────────
check(
  "the reset reply is identical regardless of account existence",
  /If that address has an account/i.test(form),
);
{
  // The success notice must be set in a `finally`, so the catch cannot diverge.
  const fn = form.match(/const handlePasswordReset[\s\S]*?\n  \};/);
  check(
    "the reset notice is set in finally (catch cannot diverge)",
    !!fn && /finally\s*\{[\s\S]*?setNotice\(/.test(fn[0]),
  );
}

// ── 5. Recovery LANDS somewhere — the door opens onto a real room ──────────
check(
  "the callback branches on a recovery OTP before finalizing",
  /otpType === "recovery"/.test(callback) && /setRecovery\(true\)/.test(callback),
);
check(
  "the recovery branch renders a set-password form that calls updateUser",
  /if \(recovery\)/.test(callback) &&
    /supabase\.auth\.updateUser\(\{\s*password/.test(callback),
);

// ── 6. The password rule has ONE home ──────────────────────────────────────
check(
  "MIN_PASSWORD_LENGTH is declared once and imported by both surfaces",
  /export const MIN_PASSWORD_LENGTH\s*=\s*\d+/.test(pwd) &&
    /import \{ MIN_PASSWORD_LENGTH \}/.test(form) &&
    /import \{ MIN_PASSWORD_LENGTH \}/.test(callback),
);
check(
  "neither surface hard-codes the minimum as a literal",
  !/minLength=\{6\}/.test(form) && !/minLength=\{6\}/.test(callback),
);
check(
  "the sign-up form states the rule before the submit",
  /At least \{MIN_PASSWORD_LENGTH\} characters/.test(form),
);

console.log("=".repeat(62));
console.log(
  `auth first-screen gate: ${passed}/${passed + failed} passed, ${failed} failed`,
);
console.log("=".repeat(62));
process.exit(failed ? 1 : 0);
