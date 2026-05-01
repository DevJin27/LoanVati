import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RiskBadge } from "./RiskBadge";

describe("RiskBadge", () => {
  it("normalizes uncertain risk text", () => {
    render(<RiskBadge level="Uncertain - Manual Review Required" />);
    expect(screen.getByText("Uncertain")).toBeInTheDocument();
  });
});
