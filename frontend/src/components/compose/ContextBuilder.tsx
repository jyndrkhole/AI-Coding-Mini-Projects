import { CONTEXT_SOURCES } from "../../types";

interface Props {
  selected: string[];
  onChange: (next: string[]) => void;
}

export function ContextBuilder({ selected, onChange }: Props) {
  const toggle = (id: string) => {
    if (selected.includes(id)) onChange(selected.filter((s) => s !== id));
    else onChange([...selected, id]);
  };

  return (
    <div>
      <label className="field-label">Context Sources</label>
      <div className="chip-group">
        {CONTEXT_SOURCES.map((src) => (
          <button
            key={src.id}
            type="button"
            className={`chip${selected.includes(src.id) ? " active" : ""}`}
            onClick={() => toggle(src.id)}
          >
            {selected.includes(src.id) ? "✓ " : ""}
            {src.label}
          </button>
        ))}
      </div>
    </div>
  );
}
