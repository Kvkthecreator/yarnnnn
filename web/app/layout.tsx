import type { Metadata, Viewport } from "next";
import { Analytics } from "@vercel/analytics/react";
import { getBaseMetadata } from "@/lib/metadata";
import { ThemeProvider } from "@/components/theme-provider";
import { DeepLinkBridge } from "@/components/shell/DeepLinkBridge";
import "./globals.css";

export const metadata: Metadata = getBaseMetadata();

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background antialiased">
        <ThemeProvider>
          {/* ADR-661 §8 step 4 — the deep-link listener must sit ABOVE the
              auth boundary. A member completing sign-in is on /auth/login,
              OUTSIDE the authenticated group, so a bridge mounted in that
              group does not exist at the one moment it is needed. Found by
              driving it: the app woke on the link and never navigated.

              Safe in the root despite ADR-660 D3 (which keeps this layout
              static): the bridge reads no cookie and no request state — it
              subscribes to a host event, and is an inert no-op on the web. */}
          <DeepLinkBridge />
          {children}
        </ThemeProvider>
        <Analytics />
      </body>
    </html>
  );
}
