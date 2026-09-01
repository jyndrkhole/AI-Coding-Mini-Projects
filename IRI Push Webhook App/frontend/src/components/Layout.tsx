import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { PortalConfig } from "../types";
import { ThemeToggle } from "./ThemeToggle";

function copyText(value: string) {
  void navigator.clipboard.writeText(value);
}

export function Layout() {
  const [online, setOnline] = useState(false);
  const [config, setConfig] = useState<PortalConfig | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [health, portalConfig] = await Promise.all([api.getHealth(), api.getConfig()]);
        setOnline(health.status === "ok");
        setConfig(portalConfig);
      } catch {
        setOnline(false);
      }
    };
    void load();
    const timer = setInterval(() => void load(), 15000);
    return () => clearInterval(timer);
  }, []);

  const webhookUrl = config?.webhookUrl ?? "http://localhost:3000/webhooks/iri";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <p className="brand-kicker">IRI Push Notification</p>
          <h1>Webhook Test Portal</h1>
        </div>
        <nav className="nav">
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/events">Events</NavLink>
          <NavLink to="/send-test">Send Test Notification</NavLink>
          <NavLink to="/settings">Settings</NavLink>
          <NavLink to="/api-docs">API Documentation</NavLink>
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <div>
            <h2>Webhook Test Portal</h2>
            <p className="topbar-sub">IRI Push Notification receiver</p>
          </div>
          <div className="status-row">
            <span className={`dot ${online ? "online" : "offline"}`} />
            <strong>{online ? "Webhook Receiver Online" : "Webhook Receiver Offline"}</strong>
            <div className="webhook-url">
              <span>POST {webhookUrl}</span>
              <button className="btn secondary" type="button" onClick={() => copyText(webhookUrl)}>
                Copy URL
              </button>
            </div>
            <ThemeToggle />
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
