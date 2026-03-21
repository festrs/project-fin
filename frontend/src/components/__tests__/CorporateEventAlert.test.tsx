import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import CorporateEventAlert from "../CorporateEventAlert";
import type { StockSplit } from "../../types";

const mockSplit: StockSplit = {
  id: "s1",
  symbol: "AAPL",
  split_date: "2025-06-15",
  from_factor: 1,
  to_factor: 4,
  event_type: "split",
  detected_at: "2025-06-10",
  current_quantity: 10,
  new_quantity: 40,
};

describe("CorporateEventAlert", () => {
  it("renders nothing when no splits", () => {
    const { container } = render(
      <CorporateEventAlert splits={[]} actionLoading={{}} onApply={vi.fn()} onDismiss={vi.fn()} />
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders split alert with correct info", () => {
    render(
      <CorporateEventAlert splits={[mockSplit]} actionLoading={{}} onApply={vi.fn()} onDismiss={vi.fn()} />
    );
    expect(screen.getByText(/AAPL Stock Split/)).toBeInTheDocument();
    expect(screen.getByText(/1:4/)).toBeInTheDocument();
    expect(screen.getByText(/10 shares → 40 shares/)).toBeInTheDocument();
  });

  it("calls onApply when Apply is clicked", () => {
    const onApply = vi.fn();
    render(
      <CorporateEventAlert splits={[mockSplit]} actionLoading={{}} onApply={onApply} onDismiss={vi.fn()} />
    );
    fireEvent.click(screen.getByText("Apply"));
    expect(onApply).toHaveBeenCalledWith("s1");
  });

  it("calls onDismiss when Dismiss is clicked", () => {
    const onDismiss = vi.fn();
    render(
      <CorporateEventAlert splits={[mockSplit]} actionLoading={{}} onApply={vi.fn()} onDismiss={onDismiss} />
    );
    fireEvent.click(screen.getByText("Dismiss"));
    expect(onDismiss).toHaveBeenCalledWith("s1");
  });

  it("shows loading state when action is in progress", () => {
    render(
      <CorporateEventAlert splits={[mockSplit]} actionLoading={{ s1: true }} onApply={vi.fn()} onDismiss={vi.fn()} />
    );
    expect(screen.getByText("Applying...")).toBeInTheDocument();
  });
});
