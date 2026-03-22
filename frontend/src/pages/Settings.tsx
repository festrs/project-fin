import { useState, useEffect } from "react";
import { useQuarantine } from "../hooks/useQuarantine";

export default function Settings() {
  const { config, loading, updateConfig } = useQuarantine();

  const [threshold, setThreshold] = useState(2);
  const [periodDays, setPeriodDays] = useState(180);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (config) {
      setThreshold(config.threshold);
      setPeriodDays(config.period_days);
    }
  }, [config]);

  const handleSaveQuarantine = async () => {
    try {
      setSaving(true);
      await updateConfig(threshold, periodDays);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // error handled by hook
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>Loading settings...</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div>
        <p className="text-label">Configuration</p>
        <h1 style={{ fontSize: 32, fontWeight: 700, letterSpacing: "-0.02em", color: "var(--text-primary)", margin: 0 }}>
          Settings
        </h1>
      </div>

      {saved && (
        <p style={{ color: "var(--green)", fontSize: 14 }}>Settings saved successfully</p>
      )}

      {/* Quarantine Settings */}
      <div className="card">
        <h2 style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)", marginBottom: 16 }}>
          Quarantine Settings
        </h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <label htmlFor="threshold" style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 4 }}>
              Threshold
            </label>
            <input
              id="threshold"
              type="number"
              min={1}
              value={threshold}
              onChange={(e) => setThreshold(parseInt(e.target.value, 10) || 0)}
              className="input-field"
            />
          </div>
          <div>
            <label htmlFor="periodDays" style={{ display: "block", fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 4 }}>
              Period (days)
            </label>
            <input
              id="periodDays"
              type="number"
              min={1}
              value={periodDays}
              onChange={(e) => setPeriodDays(parseInt(e.target.value, 10) || 0)}
              className="input-field"
            />
          </div>
          <button
            onClick={handleSaveQuarantine}
            disabled={saving}
            className="btn-primary"
          >
            {saving ? "Saving..." : "Save Quarantine Settings"}
          </button>
        </div>
      </div>
    </div>
  );
}
