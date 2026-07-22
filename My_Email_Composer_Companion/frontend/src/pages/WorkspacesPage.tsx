import { useEffect, useState } from "react";
import { useWorkspace } from "../hooks/useWorkspace";
import { api } from "../services/api";
import type { Workspace } from "../types";

export function WorkspacesPage() {
  const { refresh } = useWorkspace();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [color, setColor] = useState("#3d9a8b");
  const [error, setError] = useState("");

  const load = async () => {
    const list = await api.workspaces.list();
    setWorkspaces(list);
  };

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  const create = async () => {
    if (!name.trim()) return;
    try {
      await api.workspaces.create({ name, description, color });
      setName("");
      setDescription("");
      await load();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create failed");
    }
  };

  const remove = async (id: number) => {
    try {
      await api.workspaces.delete(id);
      await load();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  return (
    <div>
      <h1 className="page-title">Workspaces</h1>
      <p className="page-desc">
        Isolate knowledge per customer or project. RAG context stays within the selected workspace.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="grid-2">
        <div className="panel">
          <h3 className="panel-title">Your Workspaces</h3>
          <div className="list">
            {workspaces.map((w) => (
              <div
                key={w.id}
                className="list-item"
                style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}
              >
                <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-start" }}>
                  <span
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: 3,
                      background: w.color,
                      marginTop: 5,
                      flexShrink: 0,
                    }}
                  />
                  <div>
                    <h4>
                      {w.name} {w.is_default && <span className="badge ok">default</span>}
                    </h4>
                    <p>
                      {w.description || "No description"} · {w.document_count} docs ·{" "}
                      {w.email_count} emails
                    </p>
                  </div>
                </div>
                {!w.is_default && (
                  <button className="btn btn-danger" onClick={() => remove(w.id)}>
                    Delete
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <h3 className="panel-title">Create Workspace</h3>
          <input
            className="input"
            placeholder="Customer A / Project X"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ marginBottom: "0.65rem" }}
          />
          <textarea
            className="textarea"
            style={{ minHeight: 100 }}
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <div style={{ marginTop: "0.65rem" }}>
            <label className="field-label">Color</label>
            <input
              type="color"
              value={color}
              onChange={(e) => setColor(e.target.value)}
            />
          </div>
          <button className="btn btn-primary" style={{ marginTop: "0.85rem" }} onClick={create}>
            Create Workspace
          </button>
        </div>
      </div>
    </div>
  );
}
