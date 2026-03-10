import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { RecommendationCard } from "../RecommendationCard";
import { Recommendation } from "../../types";

describe("RecommendationCard", () => {
  it("renders recommendations correctly", () => {
    const recommendations: Recommendation[] = [
      {
        symbol: "AAPL",
        class_name: "US Stocks",
        effective_target: 30,
        actual_weight: 20,
        diff: 10,
      },
      {
        symbol: "GOOGL",
        class_name: "US Stocks",
        effective_target: 25,
        actual_weight: 30,
        diff: -5,
      },
    ];

    render(<RecommendationCard recommendations={recommendations} />);

    expect(screen.getByText("Recommendations")).toBeInTheDocument();
    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("GOOGL")).toBeInTheDocument();
    expect(screen.getByText("+10.0%")).toBeInTheDocument();
    expect(screen.getByText("-5.0%")).toBeInTheDocument();
  });

  it('shows "no recommendations" when empty', () => {
    render(<RecommendationCard recommendations={[]} />);

    expect(screen.getByText("Recommendations")).toBeInTheDocument();
    expect(screen.getByText("No recommendations available")).toBeInTheDocument();
  });
});
