import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { DataTable, Column } from "../DataTable";

interface TestItem {
  id: string;
  name: string;
  value: number;
}

const columns: Column<TestItem>[] = [
  { key: "name", header: "Name", sortable: true },
  {
    key: "value",
    header: "Value",
    sortable: true,
    render: (row) => `$${row.value}`,
  },
];

const data: TestItem[] = [
  { id: "1", name: "Alpha", value: 30 },
  { id: "2", name: "Beta", value: 10 },
  { id: "3", name: "Charlie", value: 20 },
];

describe("DataTable", () => {
  it("renders table with data", () => {
    render(
      <DataTable columns={columns} data={data} getRowId={(r) => r.id} />
    );
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Value")).toBeInTheDocument();
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
    expect(screen.getByText("Charlie")).toBeInTheDocument();
    expect(screen.getByText("$30")).toBeInTheDocument();
  });

  it("sorts when clicking sortable column header", async () => {
    const user = userEvent.setup();
    render(
      <DataTable columns={columns} data={data} getRowId={(r) => r.id} />
    );

    // Click Name header to sort ascending
    await user.click(screen.getByText("Name"));
    const rows = screen.getAllByRole("row");
    // row 0 is header, rows 1-3 are data
    expect(rows[1]).toHaveTextContent("Alpha");
    expect(rows[2]).toHaveTextContent("Beta");
    expect(rows[3]).toHaveTextContent("Charlie");

    // Click again to sort descending
    await user.click(screen.getByText("Name"));
    const rows2 = screen.getAllByRole("row");
    expect(rows2[1]).toHaveTextContent("Charlie");
    expect(rows2[2]).toHaveTextContent("Beta");
    expect(rows2[3]).toHaveTextContent("Alpha");
  });

  it("filters data by text input", async () => {
    const user = userEvent.setup();
    render(
      <DataTable
        columns={columns}
        data={data}
        getRowId={(r) => r.id}
        filterKey="name"
        filterPlaceholder="Search by name..."
      />
    );

    const input = screen.getByPlaceholderText("Search by name...");
    await user.type(input, "al");

    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.queryByText("Beta")).not.toBeInTheDocument();
    expect(screen.queryByText("Charlie")).not.toBeInTheDocument();
  });

  it("inline edit triggers onEdit callback", async () => {
    const user = userEvent.setup();
    const onEdit = vi.fn();

    const editableColumns: Column<TestItem>[] = [
      { key: "name", header: "Name", editable: true, onEdit },
      { key: "value", header: "Value" },
    ];

    render(
      <DataTable
        columns={editableColumns}
        data={data}
        getRowId={(r) => r.id}
      />
    );

    // Double-click to enter edit mode
    const cell = screen.getByText("Alpha");
    await user.dblClick(cell);

    // Should show an input with current value
    const input = screen.getByDisplayValue("Alpha");
    await user.clear(input);
    await user.type(input, "AlphaEdited{Enter}");

    expect(onEdit).toHaveBeenCalledWith(data[0], "AlphaEdited");
  });
});
