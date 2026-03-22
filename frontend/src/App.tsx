import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import TopNav from "./components/TopNav";
import AmbientGlows from "./components/AmbientGlows";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import Fundamentals from "./pages/Fundamentals";
import FundamentalsIndex from "./pages/FundamentalsIndex";
import Market from "./pages/Market";
import AssetClassHoldings from "./pages/AssetClassHoldings";
import Invest from "./pages/Invest";
import Login from "./pages/Login";
import { useAuth } from "./contexts/AuthContext";

function ProtectedLayout() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return (
    <>
      <AmbientGlows />
      <TopNav />
      <main style={{ position: "relative", zIndex: 1, maxWidth: 1400, margin: "0 auto", padding: 32 }}>
        <Outlet />
      </main>
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedLayout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/invest" element={<Invest />} />
          <Route path="/portfolio/:assetClassId" element={<AssetClassHoldings />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/fundamentals" element={<FundamentalsIndex />} />
          <Route path="/fundamentals/:symbol" element={<Fundamentals />} />
          <Route path="/market" element={<Market />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
