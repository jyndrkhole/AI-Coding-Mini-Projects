import { useMemo, useState } from "react";

function highlightJson(value: string): string {
  return value.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (match) => {
      let cls = "json-number";
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? "json-key" : "json-string";
      } else if (/true|false/.test(match)) {
        cls = "json-boolean";
      } else if (/null/.test(match)) {
        cls = "json-null";
      }
      return `<span class="${cls}">${match}</span>`;
    }
  );
}

export function JsonViewer({ value, label = "JSON" }: { value: unknown; label?: string }) {
  const [expanded, setExpanded] = useState(true);
  const pretty = useMemo(() => JSON.stringify(value, null, 2), [value]);
  const html = useMemo(() => highlightJson(pretty.replace(/</g, "&lt;")), [pretty]);

  return (
    <div className="json-viewer">
      <div className="json-toolbar">
        <span>{label}</span>
        <div className="inline">
          <button className="btn secondary" type="button" onClick={() => setExpanded((open) => !open)}>
            {expanded ? "Collapse" : "Expand"}
          </button>
          <button className="btn secondary" type="button" onClick={() => void navigator.clipboard.writeText(pretty)}>
            Copy JSON
          </button>
        </div>
      </div>
      {expanded ? <pre className="json-body" dangerouslySetInnerHTML={{ __html: html }} /> : null}
    </div>
  );
}
