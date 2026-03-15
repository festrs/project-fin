import { useState, useEffect } from "react";
import { useQuarantine } from "../hooks/useQuarantine";

export default function Settings() {
  const { config, loading, updateConfig } = useQuarantine();

  const [threshold, setThreshold] = useState(2);
  const [periodDays, setPeriodDays] = useState(180);
  const [recCount, setRecCount] = useState(() => {
    const saved = localStorage.getItem("recommendationCount");
    return saved ? parseInt(saved, 10) : 2;
  });
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

  const handleSaveRecommendations = () => {
    localStorage.setItem("recommendationCount", String(recCount));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (loading) {
    return <p className="text-text-muted text-base">Loading settings...</p>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">Settings</h1>

      {saved && (
        <p className="text-positive text-base">Settings saved successfully</p>
      )}

      {/* Quarantine Settings */}
      <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
        <h2 className="text-lg font-semibold text-text-primary tracking-[-0.3px] mb-4">Quarantine Settings</h2>
        <div className="space-y-4">
          <div>
            <label htmlFor="threshold" className="block text-base font-medium text-text-secondary mb-1">
              Threshold
            </label>
            <input
              id="threshold"
              type="number"
              min={1}
              value={threshold}
              onChange={(e) => setThreshold(parseInt(e.target.value, 10) || 0)}
              className="w-full bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            />
          </div>
          <div>
            <label htmlFor="periodDays" className="block text-base font-medium text-text-secondary mb-1">
              Period (days)
            </label>
            <input
              id="periodDays"
              type="number"
              min={1}
              value={periodDays}
              onChange={(e) => setPeriodDays(parseInt(e.target.value, 10) || 0)}
              className="w-full bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            />
          </div>
          <button
            onClick={handleSaveQuarantine}
            disabled={saving}
            className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Quarantine Settings"}
          </button>
        </div>
      </div>

      {/* Recommendation Settings */}
      <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
        <h2 className="text-lg font-semibold text-text-primary tracking-[-0.3px] mb-4">Recommendation Settings</h2>
        <div className="space-y-4">
          <div>
            <label htmlFor="recCount" className="block text-base font-medium text-text-secondary mb-1">
              Recommendation Count
            </label>
            <input
              id="recCount"
              type="number"
              min={1}
              value={recCount}
              onChange={(e) => setRecCount(parseInt(e.target.value, 10) || 0)}
              className="w-full bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            />
          </div>
          <button
            onClick={handleSaveRecommendations}
            className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover"
          >
            Save Recommendation Settings
          </button>
        </div>
      </div>
    </div>
  );
}
