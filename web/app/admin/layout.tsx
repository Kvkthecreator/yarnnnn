import { IntlScope } from "@/components/i18n/IntlScope";
import { AdminShell } from "@/components/admin/AdminShell";

/**
 * ADR-660 — the console is a Hat-B operator instrument and its own chrome stays
 * English, but it mounts `FeedbackProvider`, whose confirm shell IS translated
 * (Cancel is a member-facing word). `useTranslations` throws outside a scope, so
 * this route needs one: a fourth `IntlScope`, on a route that is `noindex` and
 * already dynamic (it resolves the viewer client-side before rendering
 * anything), so D3's static-marketing invariant is untouched.
 *
 * The scope is a server component; the console's auth gate and chrome are a
 * client component (`AdminShell`) underneath it.
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <IntlScope>
      <AdminShell>{children}</AdminShell>
    </IntlScope>
  );
}
