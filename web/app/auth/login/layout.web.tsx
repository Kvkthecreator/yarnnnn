import type { Metadata } from "next";
import { BRAND } from "@/lib/metadata";
import { IntlScope } from "@/components/i18n/IntlScope";

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

export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // ADR-660 D3 — a signed-out page learns its language from the device cookie.
  return <IntlScope>{children}</IntlScope>;
}
