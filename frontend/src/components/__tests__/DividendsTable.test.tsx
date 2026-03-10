import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { DividendsTable } from "../DividendsTable";
import { Transaction } from "../../types";

const mockDividends: Transaction[] = [
  {
    id: "d1",
    user_id: "u1",
    asset_class_id: "c1",
    asset_symbol: "AAPL",
    type: "dividend",
    quantity: 0,
    unit_price: 0,
    total_value: 50.0,
    currency: "USD",
    tax_amount: 7.5,
    date: "2024-06-15",
    notes: "Q2 dividend",
    created_at: "2024-06-15",
    updated_at: "2024-06-15",
  },
  {
    id: "d2",
    user_id: "u1",
    asset_class_id: "c1",
    asset_symbol: "MSFT",
    type: "dividend",
    quantity: 0,
    unit_price: 0,
    total_value: 30.0,
    currency: "USD",
    tax_amount: 4.5,
    date: "2024-07-01",
    notes: null,
    created_at: "2024-07-01",
    updated_at: "2024-07-01",
  },
  {
    id: "d3",
    user_id: "u1",
    asset_class_id: "c1",
    asset_symbol: "AAPL",
    type: "dividend",
    quantity: 0,
    unit_price: 0,
    total_value: 55.0,
    currency: "USD",
    tax_amount: 8.25,
    date: "2024-09-15",
    notes: "Q3 dividend",
    created_at: "2024-09-15",
    updated_at: "2024-09-15",
  },
];

describe("DividendsTable", () => {
  it("renders dividend data", () => {
    render(
      <DividendsTable
        dividends={mockDividends}
        loading={false}
        onCreateTransaction={vi.fn()}
      />
    );

    expect(screen.getByText("Dividends")).toBeInTheDocument();
    expect(screen.getAllByText("AAPL")).toHaveLength(2);
    expect(screen.getByText("MSFT")).toBeInTheDocument();
    expect(screen.getByText("$50.00")).toBeInTheDocument();
    expect(screen.getByText("$30.00")).toBeInTheDocument();
    expect(screen.getByText("Q2 dividend")).toBeInTheDocument();
  });

  it("filters by symbol", async () => {
    const user = userEvent.setup();

    render(
      <DividendsTable
        dividends={mockDividends}
        loading={false}
        onCreateTransaction={vi.fn()}
      />
    );

    const filterInput = screen.getByPlaceholderText("Symbol...");
    await user.type(filterInput, "MSFT");

    expect(screen.getByText("MSFT")).toBeInTheDocument();
    expect(screen.queryByText("Q2 dividend")).not.toBeInTheDocument();
    expect(screen.queryByText("Q3 dividend")).not.toBeInTheDocument();
  });
});
