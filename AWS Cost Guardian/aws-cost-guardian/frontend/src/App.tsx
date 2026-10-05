import { Route, Routes } from "react-router-dom";
import { AppShell } from "./layouts/AppShell";
import { CostExplorerPage } from "./pages/CostExplorerPage";
import { DashboardPage } from "./pages/DashboardPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/costs" element={<CostExplorerPage />} />
      </Route>
    </Routes>
  );
}
