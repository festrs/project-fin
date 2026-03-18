import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import { AssetClassesTable } from "../AssetClassesTable";
import { AssetClass } from "../../types";

const mockClasses: AssetClass[] = [
  {
    id: "1",
    user_id: "u1",
    name: "Stocks",
    target_weight: 60,
    country: "US",
    type: "stock",
    created_at: "2024-01-01",
    updated_at: "2024-01-01",
  },
  {
    id: "2",
    user_id: "u1",
    name: "Bonds",
    target_weight: 40,
    country: "US",
    type: "fixed_income",
    created_at: "2024-01-01",
    updated_at: "2024-01-01",
  },
];

const allocationMap = {
  "1": { actual_weight: 55, diff: -5 },
  "2": { actual_weight: 45, diff: 5 },
};

describe("AssetClassesTable", () => {
  it("renders table with asset classes", () => {
    render(
      <MemoryRouter><AssetClassesTable
        assetClasses={mockClasses}
        loading={false}
        allocationMap={allocationMap}
        onUpdateClass={vi.fn()}
        onCreateClass={vi.fn()}
        onDeleteClass={vi.fn()}
      /></MemoryRouter>
    );

    expect(screen.getByText("Stocks")).toBeInTheDocument();
    expect(screen.getByText("Bonds")).toBeInTheDocument();
    expect(screen.getByText("60%")).toBeInTheDocument();
    expect(screen.getByText("40%")).toBeInTheDocument();
    expect(screen.getByText("55.0%")).toBeInTheDocument();
    expect(screen.getByText("-5.0%")).toBeInTheDocument();
    expect(screen.getByText("+5.0%")).toBeInTheDocument();
  });

  it("inline edit triggers update API call", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn().mockResolvedValue({});

    render(
      <MemoryRouter><AssetClassesTable
        assetClasses={mockClasses}
        loading={false}
        allocationMap={allocationMap}
        onUpdateClass={onUpdate}
        onCreateClass={vi.fn()}
        onDeleteClass={vi.fn()}
      /></MemoryRouter>
    );

    // Double-click the target weight cell to edit
    const cell = screen.getByText("60%");
    await user.dblClick(cell);

    // Should show input with current value
    const input = screen.getByDisplayValue("60");
    await user.clear(input);
    await user.type(input, "65{Enter}");

    expect(onUpdate).toHaveBeenCalledWith("1", { target_weight: 65 });
  });
});
