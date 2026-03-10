import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { QuarantineBadge } from "../QuarantineBadge";

describe("QuarantineBadge", () => {
  it("renders nothing when not quarantined", () => {
    const { container } = render(<QuarantineBadge isQuarantined={false} />);
    expect(container.innerHTML).toBe("");
  });

  it("renders badge when quarantined", () => {
    render(<QuarantineBadge isQuarantined={true} />);
    expect(screen.getByText("Quarantined")).toBeInTheDocument();
  });

  it("shows end date when provided", () => {
    render(
      <QuarantineBadge isQuarantined={true} endsAt="2026-04-01T00:00:00Z" />
    );
    expect(screen.getByText("Quarantined")).toBeInTheDocument();
    expect(screen.getByTitle(/until/)).toBeInTheDocument();
  });
});
