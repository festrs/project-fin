import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Settings from "../../pages/Settings";

const mockUpdateConfig = vi.fn();

vi.mock("../../hooks/useQuarantine", () => ({
  useQuarantine: () => ({
    config: { id: "1", user_id: "u1", threshold: 3, period_days: 90 },
    statuses: [],
    loading: false,
    error: null,
    updateConfig: mockUpdateConfig,
    refresh: vi.fn(),
  }),
}));

describe("Settings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("renders settings form with current values", () => {
    render(<Settings />);

    expect(screen.getByText("Quarantine Settings")).toBeInTheDocument();
    expect(screen.getByText("Recommendation Settings")).toBeInTheDocument();

    const thresholdInput = screen.getByLabelText("Threshold") as HTMLInputElement;
    expect(thresholdInput.value).toBe("3");

    const periodInput = screen.getByLabelText("Period (days)") as HTMLInputElement;
    expect(periodInput.value).toBe("90");
  });

  it("save button triggers API call", async () => {
    mockUpdateConfig.mockResolvedValue({
      id: "1",
      user_id: "u1",
      threshold: 3,
      period_days: 90,
    });

    render(<Settings />);

    const saveButton = screen.getByText("Save Quarantine Settings");
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockUpdateConfig).toHaveBeenCalledWith(3, 90);
    });
  });
});
