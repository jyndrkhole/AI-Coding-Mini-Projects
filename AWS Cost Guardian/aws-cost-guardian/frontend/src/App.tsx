import { Route, Routes } from "react-router-dom";
import { AppShell } from "./layouts/AppShell";
import { AdvisorPage } from "./pages/AdvisorPage";
import { CostExplorerPage } from "./pages/CostExplorerPage";
import { DashboardPage } from "./pages/DashboardPage";
import { RecommendationDetailPage } from "./pages/RecommendationDetailPage";
import { ReportPage } from "./pages/ReportPage";
import { ResourceDetailPage } from "./pages/ResourceDetailPage";
import { ResourcesPage } from "./pages/ResourcesPage";
import { SimulationPage } from "./pages/SimulationPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/costs" element={<CostExplorerPage />} />
        <Route path="/resources" element={<ResourcesPage />} />
        <Route path="/resources/*" element={<ResourceDetailPage />} />
        <Route path="/recommendations/:recommendationId" element={<RecommendationDetailPage />} />
        <Route path="/advisor" element={<AdvisorPage />} />
        <Route path="/simulate" element={<SimulationPage />} />
        <Route path="/report" element={<ReportPage />} />
      </Route>
    </Routes>
  );
}
