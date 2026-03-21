import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { ThemeProvider, useTheme } from "../../contexts/ThemeContext";

function ThemeTester() {
  const { theme, setTheme } = useTheme();
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button onClick={() => setTheme("dark")}>Go Dark</button>
      <button onClick={() => setTheme("light")}>Go Light</button>
    </div>
  );
}

describe("ThemeContext", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("defaults to light theme", () => {
    render(
      <ThemeProvider>
        <ThemeTester />
      </ThemeProvider>
    );
    expect(screen.getByTestId("theme").textContent).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("switches to dark theme", () => {
    render(
      <ThemeProvider>
        <ThemeTester />
      </ThemeProvider>
    );
    fireEvent.click(screen.getByText("Go Dark"));
    expect(screen.getByTestId("theme").textContent).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(localStorage.getItem("theme")).toBe("dark");
  });

  it("persists theme from localStorage", () => {
    localStorage.setItem("theme", "dark");
    render(
      <ThemeProvider>
        <ThemeTester />
      </ThemeProvider>
    );
    expect(screen.getByTestId("theme").textContent).toBe("dark");
  });

  it("switches back to light", () => {
    localStorage.setItem("theme", "dark");
    render(
      <ThemeProvider>
        <ThemeTester />
      </ThemeProvider>
    );
    fireEvent.click(screen.getByText("Go Light"));
    expect(screen.getByTestId("theme").textContent).toBe("light");
    expect(localStorage.getItem("theme")).toBe("light");
  });
});
