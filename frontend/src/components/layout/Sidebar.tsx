/** Sidebar with role-dependent navigation.
 *
 * Desktop: fixed rail, collapsible to icons and back.
 * Mobile (<768px): off-canvas drawer opened from the top bar.
 */

import { PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { visibleNavItems } from "./navItems";

type SidebarProps = {
  mobileOpen: boolean;
  onCloseMobile: () => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
};

export function Sidebar({
  mobileOpen,
  onCloseMobile,
  collapsed,
  onToggleCollapsed,
}: SidebarProps) {
  const { role } = useAuth();
  const items = visibleNavItems(role);
  const [isDesktop, setIsDesktop] = useState(
    () => typeof window !== "undefined" && window.innerWidth >= 768,
  );

  useEffect(() => {
    const query = window.matchMedia("(min-width: 768px)");
    const handleChange = (event: MediaQueryListEvent) => setIsDesktop(event.matches);
    setIsDesktop(query.matches);
    query.addEventListener("change", handleChange);
    return () => query.removeEventListener("change", handleChange);
  }, []);

  // The rail is only shown as an icon column on a wide screen, and the drawer
  // is only ever icon-free, so one flag drives the labels.
  const iconsOnly = isDesktop && collapsed;

  const content = (
    <div className="flex h-full flex-col gap-2 p-3">
      <div className="flex h-10 items-center justify-between gap-2 px-1">
        <span
          className={cn(
            "text-base font-semibold tracking-tight",
            iconsOnly && "sr-only",
          )}
        >
          HRMS
        </span>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={isDesktop ? onToggleCollapsed : onCloseMobile}
          aria-label={
            isDesktop
              ? collapsed
                ? "Expand sidebar"
                : "Collapse sidebar"
              : "Close navigation"
          }
          className="h-8 w-8 shrink-0"
        >
          {isDesktop ? (
            collapsed ? (
              <PanelLeftOpen className="h-4 w-4" aria-hidden="true" />
            ) : (
              <PanelLeftClose className="h-4 w-4" aria-hidden="true" />
            )
          ) : (
            <X className="h-4 w-4" aria-hidden="true" />
          )}
        </Button>
      </div>

      <nav aria-label="Main navigation" className="flex flex-1 flex-col gap-1">
        {items.map((item) => {
          const Icon = item.icon;

          if (!item.available) {
            return (
              <span
                key={item.path}
                aria-disabled="true"
                title={`${item.label} — coming in a later phase`}
                className={cn(
                  "flex cursor-not-allowed items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground/60",
                  iconsOnly && "justify-center px-2",
                )}
              >
                <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                {!iconsOnly && (
                  <>
                    <span className="truncate">{item.label}</span>
                    <span className="ml-auto text-[10px] uppercase tracking-wide opacity-70">
                      soon
                    </span>
                  </>
                )}
              </span>
            );
          }

          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              onClick={onCloseMobile}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  iconsOnly && "justify-center px-2",
                  isActive
                    ? "bg-secondary text-secondary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )
              }
              title={iconsOnly ? item.label : undefined}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {!iconsOnly && <span className="truncate">{item.label}</span>}
            </NavLink>
          );
        })}
      </nav>

      {!iconsOnly && (
        <p className="px-3 text-xs text-muted-foreground/70">
          Phase 2 — teams and employees
        </p>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop rail */}
      <aside
        className={cn(
          "hidden shrink-0 border-r bg-background transition-[width] duration-200 md:block",
          collapsed ? "w-16" : "w-64",
        )}
      >
        {content}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <aside className="absolute inset-y-0 left-0 w-64 border-r bg-background shadow-xl">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
