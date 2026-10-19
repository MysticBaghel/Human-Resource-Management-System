/** App shell: sidebar, top bar and the routed page area. */

import { Menu } from "lucide-react";
import { useState } from "react";
import { Outlet } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { UserMenu } from "@/components/layout/UserMenu";
import { ROLE_LABELS } from "@/api/queries";
import { Button } from "@/components/ui/button";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  const { user } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex min-h-screen bg-muted">
      <Sidebar
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((value) => !value)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-background px-3 sm:px-4">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-9 w-9 md:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </Button>

          <span className="truncate text-sm font-medium md:hidden">HRMS</span>

          <div className="ml-auto flex items-center gap-3">
            {user ? (
              <span className="hidden text-xs text-muted-foreground sm:inline">
                Signed in as{" "}
                <span className="font-medium text-foreground">
                  {ROLE_LABELS[user.role]}
                </span>
              </span>
            ) : null}
            <UserMenu />
          </div>
        </header>

        <main className="min-w-0 flex-1 p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
