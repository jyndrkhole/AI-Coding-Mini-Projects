import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { PromptTemplate } from "../types";

export function PromptsPage() {
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("custom");
  const [description, setDescription] = useState("");
  const [template, setTemplate] = useState("{{input}}");
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<PromptTemplate | null>(null);

  const refresh = () => api.prompts.list().then(setPrompts);

  useEffect(() => {
    refresh().catch((e) => setError(e.message));
  }, []);

  const create = async () => {
    if (!name.trim() || !template.trim()) return;
    try {
      await api.prompts.create({
        name,
        category,
        description,
        template,
        variables: ["input"],
      });
      setName("");
      setDescription("");
      setTemplate("{{input}}");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create failed");
    }
  };

  const remove = async (id: number) => {
    try {
      await api.prompts.delete(id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  return (
    <div>
      <h1 className="page-title">Prompt Library</h1>
      <p className="page-desc">
        Reusable templates for proposals, RCAs, escalations, release notes, and more.
      </p>
      {error && <div className="error-banner">{error}</div>}

      <div className="grid-2">
        <div className="panel">
          <h3 className="panel-title">Templates</h3>
          <div className="list">
            {prompts.map((p) => (
              <div
                key={p.id}
                className="list-item"
                style={{ cursor: "pointer" }}
                onClick={() => setSelected(p)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
                  <div>
                    <h4>
                      {p.name}{" "}
                      {p.is_builtin && <span className="badge">built-in</span>}
                    </h4>
                    <p>
                      {p.category} · used {p.usage_count}× · {p.description}
                    </p>
                  </div>
                  {!p.is_builtin && (
                    <button
                      className="btn btn-danger"
                      onClick={(e) => {
                        e.stopPropagation();
                        remove(p.id);
                      }}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          {selected && (
            <div className="panel">
              <h3 className="panel-title">Preview · {selected.name}</h3>
              <pre className="log-detail mono">{selected.template}</pre>
            </div>
          )}
          <div className="panel">
            <h3 className="panel-title">Create Custom Prompt</h3>
            <input
              className="input"
              placeholder="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={{ marginBottom: "0.65rem" }}
            />
            <input
              className="input"
              placeholder="Category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              style={{ marginBottom: "0.65rem" }}
            />
            <input
              className="input"
              placeholder="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              style={{ marginBottom: "0.65rem" }}
            />
            <textarea
              className="textarea"
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              placeholder="Use {{input}} as the placeholder for user notes"
            />
            <button className="btn btn-primary" style={{ marginTop: "0.75rem" }} onClick={create}>
              Create Prompt
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
