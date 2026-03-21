import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const links = [
  { to: "/", label: "Dashboard", icon: "dashboard" },
  { to: "/invest", label: "Where to Invest", icon: "query_stats" },
  { to: "/settings", label: "Settings", icon: "settings" },
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
    <aside
      className="fixed left-0 top-0 h-full w-64 border-r flex flex-col py-6 px-4 z-50"
      style={{
        background: "var(--glass-bg)",
        backdropFilter: "blur(var(--glass-blur))",
        borderColor: "var(--glass-border)",
      }}
    >
      <div className="mb-10 px-2">
        <h1 className="text-2xl font-extrabold text-on-surface uppercase tracking-tighter">
          Project Fin
        </h1>
        <p className="text-xs text-text-muted tracking-widest uppercase mt-1 font-body">
          Wealth Management
        </p>
      </div>

      <nav className="flex-1 space-y-1">
        {links.map((link) => {
          const isActive = location.pathname === link.to;
          return (
            <Link
              key={link.to}
              to={link.to}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
                isActive
                  ? "text-primary border-r-2 border-primary"
                  : "text-text-muted hover:text-on-surface"
              }`}
              style={isActive ? { background: "var(--glass-primary-soft)" } : { }}
            >
              <span className="material-symbols-outlined text-[20px]">{link.icon}</span>
              <span className="text-sm font-medium font-body">{link.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto pt-4" style={{ borderTop: "1px solid var(--glass-border)" }}>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-4 py-3 rounded-lg text-text-muted hover:text-on-surface transition-all duration-200 w-full"
        >
          <span className="material-symbols-outlined text-[20px]">logout</span>
          <span className="text-sm font-medium font-body">Logout</span>
        </button>
      </div>
    </aside>
  );
}
