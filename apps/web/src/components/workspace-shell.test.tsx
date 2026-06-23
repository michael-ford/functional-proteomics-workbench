import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { navItems, PageHeader, WorkspaceShell } from "./workspace-shell";

describe("WorkspaceShell", () => {
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
});
