import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App", () => {
  it("renders navbar with Project Fin", () => {
    render(<App />);
    expect(screen.getByText("Project Fin")).toBeInTheDocument();
  });
});
