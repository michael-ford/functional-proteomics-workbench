import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { navItems, PageHeader, WorkspaceShell } from "./workspace-shell";

const mockUsePathname = vi.fn(() => "/");

vi.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
}));

describe("WorkspaceShell", () => {
  beforeEach(() => {
    mockUsePathname.mockReturnValue("/");
  });

  it("exposes the core workbench navigation surfaces", () => {
    render(
      <WorkspaceShell>
        <PageHeader
          eyebrow="Project"
          title="Demo project workspace"
          description="Smoke test content"
        />
      </WorkspaceShell>
    );

    for (const item of navItems) {
      expect(screen.getAllByRole("link", { name: item.label }).length).toBeGreaterThan(0);
    }
    expect(screen.getByRole("heading", { name: "Demo project workspace" })).toBeVisible();
  });

  it.each(navItems)("marks $href as current in desktop and mobile navigation", (currentItem) => {
    mockUsePathname.mockReturnValue(currentItem.href);

    render(
      <WorkspaceShell>
        <PageHeader eyebrow="Project" title="Demo project workspace" description="Smoke test content" />
      </WorkspaceShell>
    );

    const currentLinks = screen.getAllByRole("link", { current: "page" });

    expect(currentLinks).toHaveLength(2);
    expect(currentLinks.every((link) => link.getAttribute("href") === currentItem.href)).toBe(true);

    for (const item of navItems.filter((item) => item.href !== currentItem.href)) {
      for (const link of screen.getAllByRole("link", { name: item.label })) {
        expect(link).not.toHaveAttribute("aria-current");
      }
    }
  });

  it("keeps project current state scoped to the root route", () => {
    mockUsePathname.mockReturnValue("/datasets/subset");

    render(
      <WorkspaceShell>
        <PageHeader eyebrow="Dataset" title="Dataset detail" description="Smoke test content" />
      </WorkspaceShell>
    );

    expect(screen.getAllByRole("link", { name: "Dataset", current: "page" })).toHaveLength(2);
    for (const link of screen.getAllByRole("link", { name: "Project" })) {
      expect(link).not.toHaveAttribute("aria-current");
    }
  });
});
