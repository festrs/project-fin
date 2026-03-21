import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import PortfolioHeroCard from "../PortfolioHeroCard";

describe("PortfolioHeroCard", () => {
  it("renders formatted portfolio value", () => {
    render(<PortfolioHeroCard grandTotalBRL={1248392.42} loading={false} />);
    expect(screen.getByText(/1\.248\.392,42/)).toBeInTheDocument();
    expect(screen.getByText("Portfolio Value")).toBeInTheDocument();
  });

  it("shows loading skeleton when loading", () => {
    const { container } = render(<PortfolioHeroCard grandTotalBRL={0} loading={true} />);
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("renders period selector with coming soon tooltips", () => {
    render(<PortfolioHeroCard grandTotalBRL={100000} loading={false} />);
    expect(screen.getByText("1D")).toHaveAttribute("title", "Coming soon");
    expect(screen.getByText("1M")).not.toHaveAttribute("title");
  });
});
