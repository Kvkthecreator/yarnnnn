import { IntlScope } from "@/components/i18n/IntlScope";

// ADR-660 D3 — this page mounts `AuthForm`, which reads its copy from the
// catalogs; without a scope here the connector's sign-in would throw at render.
export default function McpAuthLayout({ children }: { children: React.ReactNode }) {
  return <IntlScope>{children}</IntlScope>;
}
