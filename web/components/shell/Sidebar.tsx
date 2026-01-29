"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { LayoutDashboard, Settings, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/settings", label: "Settings", icon: Settings },
];

interface SidebarItemProps {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  active: boolean;
}

function SidebarItem({ href, label, icon: Icon, active }: SidebarItemProps) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors",
        active
          ? "bg-primary/10 text-primary font-medium"
          : "text-muted-foreground hover:bg-muted hover:text-foreground"
      )}
      aria-current={active ? "page" : undefined}
    >
      <Icon className="h-4 w-4" />
      {label}
    </Link>
  );
}

interface SidebarProps {
  userEmail?: string;
}

export default function Sidebar({ userEmail }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.replace("/auth/login");
  };

  return (
    <aside className="w-64 border-r border-border bg-background flex flex-col h-screen sticky top-0">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <Link href="/dashboard" className="text-xl font-bold">
          YARNNN
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {NAV_ITEMS.map((item) => (
          <SidebarItem
            key={item.href}
            href={item.href}
            label={item.label}
            icon={item.icon}
            active={pathname?.startsWith(item.href) ?? false}
          />
        ))}
      </nav>

      {/* Footer / User */}
      <div className="p-3 border-t border-border space-y-2">
        {userEmail && (
          <p className="text-xs text-muted-foreground truncate px-3">
            {userEmail}
          </p>
        )}
        <button
          onClick={handleSignOut}
          className="flex items-center gap-3 px-3 py-2 text-sm text-muted-foreground hover:bg-muted hover:text-foreground rounded-md transition-colors w-full"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
