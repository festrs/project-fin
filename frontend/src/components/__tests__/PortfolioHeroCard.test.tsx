import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import PortfolioHeroCard from "../PortfolioHeroCard";

describe("PortfolioHeroCard", () => {
  it("renders formatted portfolio value", () => {
    render(<PortfolioHeroCard grandTotalBRL={1248392.42} loading={false} />);
    expect(screen.getByText(/1\.248\.392,42/)).toBeInTheDocument();
    expect(screen.getByText("Total balance")).toBeInTheDocument();
  });

  it("shows loading skeleton when loading", () => {
    const { container } = render(<PortfolioHeroCard grandTotalBRL={0} loading={true} />);
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("renders all period selector buttons as enabled", () => {
    render(<PortfolioHeroCard grandTotalBRL={100000} loading={false} />);
    const periods = ["1D", "1W", "1M", "1Y", "ALL"];
    for (const p of periods) {
      const btn = screen.getByText(p);
      expect(btn).toBeInTheDocument();
      expect(btn).not.toBeDisabled();
    }
  });
});
