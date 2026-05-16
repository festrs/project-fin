import { NavLink } from "react-router-dom";
import Icon from "./Icon";

const TABS = [
  { label: "Portfolio", path: "/", icon: "dashboard" as const, end: true },
  { label: "Fundamentals", path: "/fundamentals", icon: "chart" as const, end: false },
  { label: "Market", path: "/market", icon: "list" as const, end: false },
  { label: "Invest", path: "/invest", icon: "wallet" as const, end: false },
  { label: "Settings", path: "/settings", icon: "settings" as const, end: false },
];

export default function MobileNav() {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-100 md:hidden h-16 flex justify-around items-center"
      style={{
        background: "var(--bg)",
        borderTop: "1px solid var(--line)",
      }}
    >
      {TABS.map((tab) => (
        <NavLink
          key={tab.path}
          to={tab.path}
          end={tab.end}
          className={({ isActive }) =>
            `flex flex-col items-center gap-0.5 py-1 px-2 ${
              isActive ? "text-[var(--fg)]" : "text-[var(--fg-3)]"
            }`
          }
        >
          <Icon name={tab.icon} size={20} />
          <span className="text-[10px] font-medium">{tab.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
