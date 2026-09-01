import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { DashboardPage } from "./pages/Dashboard";
import { EventsPage } from "./pages/Events";
import { EventDetailPage } from "./pages/EventDetail";
import { SendTestPage } from "./pages/SendTest";
import { SettingsPage } from "./pages/Settings";
import { ApiDocsPage } from "./pages/ApiDocs";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/events" element={<EventsPage />} />
        <Route path="/events/:id" element={<EventDetailPage />} />
        <Route path="/send-test" element={<SendTestPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/api-docs" element={<ApiDocsPage />} />
      </Route>
    </Routes>
  );
}
