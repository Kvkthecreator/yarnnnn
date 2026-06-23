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

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { Settings, LogOut, Sun, Moon, Monitor, User, Columns2, LayoutGrid } from 'lucide-react';
import { createClient } from '@/lib/supabase/client';
import { Z_POPOVER } from '@/lib/shell/z-tiers';
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
  const { foregroundSurface } = useSurfacePreferences();
  const { layoutMode, setLayoutMode } = useShellChrome();
  const { isMobile } = useViewport();
  const supabase = createClient();
  const { theme, setTheme } = useTheme();

  // ADR-297 D20 (2026-05-24): balance display moved from UserMenu
  // dropdown header to top-bar SystemStatusCluster. Singular
  // Implementation: one balance indicator, in kernel chrome.

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push('/');
  };

  // ADR-347 (2026-06-19): two affordances —
  //  - Settings → the ONE operation-settings door (workspace-settings):
  //    constitution, contract (rhythm/witness/expected output), program,
  //    perception. The operation.
  //  - Account → the account window (the `settings` slug, demoted out of the
  //    launcher to UserMenu-reached): billing, usage, data/privacy. The
  //    human/principal (user_id-scoped), not an operation setting.
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

          {/* Menu items — ADR-347 (2026-06-19): the UserMenu carries the
              two affordances that are NOT operation-loop surfaces:
              Settings (the one operation-settings door) + Account (the
              human/principal's account window — billing/usage/privacy,
              demoted here from a launcher door). Sign out below. Operation
              surfaces (Home/Feed/Queue/Files/…) are reached via Dock +
              Launcher, not duplicated here. */}
          <button
            onClick={handleSettings}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-muted transition-colors"
          >
            <Settings className="w-4 h-4 text-muted-foreground" />
            <span>Settings</span>
          </button>

          <button
            onClick={handleAccount}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-muted transition-colors"
          >
            <User className="w-4 h-4 text-muted-foreground" />
            <span>Account</span>
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
