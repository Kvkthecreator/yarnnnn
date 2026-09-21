import { redirect } from 'next/navigation';
import { HOME_ROUTE } from '@/lib/routes';

/**
 * The shell's root (ADR-661 §8 step 4).
 *
 * On the web `/` is the marketing landing page (`page.web.tsx`), which the
 * shell does not ship: a member who opened the app has already arrived, and a
 * pitch is what they came through, not what they came for.
 *
 * So the shell's root is transport to the authenticated boot route. Pure
 * `redirect()` per ADR-308 — never a client `useEffect`, which would paint one
 * orphaned frame inside the OS shell before moving. `AuthGate` takes it from
 * there: a member with no session lands on sign-in, one with a session lands
 * on their desktop.
 */
export default function ShellRoot() {
  redirect(HOME_ROUTE);
}
