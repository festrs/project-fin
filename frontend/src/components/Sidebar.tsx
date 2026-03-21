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
    <nav className="fixed left-0 top-0 w-[220px] min-h-screen bg-[var(--glass-sidebar-bg)] border-r border-[var(--glass-border)] p-6 flex flex-col gap-1">
      <Link to="/" className="text-2xl font-bold text-text-primary px-3 mb-6 tracking-[-0.3px]">
        Project <span className="text-primary">Fin</span>
      </Link>
      {links.map((link) => {
        const isActive = location.pathname === link.to;
        return (
          <Link
            key={link.to}
            to={link.to}
            className={`flex items-center gap-2.5 px-3 py-2.5 rounded-[10px] text-base font-medium transition-colors ${
              isActive
                ? "bg-[var(--glass-primary-soft)] text-primary font-semibold"
                : "text-text-tertiary hover:bg-[var(--glass-hover)] hover:text-text-primary"
            }`}
          >
            <link.icon size={18} strokeWidth={1.8} />
            {link.label}
          </Link>
        );
      })}
      <button
        onClick={handleLogout}
        className="flex items-center gap-2.5 px-3 py-2.5 rounded-[10px] text-base font-medium text-text-tertiary hover:bg-[var(--glass-hover)] hover:text-text-primary transition-colors mt-auto"
      >
        <LogOut size={18} strokeWidth={1.8} />
        Logout
      </button>
    </nav>
  );
}
