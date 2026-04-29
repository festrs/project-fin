import { useLocation, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";
import Icon from "./Icon";

const TABS = [
  { id: "dashboard", label: "Portfolio", path: "/", icon: "dashboard" },
  { id: "fundamentals", label: "Fundamentals", path: "/fundamentals", icon: "chart" },
  { id: "market", label: "Market", path: "/market", icon: "list" },
  { id: "invest", label: "Invest", path: "/invest", icon: "wallet" },
  { id: "tax", label: "Tax", path: "/tax", icon: "chart" },
];

export default function TopNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { theme, toggleTheme } = useTheme();

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
    <header
      style={{
        display: "flex",
        alignItems: "center",
        gap: 24,
        padding: "14px 32px",
        borderBottom: "1px solid var(--line)",
        background: "var(--bg)",
        position: "sticky",
        top: 0,
        zIndex: 100,
      }}
    >
      {/* Logo */}
      <Link
        to="/"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          textDecoration: "none",
          color: "var(--fg)",
        }}
      >
        <div
          style={{
            width: 24,
            height: 24,
            borderRadius: 6,
            background: "var(--fg)",
            color: "var(--bg)",
            display: "grid",
            placeItems: "center",
            fontFamily: "var(--font-display)",
            fontWeight: 700,
            fontSize: 14,
          }}
        >
          F
        </div>
        <span
          style={{
            fontFamily: "var(--font-display)",
            fontWeight: 600,
            fontSize: 16,
            letterSpacing: "-0.01em",
          }}
        >
          Fin
          <span style={{ color: "var(--fg-3)", fontWeight: 400 }}>·folio</span>
        </span>
      </Link>

      {/* Navigation tabs */}
      <nav style={{ display: "flex", gap: 2, marginLeft: 20 }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => navigate(tab.path)}
            style={{
              all: "unset",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 14px",
              borderRadius: "var(--radius)",
              fontSize: 13,
              fontWeight: 500,
              color: isActive(tab.path) ? "var(--fg)" : "var(--fg-3)",
              background: isActive(tab.path) ? "var(--bg-3)" : "transparent",
            }}
          >
            <Icon name={tab.icon} size={15} />
            {tab.label}
          </button>
        ))}
      </nav>

      <div style={{ flex: 1 }} />

      {/* Search bar */}
      <div
        className="responsive-hide"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "6px 12px",
          borderRadius: "var(--radius)",
          background: "var(--bg-3)",
          minWidth: 200,
          color: "var(--fg-3)",
        }}
      >
        <Icon name="search" size={14} />
        <span style={{ fontSize: 12 }}>Search assets…</span>
        <span
          style={{
            marginLeft: "auto",
            fontSize: 10,
            fontFamily: "var(--font-mono)",
            padding: "2px 5px",
            border: "1px solid var(--line-2)",
            borderRadius: 4,
          }}
        >
          ⌘K
        </span>
      </div>

      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        style={{
          all: "unset",
          cursor: "pointer",
          padding: 8,
          borderRadius: "var(--radius)",
          color: "var(--fg-2)",
          display: "inline-flex",
        }}
      >
        <Icon name={theme === "dark" ? "sun" : "moon"} size={16} />
      </button>

      {/* Settings */}
      <button
        onClick={() => navigate("/settings")}
        style={{
          all: "unset",
          cursor: "pointer",
          padding: 8,
          borderRadius: "var(--radius)",
          color: "var(--fg-2)",
          display: "inline-flex",
        }}
      >
        <Icon name="settings" size={16} />
      </button>

      {/* Notifications */}
      <button
        style={{
          all: "unset",
          cursor: "pointer",
          padding: 8,
          borderRadius: "var(--radius)",
          color: "var(--fg-2)",
          display: "inline-flex",
          position: "relative",
        }}
      >
        <Icon name="bell" size={16} />
        <span
          style={{
            position: "absolute",
            top: 6,
            right: 6,
            width: 6,
            height: 6,
            borderRadius: 999,
            background: "var(--down)",
          }}
        />
      </button>

      {/* Avatar */}
      <div
        style={{
          width: 30,
          height: 30,
          borderRadius: 999,
          background: "var(--bg-3)",
          border: "1px solid var(--line)",
          display: "grid",
          placeItems: "center",
          fontSize: 12,
          fontWeight: 600,
          fontFamily: "var(--font-mono)",
          color: "var(--fg-2)",
        }}
      >
        {initials}
      </div>
    </header>
  );
}
