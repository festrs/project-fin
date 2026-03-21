import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import Fundamentals from "./pages/Fundamentals";
import AssetClassHoldings from "./pages/AssetClassHoldings";
import Invest from "./pages/Invest";
import Login from "./pages/Login";
import { useAuth } from "./contexts/AuthContext";

function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return (
    <div className="min-h-screen bg-surface flex">
      <Sidebar />
      <main className="ml-[220px] w-[calc(100%-220px)] px-10 py-8">
        <Outlet />
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/invest" element={<Invest />} />
          <Route path="/portfolio/:assetClassId" element={<AssetClassHoldings />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/fundamentals/:symbol" element={<Fundamentals />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
