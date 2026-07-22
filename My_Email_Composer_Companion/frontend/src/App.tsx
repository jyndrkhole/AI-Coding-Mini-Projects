import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Sidebar } from "./components/layout/Sidebar";
import { Topbar } from "./components/layout/Topbar";
import { WorkspaceProvider } from "./hooks/useWorkspace";
import { ChatPage } from "./pages/ChatPage";
import { ComposePage } from "./pages/ComposePage";
import { DashboardPage } from "./pages/DashboardPage";
import { KnowledgePage } from "./pages/KnowledgePage";
import { LogsPage } from "./pages/LogsPage";
import { PromptsPage } from "./pages/PromptsPage";
import { ReplyPage } from "./pages/ReplyPage";
import { SearchPage } from "./pages/SearchPage";
import { SettingsPage } from "./pages/SettingsPage";
import { StylePage } from "./pages/StylePage";
import { WorkspacesPage } from "./pages/WorkspacesPage";

export default function App() {
  return (
    <WorkspaceProvider>
      <BrowserRouter>
        <div className="app-shell">
          <Sidebar />
          <div className="main">
            <Topbar />
            <main className="page">
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/compose" element={<ComposePage />} />
                <Route path="/reply" element={<ReplyPage />} />
                <Route path="/knowledge" element={<KnowledgePage />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/search" element={<SearchPage />} />
                <Route path="/prompts" element={<PromptsPage />} />
                <Route path="/style" element={<StylePage />} />
                <Route path="/workspaces" element={<WorkspacesPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/logs" element={<LogsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>
          </div>
        </div>
      </BrowserRouter>
    </WorkspaceProvider>
  );
}
