import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { DashboardPage } from "./pages/Dashboard";
import { EventsPage } from "./pages/Events";
import { ReconcilePage } from "./pages/Reconcile";
import { EventDetailPage } from "./pages/EventDetail";
import { SendTestPage } from "./pages/SendTest";
import { SettingsPage } from "./pages/Settings";
import { ApiDocsPage } from "./pages/ApiDocs";
import { LoginPage } from "./pages/Login";
import { api, ApiError, onPortalAuthLost } from "./services/api";
import type { PortalSession } from "./types";

const loggedOutSession: PortalSession = { enabled: true, authenticated: false, username: null };

export default function App() {
  const [session, setSession] = useState<PortalSession | null>(null);

  useEffect(() => {
    void api
      .getPortalSession()
      .then(setSession)
      .catch(async (error) => {
        if (error instanceof ApiError && error.status === 401) {
          setSession(loggedOutSession);
          return;
        }
        try {
          await api.getConfig();
          setSession({ enabled: false, authenticated: true, username: null });
        } catch (configError) {
          if (configError instanceof ApiError && configError.status === 401) {
            setSession(loggedOutSession);
            return;
          }
          setSession({ enabled: false, authenticated: true, username: null });
        }
      });
  }, []);

  useEffect(() => {
    return onPortalAuthLost(() => {
      setSession(loggedOutSession);
    });
  }, []);

  useEffect(() => {
    if (!session?.enabled || !session.authenticated) {
      return;
    }
    const timer = window.setInterval(() => {
      void api
        .getPortalSession()
        .then((next) => {
          if (next.enabled && !next.authenticated) {
            setSession(loggedOutSession);
          }
        })
        .catch(() => {
          /* ignore transient errors while polling session */
        });
    }, 60_000);
    return () => window.clearInterval(timer);
  }, [session?.enabled, session?.authenticated]);

  if (!session) {
    return <div className="empty">Loading…</div>;
  }

  if (session.enabled && !session.authenticated) {
    return <LoginPage onLoggedIn={setSession} />;
  }

  return (
    <Routes>
      <Route element={<Layout portalSession={session} onLoggedOut={setSession} />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/events" element={<EventsPage />} />
        <Route path="/reconcile" element={<ReconcilePage />} />
        <Route path="/events/:id" element={<EventDetailPage />} />
        <Route path="/send-test" element={<SendTestPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/api-docs" element={<ApiDocsPage />} />
      </Route>
    </Routes>
  );
}
