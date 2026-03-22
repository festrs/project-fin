import { render, screen } from "@testing-library/react";
import App from "./App";
import { AuthProvider } from "./contexts/AuthContext";

describe("App", () => {
  it("renders login page when not authenticated", () => {
    render(
      <AuthProvider>
        <App />
      </AuthProvider>
    );
    expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("••••••••")).toBeInTheDocument();
  });
});
