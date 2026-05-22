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
 */

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { Settings, LogOut, Sun, Moon, Monitor, Zap } from 'lucide-react';
import { createClient } from '@/lib/supabase/client';
import { Z_POPOVER } from '@/lib/shell/z-tiers';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { cn } from '@/lib/utils';
import { api } from '@/lib/api/client';

interface UserMenuProps {
  email?: string;
}

export function UserMenu({ email }: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [balance, setBalance] = useState<{ balance: number; spend: number; isPro: boolean } | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  const { foregroundSurface } = useSurfacePreferences();
  const supabase = createClient();
  const { theme, setTheme } = useTheme();

  // Fetch balance on mount
  useEffect(() => {
    api.integrations.getLimits()
      .then((data) => {
        setBalance({
          balance: data.balance_usd,
          spend: data.spend_usd,
          isPro: data.is_subscriber,
        });
      })
      .catch(() => {});
  }, []);

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

  const handleSettings = () => {
    setIsOpen(false);
    // ADR-297 D19.4 + D19.5: Settings is an atomic surface; open it
    // as a window on the Desktop alongside whatever's foregrounded.
    // No router.push — URL is informational add-on (D19.2).
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
          {/* User info + Theme */}
          {email && (
            <div className="px-3 py-2 border-b border-border">
              <p className="text-sm font-medium truncate">{email}</p>
              <div className="flex items-center justify-between mt-1">
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  {balance ? (
                    <>
                      <Zap className="w-3 h-3" />
                      ${balance.balance.toFixed(2)} balance
                      <span className="text-muted-foreground/60">
                        {balance.isPro ? "· Pro" : ""}
                      </span>
                    </>
                  ) : (
                    "Loading..."
                  )}
                </p>
                <div className="flex items-center gap-0.5 bg-muted rounded-md p-0.5">
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

          {/* Menu items — D19.4 (2026-05-22) shrunk to Settings + Sign
              out. Mandate / Activity / Connectors / Billing entries
              DELETED. Mandate + Activity are atomic surfaces reachable
              via Dock + Launcher. Connectors is now its own atomic
              surface (15th content surface). Billing is a Settings tab
              (?tab=billing intra-surface state). UserMenu is the
              account/settings affordance only. */}
          <button
            onClick={handleSettings}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-muted transition-colors"
          >
            <Settings className="w-4 h-4 text-muted-foreground" />
            <span>Settings</span>
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
