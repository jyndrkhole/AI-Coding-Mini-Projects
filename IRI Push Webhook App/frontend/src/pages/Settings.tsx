import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { PortalConfig } from "../types";

const DELAYS = [0, 500, 1000, 3000];

export function SettingsPage() {
  const [config, setConfig] = useState<PortalConfig | null>(null);
  const [customDelay, setCustomDelay] = useState("0");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    void api.getConfig().then((portalConfig) => {
      setConfig(portalConfig);
      setCustomDelay(String(portalConfig.responseDelayMs));
    });
  }, []);

  async function save(patch: { responseStatus?: number; responseDelayMs?: number }) {
    setError("");
    try {
      const updated = await api.updateConfig(patch);
      setConfig(updated);
      setCustomDelay(String(updated.responseDelayMs));
      setMessage("Simulation settings saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save settings");
    }
  }

  if (!config) {
    return <div className="empty">Loading settings…</div>;
  }

  return (
    <section className="card panel">
      <h3>Failure simulation</h3>
      <p className="help">
        These settings change how the test portal responds to POST /webhooks/iri so backend retry and timeout
        logic can be exercised. They do not implement carrier business rules.
      </p>
      {message ? <div className="flash">{message}</div> : null}
      {error ? <div className="flash error">{error}</div> : null}
      <label className="field" style={{ marginTop: 16 }}>
        Response status
      </label>
      <div className="status-pills">
        {config.allowedResponseStatuses.map((status) => (
          <button
            key={status}
            type="button"
            className={config.responseStatus === status ? "active" : ""}
            onClick={() => void save({ responseStatus: status })}
          >
            {status}
          </button>
        ))}
      </div>
      <label className="field" style={{ marginTop: 20 }}>
        Response delay
      </label>
      <div className="status-pills">
        {DELAYS.map((delay) => (
          <button
            key={delay}
            type="button"
            className={config.responseDelayMs === delay ? "active" : ""}
            onClick={() => void save({ responseDelayMs: delay })}
          >
            {delay} ms
          </button>
        ))}
      </div>
      <div className="inline" style={{ marginTop: 16 }}>
        <label className="field">
          Custom delay (ms)
          <input value={customDelay} onChange={(event) => setCustomDelay(event.target.value)} />
        </label>
        <button className="btn" type="button" onClick={() => void save({ responseDelayMs: Number(customDelay) })}>
          Apply delay
        </button>
      </div>
      <hr style={{ border: 0, borderTop: "1px solid var(--line)", margin: "24px 0" }} />
      <h3>Receiver configuration</h3>
      <dl className="kv" style={{ marginTop: 16 }}>
        <dt>Webhook URL</dt>
        <dd className="mono">{config.webhookUrl}</dd>
        <dt>IRI catalogue</dt>
        <dd>{config.catalogVersion}</dd>
        <dt>Authentication</dt>
        <dd>{config.authEnabled ? "Enabled (X-API-Key)" : "Disabled"}</dd>
        <dt>Current status</dt>
        <dd>{config.responseStatus}</dd>
        <dt>Current delay</dt>
        <dd>{config.responseDelayMs} ms</dd>
      </dl>
    </section>
  );
}
