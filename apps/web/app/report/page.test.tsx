import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ReportPage from "./page";

describe("ReportPage", () => {
  it("renders the generated report claims and approved evidence citations", () => {
    render(<ReportPage />);

    expect(
      screen.getByRole("heading", { name: "IL-10 vs matched control under LPS 2000 ng/mL" })
    ).toBeVisible();
    expect(screen.getByText("Ranked fixture result")).toBeVisible();
    expect(screen.getByText("Conservative biological readout")).toBeVisible();
    expect(screen.getAllByText("src_dagher_2025_nelisa").length).toBeGreaterThan(0);
    expect(screen.getByText("report_demo_il10_lps")).toBeVisible();
  });
});
