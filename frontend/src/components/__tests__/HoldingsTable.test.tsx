import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import { HoldingsTable } from "../HoldingsTable";
import { AssetClass, Holding, QuarantineStatus, Transaction } from "../../types";

const mockAssetClasses: AssetClass[] = [
  { id: "c1", user_id: "u1", name: "Stocks", target_weight: 60, country: "US", type: "stock", is_emergency_reserve: false, created_at: "2024-01-01", updated_at: "2024-01-01" },
];

const mockHoldings: Holding[] = [
  {
    symbol: "AAPL",
    asset_class_id: "c1",
    quantity: 10,
    avg_price: { amount: "150", currency: "USD" },
    total_cost: { amount: "1500", currency: "USD" },
    current_price: { amount: "170", currency: "USD" },
    current_value: { amount: "1700", currency: "USD" },
    gain_loss: { amount: "200", currency: "USD" },
    target_weight: 30,
    actual_weight: 35.5,
  },
  {
    symbol: "TSLA",
    asset_class_id: "c1",
    quantity: 5,
    avg_price: { amount: "200", currency: "USD" },
    total_cost: { amount: "1000", currency: "USD" },
    current_price: { amount: "180", currency: "USD" },
    current_value: { amount: "900", currency: "USD" },
    gain_loss: { amount: "-100", currency: "USD" },
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
    unit_price: { amount: "150", currency: "USD" },
    total_value: { amount: "1500", currency: "USD" },
    tax_amount: { amount: "0", currency: "USD" },
    date: "2024-01-15",
    notes: null,
    created_at: "2024-01-15",
    updated_at: "2024-01-15",
  },
];

describe("HoldingsTable", () => {
  it("renders holdings with data", () => {
    render(
      <MemoryRouter>
        <HoldingsTable
          holdings={mockHoldings}
          assetClassId="c1"
          assetClasses={mockAssetClasses}
          type="stock"
          loading={false}
          quarantineStatuses={mockQuarantineStatuses}
          transactions={[]}
          onFetchTransactions={vi.fn()}
          onCreateTransaction={vi.fn()}
        />
      </MemoryRouter>
    );

    expect(screen.getByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("TSLA")).toBeInTheDocument();
    expect(screen.getByText("$170.00")).toBeInTheDocument();
    expect(screen.getByText("+$200.00")).toBeInTheDocument();
    expect(screen.getByText("-$100.00")).toBeInTheDocument();
  });

  it("shows quarantine badge for quarantined assets", () => {
    render(
      <MemoryRouter>
        <HoldingsTable
          holdings={mockHoldings}
          assetClassId="c1"
          assetClasses={mockAssetClasses}
          type="stock"
          loading={false}
          quarantineStatuses={mockQuarantineStatuses}
          transactions={[]}
          onFetchTransactions={vi.fn()}
          onCreateTransaction={vi.fn()}
        />
      </MemoryRouter>
    );

    // TSLA is quarantined
    expect(screen.getByText("Quarantined")).toBeInTheDocument();
  });

  it("expand row shows transactions", async () => {
    const user = userEvent.setup();
    const fetchTransactions = vi.fn();

    const { rerender } = render(
      <MemoryRouter>
        <HoldingsTable
          holdings={mockHoldings}
          assetClassId="c1"
          assetClasses={mockAssetClasses}
          type="stock"
          loading={false}
          transactions={[]}
          onFetchTransactions={fetchTransactions}
          onCreateTransaction={vi.fn()}
        />
      </MemoryRouter>
    );

    // Click AAPL row to expand
    await user.click(screen.getByText("AAPL"));
    expect(fetchTransactions).toHaveBeenCalledWith("AAPL");

    // Rerender with transactions loaded
    rerender(
      <MemoryRouter>
        <HoldingsTable
          holdings={mockHoldings}
          assetClassId="c1"
          assetClasses={mockAssetClasses}
          type="stock"
          loading={false}
          transactions={mockTransactions}
          onFetchTransactions={fetchTransactions}
          onCreateTransaction={vi.fn()}
        />
      </MemoryRouter>
    );

    expect(screen.getByText("Transaction History")).toBeInTheDocument();
    expect(screen.getByText("2024-01-15")).toBeInTheDocument();
    expect(screen.getByText("$1,500.00")).toBeInTheDocument();
  });
});
