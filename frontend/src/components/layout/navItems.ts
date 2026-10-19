/** Sidebar navigation, filtered by role.
 *
 * The menu is a UX affordance only. Every page it links to is enforced by the
 * API's permission classes, so hiding an item is never the security control.
 *
 * Items beyond Dashboard are placeholders until their phase lands. They are
 * rendered disabled rather than omitted, so the intended information
 * architecture is visible without implying the feature exists.
 */

import {
  CalendarDays,
  CalendarRange,
  ClipboardCheck,
  LayoutDashboard,
  ScrollText,
  Users,
  UsersRound,
  type LucideIcon,
} from "lucide-react";

import type { Role } from "@/api/queries";

export type NavItem = {
  label: string;
  path: string;
  icon: LucideIcon;
  /** Roles that may see this item. */
  allow: Role[];
  /** False until the phase that builds it lands. */
  available: boolean;
};

export const ALL_ROLES: Role[] = ["admin", "hr", "manager", "employee"];

export const NAV_ITEMS: NavItem[] = [
  {
    label: "Dashboard",
    path: "/",
    icon: LayoutDashboard,
    allow: ALL_ROLES,
    available: true,
  },
  {
    label: "Employees",
    path: "/employees",
    icon: Users,
    allow: ["admin", "hr", "manager"],
    available: true,
  },
  {
    label: "Teams",
    path: "/teams",
    icon: UsersRound,
    allow: ["admin", "hr"],
    available: true,
  },
  {
    label: "My time off",
    path: "/time-off",
    icon: CalendarDays,
    allow: ALL_ROLES,
    available: true,
  },
  {
    label: "Approvals",
    path: "/approvals",
    icon: ClipboardCheck,
    allow: ["admin", "hr", "manager"],
    available: true,
  },
  {
    label: "Team calendar",
    path: "/team-calendar",
    icon: CalendarRange,
    allow: ALL_ROLES,
    available: true,
  },
  {
    label: "Audit log",
    path: "/audit-log",
    icon: ScrollText,
    allow: ["admin", "hr"],
    available: true,
  },
];

export function visibleNavItems(role: Role | null): NavItem[] {
  if (role === null) return [];
  return NAV_ITEMS.filter((item) => item.allow.includes(role));
}
