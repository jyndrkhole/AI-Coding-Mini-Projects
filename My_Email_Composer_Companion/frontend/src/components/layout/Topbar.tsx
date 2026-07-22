import { useWorkspace } from "../../hooks/useWorkspace";

export function Topbar({ title }: { title?: string }) {
  const { workspaces, current, setCurrentId } = useWorkspace();

  return (
    <header className="topbar">
      <div>
        {title ? (
          <div style={{ fontWeight: 500, color: "var(--text-muted)", fontSize: "0.85rem" }}>
            {title}
          </div>
        ) : null}
      </div>
      <div className="btn-row">
        <label className="field-label" style={{ margin: 0 }}>
          Workspace
        </label>
        <select
          className="select workspace-select"
          value={current?.id ?? ""}
          onChange={(e) => setCurrentId(Number(e.target.value))}
        >
          {workspaces.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
      </div>
    </header>
  );
}
