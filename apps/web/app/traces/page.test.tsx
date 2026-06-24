import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import TracePage from "./page";

describe("TracePage", () => {
  it("renders trace model records with provenance and expandable payloads", () => {
    render(<TracePage />);

    expect(screen.getByRole("heading", { name: "Tool-call audit trail" })).toBeVisible();
    expect(screen.getAllByText("define_comparison").length).toBeGreaterThan(0);
    expect(screen.getAllByText("search_corpus").length).toBeGreaterThan(0);
    expect(screen.getByText("Ordered trace model records")).toBeVisible();
    expect(screen.getAllByText(/chat_01K1M9M8J6T2P3R4S5T6V7W8X9/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Input").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Output").length).toBeGreaterThan(0);
  });
});
