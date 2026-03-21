import { BrowserRouter, Routes, Route, Navigate, Outlet, useLocation } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import TopAppBar from "./components/TopAppBar";
import Dashboard from "./pages/Dashboard";
import Settings from "./pages/Settings";
import Fundamentals from "./pages/Fundamentals";
import AssetClassHoldings from "./pages/AssetClassHoldings";
import Invest from "./pages/Invest";
import Login from "./pages/Login";
import { useAuth } from "./contexts/AuthContext";

const ROUTE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/invest": "Where to Invest",
  "/settings": "Settings",
};

function getTitle(pathname: string): string {
  if (ROUTE_TITLES[pathname]) return ROUTE_TITLES[pathname];

  const portfolioMatch = pathname.match(/^\/portfolio\/(.+)$/);
  if (portfolioMatch) return "Portfolio Holdings";

  const fundamentalsMatch = pathname.match(/^\/fundamentals\/(.+)$/);
  if (fundamentalsMatch) return `Fundamentals — ${fundamentalsMatch[1]}`;

  return "Project Fin";
}

function ProtectedLayout() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  const title = getTitle(location.pathname);

  return (
    <div className="min-h-screen bg-surface flex">
      <Sidebar />
      <TopAppBar title={title} />
      <main className="ml-64 w-[calc(100%-16rem)] pt-24 pb-12 px-8">
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
        <Route element={<ProtectedLayout />}>
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
