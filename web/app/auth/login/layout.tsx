import type { Metadata } from "next";
import { BRAND } from "@/lib/metadata";
import { ShellIntlScope } from "@/components/i18n/ShellIntlScope";

export const metadata: Metadata = {
  title: "Sign In",
  description: "Sign in to your yarnnn account.",
  alternates: {
    canonical: `${BRAND.url}/auth/login`,
  },
  robots: {
    index: false,
    follow: false,
    noarchive: true,
    nosnippet: true,
  },
};

/**
 * The sign-in layout for the SHELL build (ADR-661 §8 step 4).
 *
 * Paired with `layout.web.tsx`, which is the web build's and the one that
 * changes when product behaviour does. The only difference is the scope:
 * `IntlScope` awaits `getLocale()` through `cookies()`, which a build with no
 * request cannot do. `ShellIntlScope` runs the same ADR-660 D2 chain from the
 * client (§8 step 2), so a signed-out member still meets the shell in their
 * own language — from the device cookie and `navigator.languages`, since
 * there is no account yet to outrank them.
 */
export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <ShellIntlScope>{children}</ShellIntlScope>;
}
