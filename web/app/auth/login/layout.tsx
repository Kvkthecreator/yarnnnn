import type { Metadata } from "next";
import { BRAND } from "@/lib/metadata";

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
  return children;
}
