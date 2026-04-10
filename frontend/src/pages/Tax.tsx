import { useState } from "react";
import { useTaxReport } from "../hooks/useTaxReport";

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const currentYear = new Date().getFullYear();
const YEARS = Array.from({ length: 5 }, (_, i) => currentYear - i);

function formatBRL(value: string) {
  const num = parseFloat(value);
  return `R$ ${num.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function Tax() {
  const [year, setYear] = useState(currentYear);
  const { report, loading, error } = useTaxReport(year);

  const nonEmptyMonths = report.filter(
    (entry) =>
      parseFloat(entry.stocks.total_sales) !== 0 ||
      parseFloat(entry.fiis.total_sales) !== 0
  );

  const totalGains = nonEmptyMonths.reduce(
    (sum, e) => sum + parseFloat(e.stocks.total_gain) + parseFloat(e.fiis.total_gain),
    0
  );

  const totalDarf = nonEmptyMonths.reduce(
    (sum, e) => sum + parseFloat(e.total_tax_due),
    0
  );

  const monthsWithDarf = nonEmptyMonths.filter(
    (e) => parseFloat(e.total_tax_due) > 0
  ).length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h1 className="text-display" style={{ fontSize: "2rem" }}>
          Tax Report
        </h1>
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="input-field w-32"
        >
          {YEARS.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="card" style={{ color: "#ff3b30" }}>
          {error}
        </div>
      )}

      {loading && (
        <div className="card" style={{ color: "var(--text-secondary)" }}>
          Loading...
        </div>
      )}

      {!loading && !error && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="card">
              <p
                className="text-sm font-medium mb-1"
                style={{ color: "var(--text-secondary)" }}
              >
                Total Gains
              </p>
              <p
                className="text-2xl font-semibold"
                style={{ color: totalGains >= 0 ? "#34c759" : "#ff3b30" }}
              >
                {formatBRL(totalGains.toFixed(2))}
              </p>
            </div>
            <div className="card">
              <p
                className="text-sm font-medium mb-1"
                style={{ color: "var(--text-secondary)" }}
              >
                Total DARF Due
              </p>
              <p
                className="text-2xl font-semibold"
                style={{ color: totalDarf > 0 ? "#ff3b30" : "var(--text-primary)" }}
              >
                {formatBRL(totalDarf.toFixed(2))}
              </p>
            </div>
            <div className="card">
              <p
                className="text-sm font-medium mb-1"
                style={{ color: "var(--text-secondary)" }}
              >
                Months with DARF
              </p>
              <p className="text-2xl font-semibold" style={{ color: "var(--text-primary)" }}>
                {monthsWithDarf}
              </p>
            </div>
          </div>

          {/* Monthly table */}
          {nonEmptyMonths.length === 0 ? (
            <div
              className="card text-center"
              style={{ color: "var(--text-secondary)", padding: "48px 24px" }}
            >
              No sell transactions in {year}
            </div>
          ) : (
            <div className="card" style={{ padding: 0, overflow: "hidden" }}>
              <div style={{ overflowX: "auto" }}>
                <table className="w-full" style={{ minWidth: 800 }}>
                  <thead>
                    <tr
                      style={{
                        borderBottom: "1px solid var(--border)",
                        color: "var(--text-secondary)",
                        fontSize: 12,
                        textTransform: "uppercase",
                        letterSpacing: "0.05em",
                      }}
                    >
                      <th style={{ textAlign: "left", padding: "12px 16px", fontWeight: 500 }}>
                        Month
                      </th>
                      <th style={{ textAlign: "right", padding: "12px 16px", fontWeight: 500 }}>
                        Stock Sales
                      </th>
                      <th style={{ textAlign: "right", padding: "12px 16px", fontWeight: 500 }}>
                        Stock Gain
                      </th>
                      <th style={{ textAlign: "center", padding: "12px 16px", fontWeight: 500 }}>
                        Exempt
                      </th>
                      <th style={{ textAlign: "right", padding: "12px 16px", fontWeight: 500 }}>
                        Stock Tax
                      </th>
                      <th style={{ textAlign: "right", padding: "12px 16px", fontWeight: 500 }}>
                        FII Sales
                      </th>
                      <th style={{ textAlign: "right", padding: "12px 16px", fontWeight: 500 }}>
                        FII Gain
                      </th>
                      <th style={{ textAlign: "right", padding: "12px 16px", fontWeight: 500 }}>
                        FII Tax
                      </th>
                      <th style={{ textAlign: "right", padding: "12px 16px", fontWeight: 500 }}>
                        Total DARF
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {nonEmptyMonths.map((entry) => {
                      const stockGain = parseFloat(entry.stocks.total_gain);
                      const fiiGain = parseFloat(entry.fiis.total_gain);
                      const totalTax = parseFloat(entry.total_tax_due);

                      return (
                        <tr
                          key={entry.month}
                          style={{
                            borderBottom: "1px solid var(--border)",
                            transition: "background 0.15s",
                          }}
                          onMouseEnter={(e) =>
                            (e.currentTarget.style.background = "rgba(255,255,255,0.03)")
                          }
                          onMouseLeave={(e) =>
                            (e.currentTarget.style.background = "transparent")
                          }
                        >
                          <td
                            style={{
                              padding: "12px 16px",
                              fontWeight: 500,
                              color: "var(--text-primary)",
                            }}
                          >
                            {MONTH_NAMES[entry.month - 1]}
                          </td>
                          <td
                            style={{
                              padding: "12px 16px",
                              textAlign: "right",
                              color: "var(--text-primary)",
                            }}
                          >
                            {formatBRL(entry.stocks.total_sales)}
                          </td>
                          <td
                            style={{
                              padding: "12px 16px",
                              textAlign: "right",
                              color: stockGain >= 0 ? "#34c759" : "#ff3b30",
                            }}
                          >
                            {formatBRL(entry.stocks.total_gain)}
                          </td>
                          <td style={{ padding: "12px 16px", textAlign: "center" }}>
                            <span
                              style={{
                                display: "inline-block",
                                padding: "2px 10px",
                                borderRadius: 9999,
                                fontSize: 12,
                                fontWeight: 600,
                                background: entry.stocks.exempt
                                  ? "rgba(52, 199, 89, 0.15)"
                                  : "rgba(255, 149, 0, 0.15)",
                                color: entry.stocks.exempt ? "#34c759" : "#ff9500",
                              }}
                            >
                              {entry.stocks.exempt ? "Yes" : "No"}
                            </span>
                          </td>
                          <td
                            style={{
                              padding: "12px 16px",
                              textAlign: "right",
                              color:
                                parseFloat(entry.stocks.tax_due) > 0
                                  ? "#ff3b30"
                                  : "var(--text-primary)",
                            }}
                          >
                            {formatBRL(entry.stocks.tax_due)}
                          </td>
                          <td
                            style={{
                              padding: "12px 16px",
                              textAlign: "right",
                              color: "var(--text-primary)",
                            }}
                          >
                            {formatBRL(entry.fiis.total_sales)}
                          </td>
                          <td
                            style={{
                              padding: "12px 16px",
                              textAlign: "right",
                              color: fiiGain >= 0 ? "#34c759" : "#ff3b30",
                            }}
                          >
                            {formatBRL(entry.fiis.total_gain)}
                          </td>
                          <td
                            style={{
                              padding: "12px 16px",
                              textAlign: "right",
                              color:
                                parseFloat(entry.fiis.tax_due) > 0
                                  ? "#ff3b30"
                                  : "var(--text-primary)",
                            }}
                          >
                            {formatBRL(entry.fiis.tax_due)}
                          </td>
                          <td
                            style={{
                              padding: "12px 16px",
                              textAlign: "right",
                              fontWeight: 600,
                              color: totalTax > 0 ? "#ff3b30" : "var(--text-primary)",
                            }}
                          >
                            {formatBRL(entry.total_tax_due)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
