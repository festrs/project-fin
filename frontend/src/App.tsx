import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Portfolio from "./pages/Portfolio";
import Settings from "./pages/Settings";
import Market from "./pages/Market";
import Fundamentals from "./pages/Fundamentals";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-bg-page flex">
        <Sidebar />
        <main className="ml-[220px] w-[calc(100%-220px)] px-10 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/market" element={<Market />} />
            <Route path="/fundamentals/:symbol" element={<Fundamentals />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
