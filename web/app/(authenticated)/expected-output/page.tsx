/**
 * /expected-output → /workspace-settings?pane=expected-output redirect stub
 * (ADR-348).
 *
 * Expected Output is pane-grade — a Contract pane inside the ONE Settings
 * door (the operation's settings), alongside Budget (Rhythm) + Autonomy
 * (Witness). The ExpectedOutputCard substrate rendering lives in the door's
 * renderPane; this route is pure server transport per ADR-308 —
 * `redirect()`, never a client-side useEffect redirect.
 */

import { redirect } from 'next/navigation';

export default function ExpectedOutputRedirect() {
  redirect('/workspace-settings?workspace-settings.pane=expected-output');
}
