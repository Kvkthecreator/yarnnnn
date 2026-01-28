import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/react";
import { getBaseMetadata } from "@/lib/metadata";
import "./globals.css";

export const metadata: Metadata = getBaseMetadata();

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-background antialiased">
        {children}
        <Analytics />
      </body>
    </html>
  );
}
