import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { DataTable, type Column } from "./DataTable";
import type { AssetClass } from "../types";

interface AllocationInfo {
  actual_weight: number;
  diff: number;
}

interface AssetClassesTableProps {
  assetClasses: AssetClass[];
  loading: boolean;
  allocationMap?: Record<string, AllocationInfo>;
  onUpdateClass: (id: string, data: Partial<AssetClass>) => Promise<unknown>;
  onCreateClass: (name: string, targetWeight: number, type: "stock" | "crypto" | "fixed_income") => Promise<unknown>;
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
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newWeight, setNewWeight] = useState("");
  const [newType, setNewType] = useState<"stock" | "crypto" | "fixed_income">("stock");

  const rows: AssetClassRow[] = assetClasses.map((ac) => {
    const info = allocationMap[ac.id] ?? { actual_weight: 0, diff: 0 };
    return {
      ...ac,
      actual_weight: info.actual_weight,
      diff: info.diff,
    };
  });

  const columns: Column<AssetClassRow>[] = [
    {
      key: "name",
      header: "Name",
      sortable: true,
      render: (row) => (
        <span className="flex items-center gap-1">
          <span>{row.name}</span>
          <span className="text-text-muted text-xs">&rsaquo;</span>
        </span>
      ),
    },
    {
      key: "type",
      header: "Type",
      sortable: true,
      render: (row) => (
        <span className="text-text-muted capitalize">{row.type.replace("_", " ")}</span>
      ),
    },
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
        const color = row.diff > 0 ? "text-positive" : row.diff < 0 ? "text-negative" : "";
        return <span className={color}>{row.diff > 0 ? "+" : ""}{row.diff.toFixed(1)}%</span>;
      },
    },
    {
      key: "_actions",
      header: "",
      render: (row) => (
        <button
          className="bg-[var(--glass-negative-soft)] text-negative px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-[rgba(239,68,68,0.15)]"
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
    await onCreateClass(newName.trim(), parseFloat(newWeight) || 0, newType);
    setNewName("");
    setNewWeight("");
    setNewType("stock");
    setShowForm(false);
  };

  if (loading) {
    return <div>Loading asset classes...</div>;
  }

  return (
    <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-text-primary tracking-[-0.3px]">Asset Classes</h2>
        <button
          className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover"
          onClick={() => setShowForm(!showForm)}
        >
          Add Class
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="mb-4 flex gap-2 items-end">
          <div>
            <label className="block text-base text-text-muted mb-1">Name</label>
            <input
              type="text"
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Class name"
            />
          </div>
          <div>
            <label className="block text-base text-text-muted mb-1">Type</label>
            <select
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
              value={newType}
              onChange={(e) => setNewType(e.target.value as "stock" | "crypto" | "fixed_income")}
            >
              <option value="stock">Stock</option>
              <option value="crypto">Crypto</option>
              <option value="fixed_income">Fixed Income</option>
            </select>
          </div>
          <div>
            <label className="block text-base text-text-muted mb-1">Target Weight (%)</label>
            <input
              type="number"
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary w-24"
              value={newWeight}
              onChange={(e) => setNewWeight(e.target.value)}
              placeholder="0"
            />
          </div>
          <button
            type="submit"
            className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover"
          >
            Save
          </button>
          <button
            type="button"
            className="bg-[rgba(0,0,0,0.03)] border border-[var(--glass-border)] text-text-secondary px-4 py-2 rounded-[10px] text-base font-medium hover:bg-[rgba(0,0,0,0.06)]"
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
        onRowClick={(row) => navigate(`/portfolio/${row.id}`)}
      />
    </div>
  );
}
