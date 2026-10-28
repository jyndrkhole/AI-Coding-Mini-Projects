import { Route, Routes } from "react-router-dom";
import { AppShell } from "./layouts/AppShell";
import { CallbacksPage } from "./pages/Callbacks";
import { OverviewPage } from "./pages/Overview";
import { QualityPage } from "./pages/Quality";
import { ReportPage } from "./pages/Report";
import { RevenuePage } from "./pages/Revenue";
import { SimulationsPage } from "./pages/Simulations";
import { TracePage } from "./pages/Trace";
import { TrendsPage } from "./pages/Trends";
import { VoicePage } from "./pages/Voice";

export function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/trends" element={<TrendsPage />} />
        <Route path="/voice" element={<VoicePage />} />
        <Route path="/revenue" element={<RevenuePage />} />
        <Route path="/callbacks" element={<CallbacksPage />} />
        <Route path="/simulations" element={<SimulationsPage />} />
        <Route path="/trace" element={<TracePage />} />
        <Route path="/report" element={<ReportPage />} />
        <Route path="/quality" element={<QualityPage />} />
      </Routes>
    </AppShell>
  );
}
