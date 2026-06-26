"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Database, FileText, GitBranch, Home, ListChecks, type LucideIcon } from "lucide-react";

import type { NavItem } from "./workspace-shell";

const navIcons: Record<NavItem["icon"], LucideIcon> = {
  home: Home,
  database: Database,
  fileText: FileText,
  gitBranch: GitBranch,
  listChecks: ListChecks,
};

export function WorkspaceNavLink({
  item,
  className,
  activeClassName,
  inactiveClassName,
  iconSize,
}: {
  item: NavItem;
  className: string;
  activeClassName: string;
  inactiveClassName: string;
  iconSize: number;
}) {
  const pathname = usePathname();
  const isActive = isActiveRoute(pathname, item.href);
  const Icon = navIcons[item.icon];

  return (
    <Link
      href={item.href}
      aria-current={isActive ? "page" : undefined}
      className={`${className} ${isActive ? activeClassName : inactiveClassName}`}
    >
      <Icon size={iconSize} aria-hidden="true" />
      <span className="truncate">{item.label}</span>
    </Link>
  );
}

function isActiveRoute(pathname: string | null, href: string) {
  if (!pathname) {
    return href === "/";
  }

  const normalizedPathname = normalizePathname(pathname);
  if (href === "/") {
    return normalizedPathname === "/";
  }

  return normalizedPathname === href || normalizedPathname.startsWith(`${href}/`);
}

function normalizePathname(pathname: string) {
  if (pathname.length > 1 && pathname.endsWith("/")) {
    return pathname.slice(0, -1);
  }

  return pathname;
}
