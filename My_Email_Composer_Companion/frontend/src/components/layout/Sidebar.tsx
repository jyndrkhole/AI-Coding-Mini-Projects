import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  PenLine,
  Reply,
  Library,
  MessageSquare,
  Search,
  ScrollText,
  Folders,
  Settings,
  FileText,
  Feather,
} from "lucide-react";

const NAV = [
  {
    label: "Work",
    items: [
      { to: "/", icon: LayoutDashboard, label: "Dashboard" },
      { to: "/compose", icon: PenLine, label: "Compose Email" },
      { to: "/reply", icon: Reply, label: "Reply to Email" },
      { to: "/chat", icon: MessageSquare, label: "Chat" },
    ],
  },
  {
    label: "Knowledge",
    items: [
      { to: "/knowledge", icon: Library, label: "Knowledge Base" },
      { to: "/search", icon: Search, label: "Search" },
      { to: "/prompts", icon: ScrollText, label: "Prompt Library" },
      { to: "/style", icon: Feather, label: "Style Memory" },
    ],
  },
  {
    label: "System",
    items: [
      { to: "/workspaces", icon: Folders, label: "Workspaces" },
      { to: "/settings", icon: Settings, label: "AI Settings" },
      { to: "/logs", icon: FileText, label: "Logs" },
    ],
  },
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">MailMind</div>
        <div className="brand-sub">Local Email Intelligence</div>
      </div>

      {NAV.map((section) => (
        <div key={section.label} className="nav-section">
          <div className="nav-label">{section.label}</div>
          {section.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
            >
              <item.icon size={17} strokeWidth={1.8} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      ))}
    </aside>
  );
}
