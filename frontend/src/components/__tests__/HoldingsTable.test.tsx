import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { HoldingsTable } from "../HoldingsTable";
import { Holding, QuarantineStatus, Transaction } from "../../types";

const mockHoldings: Holding[] = [
  {
    symbol: "AAPL",
    asset_class_id: "c1",
    quantity: 10,
    avg_price: 150,
    total_cost: 1500,
    current_price: 170,
    current_value: 1700,
    gain_loss: 200,
    target_weight: 30,
    actual_weight: 35.5,
  },
  {
    symbol: "TSLA",
    asset_class_id: "c1",
    quantity: 5,
    avg_price: 200,
    total_cost: 1000,
    current_price: 180,
    current_value: 900,
    gain_loss: -100,
    target_weight: 20,
    actual_weight: 18.8,
  },
];

const mockQuarantineStatuses: QuarantineStatus[] = [
  {
    asset_symbol: "TSLA",
    buy_count_in_period: 5,
    is_quarantined: true,
    quarantine_ends_at: "2025-06-01",
  },
];

const mockTransactions: Transaction[] = [
  {
    id: "t1",
    user_id: "u1",
    asset_class_id: "c1",
    asset_symbol: "AAPL",
    type: "buy",
    quantity: 10,
    unit_price: 150,
    total_value: 1500,
    currency: "USD",
    tax_amount: 0,
    date: "2024-01-15",
    notes: null,
    created_at: "2024-01-15",
    updated_at: "2024-01-15",
  },
];

describe("HoldingsTable", () => {
  it("renders holdings with data", () => {
    render(
      <HoldingsTable
        holdings={mockHoldings}
        loading={false}
        quarantineStatuses={mockQuarantineStatuses}
        transactions={[]}
        onFetchTransactions={vi.fn()}
        onCreateTransaction={vi.fn()}
      />
    );

    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("TSLA")).toBeInTheDocument();
    expect(screen.getByText("$170.00")).toBeInTheDocument();
    expect(screen.getByText("+$200.00")).toBeInTheDocument();
    expect(screen.getByText("-$100.00")).toBeInTheDocument();
  });

  it("shows quarantine badge for quarantined assets", () => {
    render(
      <HoldingsTable
        holdings={mockHoldings}
        loading={false}
        quarantineStatuses={mockQuarantineStatuses}
        transactions={[]}
        onFetchTransactions={vi.fn()}
        onCreateTransaction={vi.fn()}
      />
    );

    // TSLA is quarantined
    expect(screen.getByText("Quarantined")).toBeInTheDocument();
  });

  it("expand row shows transactions", async () => {
    const user = userEvent.setup();
    const fetchTransactions = vi.fn();

    const { rerender } = render(
      <HoldingsTable
        holdings={mockHoldings}
        loading={false}
        transactions={[]}
        onFetchTransactions={fetchTransactions}
        onCreateTransaction={vi.fn()}
      />
    );

    // Click AAPL row to expand
    await user.click(screen.getByText("AAPL"));
    expect(fetchTransactions).toHaveBeenCalledWith("AAPL");

    // Rerender with transactions loaded
    rerender(
      <HoldingsTable
        holdings={mockHoldings}
        loading={false}
        transactions={mockTransactions}
        onFetchTransactions={fetchTransactions}
        onCreateTransaction={vi.fn()}
      />
    );

    expect(screen.getByText("Transaction History")).toBeInTheDocument();
    expect(screen.getByText("2024-01-15")).toBeInTheDocument();
    expect(screen.getByText("$1500.00")).toBeInTheDocument();
  });
});
