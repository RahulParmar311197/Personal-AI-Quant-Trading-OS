import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "./page";

describe("HomePage", () => {
  it("renders the operator dashboard and safety state", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { name: /operator dashboard/i })).toBeInTheDocument();
    expect(screen.getByText("LIVE TRADING DISABLED")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Risk" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Control plane" })).toBeInTheDocument();
    expect(screen.getByText("Paper-first")).toBeInTheDocument();
    expect(screen.getByText("High volatility")).toBeInTheDocument();
  });
});
