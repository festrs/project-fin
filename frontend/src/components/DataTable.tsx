import { useState, useCallback } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  sortable?: boolean;
  editable?: boolean;
  onEdit?: (row: T, value: string) => void;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  filterPlaceholder?: string;
  filterKey?: string;
  onRowClick?: (row: T) => void;
  expandedRow?: string | null;
  renderExpanded?: (row: T) => React.ReactNode;
  getRowId: (row: T) => string;
}

type SortDirection = "asc" | "desc";

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  filterPlaceholder,
  filterKey,
  onRowClick,
  expandedRow,
  renderExpanded,
  getRowId,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDirection>("asc");
  const [filter, setFilter] = useState("");
  const [editingCell, setEditingCell] = useState<{
    rowId: string;
    colKey: string;
  } | null>(null);
  const [editValue, setEditValue] = useState("");

  const handleSort = useCallback(
    (key: string) => {
      if (sortKey === key) {
        setSortDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setSortKey(key);
        setSortDir("asc");
      }
    },
    [sortKey]
  );

  const handleDoubleClick = (row: T, col: Column<T>) => {
    if (!col.editable) return;
    setEditingCell({ rowId: getRowId(row), colKey: col.key });
    setEditValue(String(row[col.key] ?? ""));
  };

  const commitEdit = (row: T, col: Column<T>) => {
    col.onEdit?.(row, editValue);
    setEditingCell(null);
  };

  // Filter
  let processed = data;
  if (filterKey && filter) {
    const lowerFilter = filter.toLowerCase();
    processed = processed.filter((row) =>
      String(row[filterKey] ?? "")
        .toLowerCase()
        .includes(lowerFilter)
    );
  }

  // Sort
  if (sortKey) {
    processed = [...processed].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      let cmp = 0;
      if (typeof aVal === "number" && typeof bVal === "number") {
        cmp = aVal - bVal;
      } else {
        cmp = String(aVal ?? "").localeCompare(String(bVal ?? ""));
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }

  return (
    <div>
      {filterKey && (
        <input
          type="text"
          className="mb-3 w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder={filterPlaceholder ?? "Filter..."}
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      )}
      <table className="w-full text-sm text-left">
        <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-4 py-3 ${col.sortable ? "cursor-pointer select-none" : ""}`}
                onClick={col.sortable ? () => handleSort(col.key) : undefined}
              >
                {col.header}
                {col.sortable && sortKey === col.key && (
                  <span className="ml-1">{sortDir === "asc" ? "\u25B2" : "\u25BC"}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {processed.map((row) => {
            const rowId = getRowId(row);
            const isExpanded = expandedRow === rowId;
            return (
              <tr key={rowId} className="even:bg-gray-50">
                {columns.map((col) => {
                  const isEditing =
                    editingCell?.rowId === rowId &&
                    editingCell?.colKey === col.key;

                  return (
                    <td
                      key={col.key}
                      className={`px-4 py-3 ${onRowClick ? "cursor-pointer" : ""}`}
                      onClick={() => onRowClick?.(row)}
                      onDoubleClick={() => handleDoubleClick(row, col)}
                    >
                      {isEditing ? (
                        <input
                          type="text"
                          className="border border-blue-400 rounded px-1 py-0.5 text-sm w-full"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onBlur={() => commitEdit(row, col)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") commitEdit(row, col);
                            if (e.key === "Escape") setEditingCell(null);
                          }}
                          autoFocus
                        />
                      ) : col.render ? (
                        col.render(row)
                      ) : (
                        String(row[col.key] ?? "")
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
      {/* Render expanded rows outside the table for simplicity, or inline */}
      {expandedRow &&
        renderExpanded &&
        processed.map((row) => {
          if (getRowId(row) !== expandedRow) return null;
          return (
            <div key={`expanded-${getRowId(row)}`} className="px-4 py-3 bg-gray-50 border-t">
              {renderExpanded(row)}
            </div>
          );
        })}
    </div>
  );
}
