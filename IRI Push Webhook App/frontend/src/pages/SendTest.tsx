import { useEffect, useMemo, useState } from "react";
import { JsonViewer } from "../components/JsonViewer";
import { api } from "../services/api";
import type { CatalogEvent, PortalConfig } from "../types";

export function SendTestPage() {
  const [catalog, setCatalog] = useState<CatalogEvent[]>([]);
  const [config, setConfig] = useState<PortalConfig | null>(null);
  const [eventType, setEventType] = useState("");
  const [policyNumber, setPolicyNumber] = useState("");
  const [payloadText, setPayloadText] = useState("{}");
  const [apiKey, setApiKey] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [result, setResult] = useState<unknown>(null);

  const selected = catalog.find((item) => item.eventType === eventType);

  useEffect(() => {
    void Promise.all([api.getCatalog(), api.getConfig()]).then(([catalogResult, portalConfig]) => {
      setCatalog(catalogResult.events);
      setConfig(portalConfig);
      const first = catalogResult.events[0];
      if (first) {
        setEventType(first.eventType);
        setPayloadText(JSON.stringify(first.samplePayload, null, 2));
        setPolicyNumber(String(first.samplePayload.policyNumber ?? ""));
      }
    });
  }, []);

  function applyEvent(nextType: string) {
    const event = catalog.find((item) => item.eventType === nextType);
    setEventType(nextType);
    if (!event) {
      return;
    }
    setPayloadText(JSON.stringify(event.samplePayload, null, 2));
    setPolicyNumber(String(event.samplePayload.policyNumber ?? ""));
    setMessage("");
    setError("");
    setResult(null);
  }

  function parsedPayload(): Record<string, unknown> {
    const parsed = JSON.parse(payloadText) as Record<string, unknown>;
    if (policyNumber) {
      parsed.policyNumber = policyNumber;
    }
    return parsed;
  }

  function formatJson() {
    try {
      setPayloadText(JSON.stringify(JSON.parse(payloadText), null, 2));
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid JSON");
    }
  }

  function resetPayload() {
    if (selected) {
      setPayloadText(JSON.stringify(selected.samplePayload, null, 2));
      setPolicyNumber(String(selected.samplePayload.policyNumber ?? ""));
    }
  }

  async function send() {
    setMessage("");
    setError("");
    try {
      const payload = parsedPayload();
      const response = await api.sendWebhook(payload, apiKey || undefined);
      setResult(response);
      if (response.status >= 200 && response.status < 300) {
        setMessage(`Webhook sent. HTTP ${response.status}`);
      } else {
        setError(`Webhook returned HTTP ${response.status}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send webhook");
    }
  }

  const curl = useMemo(() => {
    const url = config?.webhookUrl ?? "http://localhost:3000/webhooks/iri";
    let pretty = payloadText;
    try {
      pretty = JSON.stringify(parsedPayload());
    } catch {
      pretty = payloadText;
    }
    const keyLine = config?.authEnabled ? `  -H "X-API-Key: ${apiKey || "test-token"}" \\\n` : "";
    return `curl -X POST ${url} \\\n  -H "Content-Type: application/json" \\\n${keyLine}  -d '${pretty}'`;
  }, [apiKey, config, payloadText, policyNumber]);

  return (
    <div className="split">
      <section className="card panel">
        <h3>Send Test Notification</h3>
        <p className="help">
          Sample payloads are labelled as test data from the IRI catalogue. Edit freely before sending.
        </p>
        {message ? <div className="flash">{message}</div> : null}
        {error ? <div className="flash error">{error}</div> : null}
        <label className="field" style={{ marginTop: 12 }}>
          Event Type
          <select value={eventType} onChange={(event) => applyEvent(event.target.value)}>
            {catalog.map((item) => (
              <option key={item.eventType} value={item.eventType}>
                {item.displayName}
              </option>
            ))}
          </select>
        </label>
        {selected ? <p className="notice">{selected.description}</p> : null}
        <label className="field" style={{ marginTop: 12 }}>
          Policy Number
          <input value={policyNumber} onChange={(event) => setPolicyNumber(event.target.value)} />
        </label>
        {config?.authEnabled ? (
          <label className="field" style={{ marginTop: 12 }}>
            X-API-Key
            <input value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="Required" />
          </label>
        ) : null}
        <label className="field" style={{ marginTop: 12 }}>
          Test Payload
          <textarea value={payloadText} onChange={(event) => setPayloadText(event.target.value)} />
        </label>
        <div className="inline" style={{ marginTop: 12 }}>
          <button className="btn secondary" type="button" onClick={formatJson}>
            Format JSON
          </button>
          <button className="btn secondary" type="button" onClick={resetPayload}>
            Reset Payload
          </button>
          <button className="btn" type="button" onClick={() => void send()}>
            Send Webhook
          </button>
        </div>
      </section>
      <section className="card panel">
        <div className="panel-header">
          <h3>Developer usage</h3>
          <button className="btn secondary" type="button" onClick={() => void navigator.clipboard.writeText(curl)}>
            Copy curl
          </button>
        </div>
        <pre className="json-body" style={{ background: "#102033", color: "#d7e3ef", borderRadius: 10 }}>
          {curl}
        </pre>
        {result ? (
          <div style={{ marginTop: 16 }}>
            <JsonViewer value={result} label="Last response" />
          </div>
        ) : null}
      </section>
    </div>
  );
}
