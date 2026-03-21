import { Link, useLocation, useNavigate } from "react-router-dom";
import { LayoutGrid, TrendingUp, Settings, LogOut } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutGrid },
  { to: "/invest", label: "Where to Invest", icon: TrendingUp },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout } = useAuth();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <nav className="fixed left-0 top-0 w-[220px] min-h-screen bg-surface-low p-6 flex flex-col gap-1" style={{ backdropFilter: `blur(var(--glass-blur))` }}>
      <Link to="/" className="text-2xl font-bold text-on-surface px-3 mb-6 tracking-[-0.3px]">
        Project <span className="text-primary-container">Fin</span>
      </Link>
      {links.map((link) => {
        const isActive = location.pathname === link.to;
        return (
          <Link
            key={link.to}
            to={link.to}
            className={`flex items-center gap-2.5 px-3 py-2.5 rounded-DEFAULT text-base font-medium transition-colors ${
              isActive
                ? "bg-primary-fixed/10 text-primary font-semibold"
                : "text-on-surface-variant hover:bg-[var(--glass-hover)] hover:text-on-surface"
            }`}
          >
            <link.icon size={18} strokeWidth={1.8} />
            {link.label}
          </Link>
        );
      })}
      <button
        onClick={handleLogout}
        className="flex items-center gap-2.5 px-3 py-2.5 rounded-DEFAULT text-base font-medium text-on-surface-variant hover:bg-[var(--glass-hover)] hover:text-on-surface transition-colors mt-auto"
      >
        <LogOut size={18} strokeWidth={1.8} />
        Logout
      </button>
    </nav>
  );
}
