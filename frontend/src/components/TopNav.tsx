import { useLocation, useNavigate, Link } from "react-router-dom";
import { Settings, Bell } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";

const TABS = [
  { label: "Portfolio", path: "/" },
  { label: "Fundamentals", path: "/fundamentals" },
  { label: "Market", path: "/market" },
  { label: "Invest", path: "/invest" },
];

export default function TopNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : "??";

  const isActive = (path: string) => {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  };

  return (
    <nav
      style={{
        position: "sticky",
        top: 0,
        zIndex: 100,
        background: "rgba(10, 10, 10, 0.85)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderBottom: "1px solid var(--border)",
        padding: "0 32px",
      }}
    >
      <div
        style={{
          maxWidth: 1400,
          margin: "0 auto",
          display: "flex",
          alignItems: "center",
          height: 52,
          gap: 32,
        }}
      >
        {/* Logo */}
        <Link
          to="/"
          style={{
            fontSize: 18,
            fontWeight: 600,
            letterSpacing: "-0.02em",
            color: "var(--text-primary)",
            textDecoration: "none",
            whiteSpace: "nowrap",
          }}
        >
          Fin
        </Link>

        {/* Segmented Tabs */}
        <div
          style={{
            display: "flex",
            gap: 4,
            background: "rgba(255, 255, 255, 0.06)",
            borderRadius: "var(--radius-pill)",
            padding: 3,
          }}
        >
          {TABS.map((tab) => (
            <button
              key={tab.path}
              onClick={() => navigate(tab.path)}
              style={{
                padding: "6px 18px",
                borderRadius: "var(--radius-pill)",
                fontSize: 13,
                fontWeight: 500,
                color: isActive(tab.path)
                  ? "var(--text-primary)"
                  : "var(--text-secondary)",
                background: isActive(tab.path)
                  ? "rgba(255, 255, 255, 0.12)"
                  : "transparent",
                border: "none",
                cursor: "pointer",
                transition: "all 0.2s",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Right Section */}
        <div
          style={{
            marginLeft: "auto",
            display: "flex",
            alignItems: "center",
            gap: 16,
          }}
        >
          <button
            onClick={() => navigate("/settings")}
            style={{
              width: 44,
              height: 44,
              borderRadius: "50%",
              background: "rgba(255, 255, 255, 0.06)",
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-secondary)",
              transition: "all 0.2s",
            }}
          >
            <Settings size={20} />
          </button>
          <button
            style={{
              width: 44,
              height: 44,
              borderRadius: "50%",
              background: "rgba(255, 255, 255, 0.06)",
              border: "none",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--text-secondary)",
              transition: "all 0.2s",
            }}
          >
            <Bell size={20} />
          </button>
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              background: "var(--blue)",
              fontSize: 11,
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "white",
            }}
          >
            {initials}
          </div>
        </div>
      </div>
    </nav>
  );
}
