import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "./page";

describe("HomePage", () => {
  it("renders the research-first trading workspace and safety state", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { name: /research-first trading workspace/i })).toBeInTheDocument();
    expect(screen.getByText("LIVE TRADING DISABLED")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Risk" })).toBeInTheDocument();
  });
});
