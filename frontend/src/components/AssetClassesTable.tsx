import { useState } from "react";
import { DataTable, Column } from "./DataTable";
import { AssetClass } from "../types";

interface AllocationInfo {
  actual_weight: number;
  diff: number;
}

interface AssetClassesTableProps {
  assetClasses: AssetClass[];
  loading: boolean;
  allocationMap?: Record<string, AllocationInfo>;
  onUpdateClass: (id: string, data: Partial<AssetClass>) => Promise<unknown>;
  onCreateClass: (name: string, targetWeight: number) => Promise<unknown>;
  onDeleteClass: (id: string) => Promise<unknown>;
}

type AssetClassRow = AssetClass & {
  actual_weight: number;
  diff: number;
};

export function AssetClassesTable({
  assetClasses,
  loading,
  allocationMap = {},
  onUpdateClass,
  onCreateClass,
  onDeleteClass,
}: AssetClassesTableProps) {
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newWeight, setNewWeight] = useState("");

  const rows: AssetClassRow[] = assetClasses.map((ac) => {
    const info = allocationMap[ac.id] ?? { actual_weight: 0, diff: 0 };
    return {
      ...ac,
      actual_weight: info.actual_weight,
      diff: info.diff,
    };
  });

  const columns: Column<AssetClassRow>[] = [
    { key: "name", header: "Name", sortable: true },
    {
      key: "target_weight",
      header: "Target Weight",
      sortable: true,
      editable: true,
      onEdit: (row, value) => {
        const parsed = parseFloat(value);
        if (!isNaN(parsed)) {
          onUpdateClass(row.id, { target_weight: parsed });
        }
      },
      render: (row) => `${row.target_weight}%`,
    },
    {
      key: "actual_weight",
      header: "Actual Weight",
      sortable: true,
      render: (row) => `${row.actual_weight.toFixed(1)}%`,
    },
    {
      key: "diff",
      header: "Diff",
      sortable: true,
      render: (row) => {
        const color = row.diff > 0 ? "text-green-600" : row.diff < 0 ? "text-red-600" : "";
        return <span className={color}>{row.diff > 0 ? "+" : ""}{row.diff.toFixed(1)}%</span>;
      },
    },
    {
      key: "_actions",
      header: "",
      render: (row) => (
        <button
          className="text-red-500 hover:text-red-700 text-sm"
          onClick={(e) => {
            e.stopPropagation();
            onDeleteClass(row.id);
          }}
        >
          Delete
        </button>
      ),
    },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    await onCreateClass(newName.trim(), parseFloat(newWeight) || 0);
    setNewName("");
    setNewWeight("");
    setShowForm(false);
  };

  if (loading) {
    return <div>Loading asset classes...</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Asset Classes</h2>
        <button
          className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
          onClick={() => setShowForm(!showForm)}
        >
          Add Class
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-4 flex gap-2 items-end">
          <div>
            <label className="block text-xs text-gray-600 mb-1">Name</label>
            <input
              type="text"
              className="border rounded px-2 py-1 text-sm"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Class name"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Target Weight (%)</label>
            <input
              type="number"
              className="border rounded px-2 py-1 text-sm w-24"
              value={newWeight}
              onChange={(e) => setNewWeight(e.target.value)}
              placeholder="0"
            />
          </div>
          <button
            type="submit"
            className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
          >
            Save
          </button>
          <button
            type="button"
            className="text-gray-500 px-3 py-1 rounded text-sm hover:text-gray-700"
            onClick={() => setShowForm(false)}
          >
            Cancel
          </button>
        </form>
      )}

      <DataTable
        columns={columns}
        data={rows}
        getRowId={(r) => r.id}
      />
    </div>
  );
}
