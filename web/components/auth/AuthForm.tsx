"use client";

/**
 * AuthForm — the single Supabase email/password + Google auth surface.
 *
 * Singular Implementation (CLAUDE.md §2): the cockpit login (`/auth/login`) and
 * the MCP connect login (`/mcp/auth`, ADR-370 A1-lite) share IDENTICAL auth
 * mechanics — the Google button, the email/password form, the signup/login mode
 * toggle, the Supabase calls. Only their *redirect behavior* and *copy* differ
 * (cockpit lands in /desktop; MCP resumes the connect flow, never the cockpit).
 *
 * So the mechanics live here, once; each caller passes:
 *   - onSuccess(): where to go after a password/login success (the redirect)
 *   - callbackRedirect: the OAuth/email-confirm return URL (carries `next`)
 *   - heading / subheading / submitLabel: surface-specific copy
 *   - footer: optional surface note
 *
 * This replaces the ~150 lines that were duplicated across the two pages.
 */

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createClient } from "@/lib/supabase/client";
import { useTranslations } from "next-intl";
import { STAGE_NOTICE } from "@/lib/metadata";
import { MIN_PASSWORD_LENGTH } from "@/lib/auth/password";

/**
 * Is this address one the mail provider can actually deliver to?
 *
 * `<input type="email">` and the auth provider both accept a bare, TLD-less
 * domain (`me@gmail`, `you@localhost`) as syntactically valid. The mail
 * provider then refuses it, and the signup call fails with HTTP 500
 * `unexpected_failure` / "Error sending confirmation email" — a message that
 * blames OUR infrastructure for THEIR typo, with no correction offered.
 * Reproduced 3/3 on 2026-09-15 during the beta-readiness pass, where a
 * first-time visitor read it as "this product is broken" and nearly left.
 *
 * A nonexistent-but-well-formed domain (`you@thisdomaindoesnotexist-zzz.com`)
 * is NOT caught here and must not be: it succeeds at signup and simply bounces
 * later, which is the mail system's job to report, not the form's to guess.
 * The only thing checked is the structural property the provider requires — a
 * dot-bearing domain with a plausible TLD.
 */
function looksDeliverable(email: string): boolean {
  const at = email.lastIndexOf("@");
  if (at < 1 || at === email.length - 1) return false;
  const domain = email.slice(at + 1);
  return /^[^\s.@]+(\.[^\s.@]+)*\.[a-z]{2,}$/i.test(domain);
}

function GoogleIcon() {
  return (
    <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
      <path
        fill="currentColor"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="currentColor"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="currentColor"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="currentColor"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

export interface AuthFormProps {
  /** Where to go after a successful password login. The caller owns the
   *  redirect so the cockpit and MCP surfaces diverge here (and only here). */
  onPasswordSuccess: () => void;
  /** The OAuth / email-confirm return URL (carries the `next` resume target). */
  callbackRedirect: string;
  /** Pre-set the mode (e.g. signup-first surfaces). Defaults to login. */
  initialMode?: "login" | "signup";
  /** Surface copy. */
  loginSubheading: string;
  signupSubheading: string;
  loginSubmitLabel?: string;
  signupSubmitLabel?: string;
  /** Optional initial error to surface (e.g. from OAuth callback params). */
  initialError?: string | null;
}

export function AuthForm({
  onPasswordSuccess,
  callbackRedirect,
  initialMode = "login",
  loginSubheading,
  signupSubheading,
  loginSubmitLabel,
  signupSubmitLabel,
  initialError = null,
}: AuthFormProps) {
  const t = useTranslations("auth");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  /**
   * ONE notice slot, but its TONE is declared, never sniffed from the words.
   *
   * Until 2026-09-15 the sign-up success ("Check your email for a confirmation
   * link.") was written into the `error` state and rendered green by
   * `error.includes("Check your email")`. Two meanings in one channel,
   * discriminated by prose: re-word the copy — which the VOICE-AND-TONE pass is
   * actively doing — and the only success message on the sign-up screen turns
   * red, telling every new member their account failed when it did not. This is
   * the first screen a beta user touches, so the tone is declared beside the
   * text and the render reads the declaration.
   */
  const [notice, setNotice] = useState<{ tone: "error" | "success"; text: string } | null>(
    initialError ? { tone: "error", text: initialError } : null,
  );
  const [mode, setMode] = useState<"login" | "signup">(initialMode);

  // `useState(initialError)` captures the prop on the FIRST render only, and
  // the login page reads `?error=` in an effect — so an error that arrives
  // with the URL was computed and then silently discarded. A member bounced
  // back from a failed callback saw a bare sign-in form with no reason, which
  // reads as "it just didn't work" and is unreportable.
  //
  // Observed while diagnosing a desktop sign-in loop: the callback WAS
  // redirecting with `?error=code_exchange&message=…` and the screen said
  // nothing. ADR-661.
  useEffect(() => {
    if (initialError) setNotice({ tone: "error", text: initialError });
  }, [initialError]);

  const supabase = createClient();

  /**
   * ADR-660 — the provider answers in English. Its error CODE is stable, so the
   * common ones are worded from the catalog; anything unrecognised keeps the
   * provider's own sentence rather than collapsing to a generic one.
   */
  const wordProviderError = (err: unknown): string => {
    const raw = err instanceof Error ? err.message : "";
    const code = (err as { code?: string } | null)?.code ?? "";
    if (code === "invalid_credentials" || /invalid login credentials/i.test(raw)) return t("errors.invalidCredentials");
    if (code === "email_not_confirmed" || /email not confirmed/i.test(raw)) return t("errors.emailNotConfirmed");
    if (code === "user_already_exists" || /already registered/i.test(raw)) return t("errors.alreadyRegistered");
    if (code === "weak_password") return t("errors.weakPassword", { min: MIN_PASSWORD_LENGTH });
    if (code === "over_email_send_rate_limit" || code === "over_request_rate_limit") return t("errors.rateLimited");
    return raw || t("errors.generic");
  };

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    // Caught HERE rather than at the provider: a TLD-less domain returns a 500
    // that reads as our failure. Say what is wrong and let them fix it.
    if (!looksDeliverable(email)) {
      setNotice({
        tone: "error",
        text: t("errors.incompleteEmail"),
      });
      return;
    }
    setLoading(true);
    setNotice(null);
    try {
      if (mode === "login") {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        onPasswordSuccess();
      } else {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: callbackRedirect },
        });
        if (error) throw error;
        setNotice({
          tone: "success",
          text: t("confirmationSent"),
        });
      }
    } catch (err) {
      const raw = err instanceof Error ? err.message : "";
      // The provider's own words for an undeliverable address name OUR mail
      // infrastructure ("Error sending confirmation email"), so a person reads
      // a typo as our outage. Re-say it as something they can act on, and keep
      // the Google door in view — it is unaffected by mail delivery.
      const undeliverable = /sending confirmation email|unexpected_failure/i.test(raw);
      setNotice({
        tone: "error",
        text: undeliverable
          ? t("errors.undeliverable")
          : wordProviderError(err),
      });
    } finally {
      setLoading(false);
    }
  };

  /**
   * Send a password-reset link (2026-09-15).
   *
   * Until the beta-readiness pass there was NO reset path anywhere in the
   * product — no `resetPasswordForEmail` call and no route — so a member who
   * forgot their password was permanently locked out of their own substrate
   * with no self-service door. The Supabase template
   * (`supabase/templates/auth/reset-password.html`) has existed the whole time;
   * only the door was missing.
   *
   * The response is deliberately the SAME whether or not the address has an
   * account: a differing message turns this box into an account-existence
   * oracle for anyone who wants to enumerate members.
   */
  const handlePasswordReset = async () => {
    if (!looksDeliverable(email)) {
      setNotice({
        tone: "error",
        text: t("errors.resetNeedsEmail"),
      });
      return;
    }
    setLoading(true);
    setNotice(null);
    try {
      await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: callbackRedirect,
      });
    } catch {
      // Swallowed on purpose — see the oracle note above. A failure and a
      // success must be indistinguishable from outside.
    } finally {
      setNotice({
        tone: "success",
        text: t("resetSent"),
      });
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    setNotice(null);

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: callbackRedirect,
          queryParams: { access_type: "offline", prompt: "consent" },
        },
      });
      if (error) throw error;
    } catch (err) {
      setNotice({
        tone: "error",
        text: wordProviderError(err),
      });
      setLoading(false);
    }
  };

  return (
    <>
      <p className="mt-2 text-[#1a1a1a]/60 text-center">
        {mode === "login" ? loginSubheading : signupSubheading}
      </p>
      {mode === "signup" && STAGE_NOTICE && (
        // ADR-629 D4 — the ONE place the stage is said out loud: where a
        // person decides to make an account. Everywhere else it is a quiet
        // annotation beside the mark.
        <p className="mt-2 text-center text-xs text-[#1a1a1a]/50">{STAGE_NOTICE}</p>
      )}

      <div className="glass-card-light p-8 space-y-6 mt-8">
        <Button
          type="button"
          variant="outline"
          className="w-full"
          onClick={handleGoogleLogin}
          disabled={loading}
        >
          <GoogleIcon />
          {t("continueWithGoogle")}
        </Button>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-[#1a1a1a]/10" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white/80 text-[#1a1a1a]/50">{t("or")}</span>
          </div>
        </div>

        <form onSubmit={handleEmailAuth} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-[#1a1a1a]">
              {t("email")}
            </label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1 bg-white/50 border-[#1a1a1a]/10 text-[#1a1a1a] placeholder:text-[#1a1a1a]/40 focus:border-[#1a1a1a]/30"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-[#1a1a1a]">
              {t("password")}
            </label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-1 bg-white/50 border-[#1a1a1a]/10 text-[#1a1a1a] placeholder:text-[#1a1a1a]/40 focus:border-[#1a1a1a]/30"
              placeholder="••••••••"
              minLength={MIN_PASSWORD_LENGTH}
            />
            {mode === "signup" && (
              // Stated BEFORE the submit. The native minLength popup fires only
              // after a failed submit, which reads as a rejection rather than a
              // rule a person could have followed.
              <p className="mt-1 text-xs text-[#1a1a1a]/50">
                {t("passwordRule", { min: MIN_PASSWORD_LENGTH })}
              </p>
            )}
          </div>

          {notice && (
            <p
              role={notice.tone === "error" ? "alert" : "status"}
              className={`text-sm ${
                notice.tone === "success" ? "text-emerald-600" : "text-red-600"
              }`}
            >
              {notice.text}
            </p>
          )}

          <Button
            type="submit"
            className="w-full bg-[#1a1a1a] hover:bg-[#1a1a1a]/90 text-white"
            disabled={loading}
          >
            {loading
              ? t("loading")
              : mode === "login"
                ? (loginSubmitLabel ?? t("signIn"))
                : (signupSubmitLabel ?? t("signUp"))}
          </Button>

          {mode === "login" && (
            // The only way back in for a member who forgot their password.
            // Sign-up mode has nothing to reset, so it is shown only here.
            <button
              type="button"
              onClick={handlePasswordReset}
              disabled={loading}
              className="w-full text-center text-xs text-[#1a1a1a]/50 hover:text-[#1a1a1a]/80 transition-colors disabled:opacity-50"
            >
              {t("forgotPassword")}
            </button>
          )}
        </form>

        <p className="text-center text-sm text-[#1a1a1a]/60">
          {mode === "login" ? (
            <>
              {t("noAccount")}{" "}
              <button
                type="button"
                onClick={() => setMode("signup")}
                className="text-[#1a1a1a] font-medium hover:underline"
              >
                {t("signUp")}
              </button>
            </>
          ) : (
            <>
              {t("haveAccount")}{" "}
              <button
                type="button"
                onClick={() => setMode("login")}
                className="text-[#1a1a1a] font-medium hover:underline"
              >
                {t("signIn")}
              </button>
            </>
          )}
        </p>
      </div>
    </>
  );
}
