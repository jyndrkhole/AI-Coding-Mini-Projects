import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { PortalConfig, PortalSession } from "../types";
import { APP_NAME } from "../constants";
import { advertisedWebhookUrl } from "../utils/webhookUrl";
import { ThemeToggle } from "./ThemeToggle";

function copyText(value: string) {
  void navigator.clipboard.writeText(value);
}

export function Layout({
  portalSession,
  onLoggedOut
}: {
  portalSession: PortalSession;
  onLoggedOut: (session: PortalSession) => void;
}) {
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

  const webhookUrl = advertisedWebhookUrl(config);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <p className="brand-kicker">Application Status</p>
          <h1>{APP_NAME}</h1>
        </div>
        <nav className="nav">
          <NavLink to="/" end>
            Dashboard
          </NavLink>
          <NavLink to="/events">Events</NavLink>
          <NavLink to="/reconcile">Reconcile</NavLink>
          <NavLink to="/send-test">Send Test Notification</NavLink>
          <NavLink to="/settings">Settings</NavLink>
          <NavLink to="/api-docs">API Documentation</NavLink>
        </nav>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="topbar-title">
            <h2>{APP_NAME}</h2>
            <p className="topbar-sub">Test webhook receiver</p>
          </div>
          <div className="status-row">
            <span className={`dot ${online ? "online" : "offline"}`} />
            <strong>{online ? "Webhook Receiver Online" : "Webhook Receiver Offline"}</strong>
            <div className="webhook-url">
              <span title={webhookUrl}>POST {webhookUrl}</span>
              <button className="btn secondary" type="button" onClick={() => copyText(webhookUrl)}>
                Copy URL
              </button>
            </div>
            <ThemeToggle />
            {portalSession.enabled ? (
              <button
                className="btn secondary"
                type="button"
                onClick={() => {
                  void api.logout().then(onLoggedOut);
                }}
              >
                Sign out
              </button>
            ) : null}
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
