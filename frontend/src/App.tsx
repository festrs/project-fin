import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation } from "react-router-dom";
import TopNav from "./components/TopNav";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import Fundamentals from "./pages/Fundamentals";
import FundamentalsIndex from "./pages/FundamentalsIndex";
import Market from "./pages/Market";
import AssetClassHoldings from "./pages/AssetClassHoldings";
import Invest from "./pages/Invest";
import AssetDetail from "./pages/AssetDetail";
import Login from "./pages/Login";
import Tax from "./pages/Tax";
import { useAuth } from "./contexts/AuthContext";
import { ThemeProvider } from "./contexts/ThemeContext";

const PAGE_TITLES: Record<string, { breadcrumb: string; heading: string }> = {
  "/": { breadcrumb: "Dashboard", heading: "Portfolio overview" },
  "/fundamentals": { breadcrumb: "Fundamentals", heading: "Fundamentals scores" },
  "/market": { breadcrumb: "Market", heading: "Market overview" },
  "/invest": { breadcrumb: "Invest", heading: "Investment calculator" },
  "/tax": { breadcrumb: "Tax", heading: "Tax report" },
  "/settings": { breadcrumb: "Settings", heading: "Settings" },
};

function ProtectedLayout() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  const pageInfo = PAGE_TITLES[location.pathname] || { breadcrumb: "", heading: "" };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <TopNav />
      <main
        style={{
          flex: 1,
          maxWidth: 1360,
          margin: "0 auto",
          width: "100%",
          padding: "28px 32px 80px",
        }}
      >
        {pageInfo.heading && (
          <div style={{ marginBottom: 28 }}>
            <div
              style={{
                fontSize: 12,
                color: "var(--fg-3)",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}
            >
              {pageInfo.breadcrumb}
            </div>
            <h1
              style={{
                margin: "4px 0 0",
                fontFamily: "var(--font-display)",
                fontSize: 28,
                fontWeight: 600,
                letterSpacing: "-0.02em",
                color: "var(--fg)",
              }}
            >
              {pageInfo.heading}
            </h1>
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/invest" element={<Invest />} />
            <Route path="/portfolio/:assetClassId" element={<AssetClassHoldings />} />
            <Route path="/portfolio/:assetClassId/:symbol" element={<AssetDetail />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/fundamentals" element={<FundamentalsIndex />} />
            <Route path="/fundamentals/:symbol" element={<Fundamentals />} />
            <Route path="/market" element={<Market />} />
            <Route path="/tax" element={<Tax />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
