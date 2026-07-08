'use client';

/**
 * UserMenu — account/settings affordance.
 *
 * ADR-297 D19.4 (2026-05-22) — shrunk to header (email + balance +
 * theme) + Settings + Sign out. Pre-D19.4 the menu mixed atomic
 * surface discovery (Mandate, Activity) with account chrome
 * (Settings, Billing, Connectors), which was an inconsistent
 * paradigm. Atomic surfaces are discoverable via Dock + Launcher;
 * UserMenu doesn't need to be a parallel discovery surface for them.
 * Billing folds into Settings as a tab (?tab=billing). Connectors
 * is its own atomic surface (15th content surface, ADR-297 D19.4
 * §D19.4.2) — operator reaches it via Launcher or by adding it to
 * the Dock.
 *
 * ADR-297 D20 (2026-05-24) — balance display deleted from the
 * dropdown header. Balance now lives in the top-bar agent-OS
 * SystemStatusCluster (slot 3). Header retains email + theme toggle.
 * Singular Implementation: one balance indicator in the workspace.
 *
 * ADR-358 (2026-06-23) — the UserMenu gains the LAYOUT-MODE control: a
 * Canvas · Desktop segmented toggle. This is the operator's choice of the
 * shell's spatial paradigm (chat-interface convention vs macOS window
 * manager) — a shell-wide preference, the System-Settings-adjacent home
 * (ADR-338 management-plane vocabulary). Desktop-only: mode is inert on
 * mobile (one physically-possible arrangement), so the control is hidden
 * below the breakpoint.
 */

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { Settings, LogOut, Sun, Moon, Monitor, User, Columns2, LayoutGrid, Check, Briefcase } from 'lucide-react';
import { createClient } from '@/lib/supabase/client';
import { setActiveWorkspace, clearActiveWorkspace } from '@/lib/api/client';
import {
  useWorkspaceMembers,
  useWorkspaceMemberships,
  type WorkspaceMembershipRow,
} from '@/lib/workspace/viewer';
import { Z_POPOVER } from '@/lib/shell/z-tiers';
import { usePopoverDismissal } from '@/lib/shell/usePopoverDismissal';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { useShellChrome } from './ShellChromeContext';
import { useViewport } from '@/lib/shell/useViewport';
import { cn } from '@/lib/utils';

interface UserMenuProps {
  email?: string;
}

export function UserMenu({ email }: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { foregroundSurface, navigateToSurface } = useSurfacePreferences();
  const { layoutMode, setLayoutMode } = useShellChrome();
  const { isMobile } = useViewport();
  const supabase = createClient();
  const { theme, setTheme } = useTheme();

  // ADR-297 D20 (2026-05-24): balance display moved from UserMenu
  // dropdown header to top-bar SystemStatusCluster. Singular
  // Implementation: one balance indicator, in kernel chrome.

  // Click-outside + Escape close (shared dismissal contract, 2026-07-01).
  usePopoverDismissal(dropdownRef, isOpen, () => setIsOpen(false));

  // ADR-407 Phase 5 + ADR-412 D6 — the ambient workspace context, homed HERE
  // (operator ruling 2026-07-07: the menu, not fixed top-bar chrome). Both
  // reads come from the module-cached viewer-layer fetches (membership is a
  // slow fact, one fetch per page life — never presence, never realtime).
  // The Workspace section ALWAYS renders once resolved (N=1 shows the single
  // binding — consistent chrome); rows are switchable only when there is an
  // alternative to switch to.
  const { memberships } = useWorkspaceMemberships();
  const { members } = useWorkspaceMembers();

  // People-count for the workspace row's sub-label (2026-07-08: replaces the
  // full WHO'S HERE list — a compact "N people" over the human members
  // [owner + member roles], AI principals excluded [they live on the Members /
  // AI-Connections surfaces, not this glance]). Rendered as "N people (Role)".
  const humanCount = members.filter(
    (m) => m.role === 'owner' || m.role === 'member',
  ).length;
  const peopleLabel =
    humanCount > 0 ? `${humanCount} ${humanCount === 1 ? 'person' : 'people'}` : null;

  const handleSwitchWorkspace = (m: WorkspaceMembershipRow) => {
    if (m.is_active) {
      setIsOpen(false);
      return;
    }
    // Owner → CLEAR the binding (absent header = server resolves the owner
    // workspace); member → pin the workspace id. Then hard-navigate: a full
    // reload is required so every fetched surface rebinds to the new
    // workspace — no client-side route.
    if (m.role === 'owner') clearActiveWorkspace();
    else setActiveWorkspace(m.workspace_id);
    window.location.assign('/home');
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push('/');
  };

  // ADR-347 (2026-06-19): two affordances — the two scopes, one name each
  // (naming-coherence pass 2026-07-08 — menu label == window title, no
  // felt-redirect):
  //  - Workspace Settings → the operation door (workspace-settings slug):
  //    constitution, contract (rhythm/witness/expected output), program,
  //    perception. The operation.
  //  - User Settings → the account window (the `settings` slug): billing,
  //    usage, data/privacy. The human/principal (user_id-scoped), not an
  //    operation setting. (Renamed from "Account" so it matches the window
  //    title "User Settings" — was titled "System Settings", which fought both
  //    its content and this label.)
  const handleSettings = () => {
    setIsOpen(false);
    // ADR-297 D19.4 + D19.5: open as a window on the Desktop; no router.push.
    foregroundSurface('workspace-settings');
  };

  const handleAccount = () => {
    setIsOpen(false);
    foregroundSurface('settings');
  };

  // Get initials from email
  const initials = email
    ? email.split('@')[0].slice(0, 2).toUpperCase()
    : '?';

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-colors",
          "bg-primary/10 text-primary hover:bg-primary/20",
          isOpen && "ring-2 ring-primary/30"
        )}
        title={email || 'User menu'}
      >
        {initials}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          style={{ zIndex: Z_POPOVER }}
          className="absolute top-full right-0 mt-1 w-56 bg-background border border-border rounded-lg shadow-lg py-1"
        >
          {/* User info + Theme. ADR-297 D20: balance display removed
              — balance is now in the top-bar SystemStatusCluster
              (Singular Implementation: one balance indicator). */}
          {email && (
            <div className="px-3 py-2 border-b border-border">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium truncate">{email}</p>
                <div className="flex items-center gap-0.5 bg-muted rounded-md p-0.5 shrink-0">
                  <button
                    onClick={() => setTheme('light')}
                    className={cn(
                      "p-1 rounded transition-colors",
                      theme === 'light' ? "bg-background shadow-sm" : "hover:bg-background/50"
                    )}
                    title="Light"
                  >
                    <Sun className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => setTheme('dark')}
                    className={cn(
                      "p-1 rounded transition-colors",
                      theme === 'dark' ? "bg-background shadow-sm" : "hover:bg-background/50"
                    )}
                    title="Dark"
                  >
                    <Moon className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => setTheme('system')}
                    className={cn(
                      "p-1 rounded transition-colors",
                      theme === 'system' ? "bg-background shadow-sm" : "hover:bg-background/50"
                    )}
                    title="System"
                  >
                    <Monitor className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ADR-358 — layout-mode control. Canvas (chat-left + one
              full-bleed surface) vs Desktop (free-floating window manager
              + right rail). The operator's choice of spatial paradigm.
              Desktop-only: mode is inert on mobile (one arrangement is
              physically possible), so the row is hidden below the
              breakpoint. Same segmented-control grammar as the theme
              toggle above. */}
          {!isMobile && (
            <div className="px-3 py-2 border-b border-border">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs text-muted-foreground">Layout</span>
                <div className="flex items-center gap-0.5 bg-muted rounded-md p-0.5 shrink-0">
                  <button
                    onClick={() => setLayoutMode('canvas')}
                    className={cn(
                      'flex items-center gap-1 px-1.5 py-1 rounded text-[11px] transition-colors',
                      layoutMode === 'canvas'
                        ? 'bg-background shadow-sm'
                        : 'hover:bg-background/50'
                    )}
                    title="Canvas — chat beside one surface"
                  >
                    <Columns2 className="w-3 h-3" />
                    <span>Canvas</span>
                  </button>
                  <button
                    onClick={() => setLayoutMode('desktop')}
                    className={cn(
                      'flex items-center gap-1 px-1.5 py-1 rounded text-[11px] transition-colors',
                      layoutMode === 'desktop'
                        ? 'bg-background shadow-sm'
                        : 'hover:bg-background/50'
                    )}
                    title="Desktop — floating windows"
                  >
                    <LayoutGrid className="w-3 h-3" />
                    <span>Desktop</span>
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ADR-407 Phase 5 + ADR-412 D6 — the Workspace section: ALWAYS
              rendered once resolved (N=1 shows the single binding — operator
              ruling 2026-07-07: consistent chrome, homed in the menu). Rows
              double as the switcher when the caller holds more than one
              membership: selecting a workspace rebinds X-Workspace-Id
              (owner = clear, member = pin) and hard-reloads to /home so all
              fetched state rebinds. The row's sub-label is a compact
              "N people (Role)" — the human MEMBERSHIP count (never presence —
              ADR-373 rejection stands) folded onto the role, replacing the
              standalone who's-here list (2026-07-08). The Manage-access door
              into the Members pane carries the full roster. */}
          {memberships.length > 0 && (
            <div className="border-b border-border py-1">
              <div className="px-3 py-1 text-[11px] uppercase tracking-wide text-muted-foreground">
                Workspace
              </div>
              {memberships.map((m) => (
                <button
                  key={m.workspace_id}
                  onClick={() => handleSwitchWorkspace(m)}
                  className="w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-muted transition-colors"
                >
                  <Briefcase className="w-4 h-4 text-muted-foreground shrink-0" />
                  <span className="flex-1 min-w-0">
                    <span className="block truncate">{m.label}</span>
                    <span className="block text-[11px] text-muted-foreground">
                      {/* People-count only on the active workspace (the only
                          roster we've fetched); inactive rows show the role
                          alone. "3 people (Owner)" / "1 person (Member)". */}
                      {m.is_active && peopleLabel ? (
                        <>
                          {peopleLabel}{' '}
                          <span className="capitalize">({m.role})</span>
                        </>
                      ) : (
                        <span className="capitalize">{m.role}</span>
                      )}
                    </span>
                  </span>
                  {m.is_active && <Check className="w-4 h-4 text-primary shrink-0" />}
                </button>
              ))}
              <button
                onClick={() => {
                  setIsOpen(false);
                  navigateToSurface('workspace-settings', { pane: 'members' });
                }}
                className="w-full px-3 py-1.5 text-left text-[11px] text-primary hover:bg-muted transition-colors"
              >
                Manage access →
              </button>
            </div>
          )}

          {/* Menu items — ADR-347 (2026-06-19): the UserMenu carries the two
              settings doors (NOT operation-loop surfaces): Workspace Settings
              (the operation) + User Settings (the human/principal's account —
              billing/usage/privacy). Each label == its window title, so
              clicking one never feels like a redirect (naming-coherence pass
              2026-07-08). Sign out below. Operation surfaces (Home/Files/…) are
              reached via Dock + Launcher, not duplicated here. */}
          <button
            onClick={handleSettings}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-muted transition-colors"
          >
            <Settings className="w-4 h-4 text-muted-foreground" />
            <span>Workspace Settings</span>
          </button>

          <button
            onClick={handleAccount}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-muted transition-colors"
          >
            <User className="w-4 h-4 text-muted-foreground" />
            <span>User Settings</span>
          </button>

          <div className="border-t border-border my-1" />

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-muted transition-colors text-destructive"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign out</span>
          </button>
        </div>
      )}
    </div>
  );
}
