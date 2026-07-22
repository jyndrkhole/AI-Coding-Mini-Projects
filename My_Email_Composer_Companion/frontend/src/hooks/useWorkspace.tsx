import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../services/api";
import type { Workspace } from "../types";

interface WorkspaceContextValue {
  workspaces: Workspace[];
  current: Workspace | null;
  setCurrentId: (id: number) => void;
  refresh: () => Promise<void>;
  loading: boolean;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentId, setCurrentId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    const list = await api.workspaces.list();
    setWorkspaces(list);
    setCurrentId((prev) => {
      if (prev && list.some((w) => w.id === prev)) return prev;
      const stored = localStorage.getItem("workspace_id");
      if (stored && list.some((w) => w.id === Number(stored))) return Number(stored);
      return list.find((w) => w.is_default)?.id ?? list[0]?.id ?? null;
    });
  };

  useEffect(() => {
    refresh()
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (currentId != null) localStorage.setItem("workspace_id", String(currentId));
  }, [currentId]);

  const current = workspaces.find((w) => w.id === currentId) ?? null;

  return (
    <WorkspaceContext.Provider
      value={{
        workspaces,
        current,
        setCurrentId: (id) => setCurrentId(id),
        refresh,
        loading,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within WorkspaceProvider");
  return ctx;
}
