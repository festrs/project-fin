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
    return <p className="text-gray-500 text-sm">Loading settings...</p>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {saved && (
        <p className="text-green-600 text-sm">Settings saved successfully</p>
      )}

      {/* Quarantine Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Quarantine Settings</h2>
        <div className="space-y-4">
          <div>
            <label htmlFor="threshold" className="block text-sm font-medium text-gray-700 mb-1">
              Threshold
            </label>
            <input
              id="threshold"
              type="number"
              min={1}
              value={threshold}
              onChange={(e) => setThreshold(parseInt(e.target.value, 10) || 0)}
              className="w-full border border-gray-300 rounded px-3 py-2"
            />
          </div>
          <div>
            <label htmlFor="periodDays" className="block text-sm font-medium text-gray-700 mb-1">
              Period (days)
            </label>
            <input
              id="periodDays"
              type="number"
              min={1}
              value={periodDays}
              onChange={(e) => setPeriodDays(parseInt(e.target.value, 10) || 0)}
              className="w-full border border-gray-300 rounded px-3 py-2"
            />
          </div>
          <button
            onClick={handleSaveQuarantine}
            disabled={saving}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Quarantine Settings"}
          </button>
        </div>
      </div>

      {/* Recommendation Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">Recommendation Settings</h2>
        <div className="space-y-4">
          <div>
            <label htmlFor="recCount" className="block text-sm font-medium text-gray-700 mb-1">
              Recommendation Count
            </label>
            <input
              id="recCount"
              type="number"
              min={1}
              value={recCount}
              onChange={(e) => setRecCount(parseInt(e.target.value, 10) || 0)}
              className="w-full border border-gray-300 rounded px-3 py-2"
            />
          </div>
          <button
            onClick={handleSaveRecommendations}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Save Recommendation Settings
          </button>
        </div>
      </div>
    </div>
  );
}
