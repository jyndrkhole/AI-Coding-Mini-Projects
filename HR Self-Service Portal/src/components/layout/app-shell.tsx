"use client";

import {
  Bell,
  CalendarPlus,
  CalendarRange,
  ChartColumn,
  ClipboardList,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  Scale,
  ScrollText,
  SlidersHorizontal,
  UserRound,
  Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { logoutAction } from "@/server/auth/actions";
import { cn } from "@/lib/cn";

type IconName =
  | "dashboard"
  | "apply"
  | "leaves"
  | "calendar"
  | "profile"
  | "employees"
  | "manage"
  | "policies"
  | "balances"
  | "reports"
  | "audit";

const icons: Record<IconName, LucideIcon> = {
  dashboard: LayoutDashboard,
  apply: CalendarPlus,
  leaves: ListChecks,
  calendar: CalendarRange,
  profile: UserRound,
  employees: Users,
  manage: ClipboardList,
  policies: SlidersHorizontal,
  balances: Scale,
  reports: ChartColumn,
  audit: ScrollText,
};

type NavItem = { href: string; label: string; icon: IconName; exact?: boolean };

const employeeNav: NavItem[] = [
  { href: "/dashboard", label: "My Dashboard", icon: "dashboard", exact: true },
  { href: "/leave/new", label: "Apply for Leave", icon: "apply", exact: true },
  { href: "/leave", label: "My Leaves", icon: "leaves" },
  { href: "/calendar", label: "Leave Calendar", icon: "calendar" },
  { href: "/profile", label: "My Profile", icon: "profile" },
];

const adminNav: NavItem[] = [
  { href: "/admin", label: "Admin Dashboard", icon: "dashboard", exact: true },
  { href: "/admin/employees", label: "Employees", icon: "employees" },
  { href: "/admin/leave", label: "Leave Management", icon: "manage" },
  { href: "/admin/calendar", label: "Leave Calendar", icon: "calendar" },
  { href: "/admin/policies", label: "Leave Types & Policies", icon: "policies" },
  { href: "/admin/balances", label: "Leave Balances", icon: "balances" },
  { href: "/admin/reports", label: "Reports", icon: "reports" },
  { href: "/admin/audit", label: "Audit Log", icon: "audit" },
];

function isActive(pathname: string, item: NavItem) {
  if (item.href === "/leave") {
    return pathname === "/leave" || (pathname.startsWith("/leave/") && pathname !== "/leave/new");
  }
  if (item.exact) return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

export function AppShell({
  portal,
  companyName,
  userName,
  email,
  role,
  children,
}: {
  portal: "employee" | "admin";
  companyName: string;
  userName: string;
  email: string;
  role: "EMPLOYEE" | "ADMINISTRATOR" | "MANAGER";
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [alertsOpen, setAlertsOpen] = useState(false);
  const nav = portal === "admin" ? adminNav : employeeNav;
  const initials = userName
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();

  useEffect(() => {
    const stored = window.localStorage.getItem("peoplehub-sidebar");
    if (stored === "collapsed") setCollapsed(true);
  }, []);

  useEffect(() => {
    setMobileOpen(false);
    setMenuOpen(false);
  }, [pathname]);

  function toggleCollapsed() {
    setCollapsed((current) => {
      window.localStorage.setItem("peoplehub-sidebar", current ? "open" : "collapsed");
      return !current;
    });
  }

  const sidebar = (mobile: boolean) => (
    <div className={cn("flex h-full flex-col bg-white", mobile ? "w-72" : collapsed ? "w-[4.5rem]" : "w-64")}>
      <div className="flex h-16 items-center gap-3 border-b border-line px-4">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand text-sm font-semibold text-white">
          P
        </span>
        {(mobile || !collapsed) && (
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold">PeopleHub</span>
            <span className="block truncate text-xs text-muted">{companyName}</span>
          </span>
        )}
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label={portal === "admin" ? "Administration" : "Employee"}>
        {nav.map((item) => {
          const Icon = icons[item.icon];
          const active = isActive(pathname, item);
          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.label}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm",
                active ? "bg-brand/10 font-medium text-brand" : "text-muted hover:bg-canvas hover:text-ink",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              {(mobile || !collapsed) && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </nav>
    </div>
  );

  return (
    <div className="flex h-dvh overflow-hidden bg-canvas text-ink">
      <aside className="hidden border-r border-line md:block">{sidebar(false)}</aside>
      {mobileOpen ? (
        <div className="fixed inset-0 z-40 md:hidden">
          <button className="absolute inset-0 bg-ink/30" aria-label="Close menu" onClick={() => setMobileOpen(false)} />
          <div className="relative h-full border-r border-line shadow-none">{sidebar(true)}</div>
        </div>
      ) : null}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-line bg-white px-3 sm:px-4">
          <button
            type="button"
            className="grid h-9 w-9 place-items-center rounded-lg text-muted hover:bg-canvas md:hidden"
            aria-label="Open menu"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>
          <button
            type="button"
            className="hidden h-9 w-9 place-items-center rounded-lg text-muted hover:bg-canvas md:grid"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={toggleCollapsed}
          >
            {collapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
          </button>
          <div className="ml-auto flex items-center gap-1">
            <div className="relative">
              <button
                type="button"
                className="grid h-9 w-9 place-items-center rounded-lg text-muted hover:bg-canvas"
                aria-label="Notifications"
                aria-expanded={alertsOpen}
                onClick={() => {
                  setAlertsOpen((open) => !open);
                  setMenuOpen(false);
                }}
              >
                <Bell className="h-5 w-5" />
              </button>
              {alertsOpen ? (
                <div className="absolute right-0 z-20 mt-2 w-64 rounded-xl border border-line bg-white p-3 text-sm text-muted">
                  No notifications.
                </div>
              ) : null}
            </div>
            <div className="relative">
              <button
                type="button"
                className="flex items-center gap-2 rounded-lg px-2 py-1 hover:bg-canvas"
                aria-expanded={menuOpen}
                aria-haspopup="menu"
                onClick={() => {
                  setMenuOpen((open) => !open);
                  setAlertsOpen(false);
                }}
              >
                <span className="grid h-8 w-8 place-items-center rounded-full bg-brand/10 text-xs font-semibold text-brand">
                  {initials || "U"}
                </span>
                <span className="hidden text-left sm:block">
                  <span className="block max-w-40 truncate text-sm font-medium">{userName}</span>
                  <span className="block text-xs text-muted">{role === "ADMINISTRATOR" ? "Administrator" : "Employee"}</span>
                </span>
              </button>
              {menuOpen ? (
                <div role="menu" className="absolute right-0 z-20 mt-2 w-56 rounded-xl border border-line bg-white p-2">
                  <p className="truncate px-2 py-1 text-xs text-muted">{email}</p>
                  {role === "ADMINISTRATOR" && portal === "admin" ? (
                    <Link href="/dashboard" className="block rounded-lg px-2 py-2 text-sm hover:bg-canvas">
                      My leave
                    </Link>
                  ) : null}
                  {role === "ADMINISTRATOR" && portal === "employee" ? (
                    <Link href="/admin" className="block rounded-lg px-2 py-2 text-sm hover:bg-canvas">
                      Administration
                    </Link>
                  ) : null}
                  <form action={logoutAction}>
                    <button type="submit" className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-ink hover:bg-canvas">
                      <LogOut className="h-4 w-4" />
                      Log out
                    </button>
                  </form>
                </div>
              ) : null}
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-6xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
