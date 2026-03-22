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
    return <p className="text-text-muted text-base">Loading settings...</p>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-display" style={{ fontSize: '2rem' }}>Settings</h1>

      {saved && (
        <p className="text-secondary text-base">Settings saved successfully</p>
      )}

      {/* Quarantine Settings */}
      <div className="card">
        <h2 className="text-heading mb-4">Quarantine Settings</h2>
        <div className="space-y-4">
          <div>
            <label htmlFor="threshold" className="block text-base font-medium text-on-surface-variant mb-1">
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
            <label htmlFor="periodDays" className="block text-base font-medium text-on-surface-variant mb-1">
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
