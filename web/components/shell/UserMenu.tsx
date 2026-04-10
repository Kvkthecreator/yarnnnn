'use client';

/**
 * ADR-014: Top Bar with Minimal Chrome
 * User menu dropdown with settings and logout
 */

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { Settings, LogOut, CreditCard, Sun, Moon, Monitor, Zap } from 'lucide-react';
import { createClient } from '@/lib/supabase/client';
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
    router.push('/settings');
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
        <div className="absolute top-full right-0 mt-1 w-56 bg-background border border-border rounded-lg shadow-lg z-50 py-1">
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

          {/* Menu items */}
          <button
            onClick={handleSettings}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-muted transition-colors"
          >
            <Settings className="w-4 h-4 text-muted-foreground" />
            <span>Settings</span>
          </button>

          <button
            onClick={() => {
              setIsOpen(false);
              router.push('/settings?tab=billing');
            }}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-left hover:bg-muted transition-colors"
          >
            <CreditCard className="w-4 h-4 text-muted-foreground" />
            <span>Billing</span>
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
