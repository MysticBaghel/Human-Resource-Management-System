/** Sidebar with role-dependent navigation.
 *
 * Desktop: fixed rail, collapsible to icons and back.
 * Mobile (<768px): off-canvas drawer opened from the top bar.
 */

import { PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { Fragment } from "react";
import { NavLink } from "react-router-dom";

import { useAuth } from "@/auth/AuthContext";
import { Button } from "@/components/ui/button";
import { useMediaQuery } from "@/lib/useMediaQuery";
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
  const isDesktop = useMediaQuery("(min-width: 768px)");

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
        {items.map((item, index) => {
          const Icon = item.icon;
          const label =
            (role ? item.labelFor?.[role] : undefined) ?? item.label;
          const previous = items[index - 1];
          const startsSection = Boolean(
            item.section && item.section !== previous?.section,
          );
          const endsSection = Boolean(
            item.section && item.section !== items[index + 1]?.section,
          );

          const link = !item.available ? (
            <span
              key={item.path}
              aria-disabled="true"
              title={`${label} — coming in a later phase`}
              className={cn(
                "flex cursor-not-allowed items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground/60",
                iconsOnly && "justify-center px-2",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {!iconsOnly && (
                <>
                  <span className="truncate">{label}</span>
                  <span className="ml-auto text-[10px] uppercase tracking-wide opacity-70">
                    soon
                  </span>
                </>
              )}
            </span>
          ) : (
            <NavLink
              key={item.path}
              to={item.path}
              end={
                item.path === "/" ||
                item.path === "/payroll" ||
                item.path === "/invoices"
              }
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
              title={iconsOnly ? label : undefined}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {!iconsOnly && <span className="truncate">{label}</span>}
            </NavLink>
          );

          if (!startsSection && !endsSection) return link;

          return (
            <Fragment key={`section-${item.path}`}>
              {startsSection ? (
                !iconsOnly ? (
                  <p className="px-3 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/70">
                    {item.section}
                  </p>
                ) : (
                  <span className="my-1 border-t" aria-hidden="true" />
                )
              ) : null}
              {link}
              {endsSection ? (
                <span className="my-1 border-t" aria-hidden="true" />
              ) : null}
            </Fragment>
          );
        })}
      </nav>

      {!iconsOnly && (
        <p className="px-3 text-xs text-muted-foreground/70">
          People · time off · payroll · invoices
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
