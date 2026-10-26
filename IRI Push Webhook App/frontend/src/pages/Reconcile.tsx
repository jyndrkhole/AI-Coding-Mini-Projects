import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { JsonViewer } from "../components/JsonViewer";
import { api } from "../services/api";
import type { PortalConfig, ReconciliationEvent, ReconciliationResult, SourceEventResult } from "../types";

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

function toDateInput(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function sourceBaseForDisplay(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }
  try {
    const url = new URL(trimmed);
    url.search = "";
    url.hash = "";
    const path = url.pathname
      .replace(/\/+$/, "")
      .replace(/\/v\d+\/application-notifications(?:\/.*)?$/i, "")
      .replace(/\/getAuthToken$/i, "");
    url.pathname = path || "/";
    return url.toString().replace(/\/$/, "");
  } catch {
    return trimmed.replace(/\/$/, "");
  }
}

function sourceDate(value: string): string {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) ? value : "";
}

export function ReconcilePage() {
  const [config, setConfig] = useState<PortalConfig | null>(null);
  const today = new Date();
  const [startTime, setStartTime] = useState(`${today.getFullYear()}-01-01`);
  const [endTime, setEndTime] = useState(toDateInput(today));
  const [associatedFirmId, setAssociatedFirmId] = useState("");
  const [correlationId, setCorrelationId] = useState("");
  const [orderBy, setOrderBy] = useState("");
  const [sortOrder, setSortOrder] = useState("");
  const [offset, setOffset] = useState("");
  const [limit, setLimit] = useState("");
  const [lookupEventId, setLookupEventId] = useState("");
  const [sourceEndpoint, setSourceEndpoint] = useState(() => sessionStorage.getItem("iri-source-endpoint") ?? "");
  const [sourceApiKey, setSourceApiKey] = useState(() => sessionStorage.getItem("iri-source-x-api-key") ?? "");
  const [result, setResult] = useState<ReconciliationResult | null>(null);
  const [selected, setSelected] = useState<SourceEventResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingEventId, setLoadingEventId] = useState("");
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");

  useEffect(() => {
    void api.getConfig().then((portalConfig) => {
      setConfig(portalConfig);
      setSourceEndpoint((current) => current || portalConfig.sourceApiBaseUrl || "");
    }).catch(() => setConfig(null));
  }, []);

  useEffect(() => {
    sessionStorage.setItem("iri-source-endpoint", sourceEndpoint);
    sessionStorage.setItem("iri-source-x-api-key", sourceApiKey);
  }, [sourceEndpoint, sourceApiKey]);

  const sourceBase = sourceBaseForDisplay(config?.sourceApiBaseUrl ?? "");
  const activeEndpoint = sourceBaseForDisplay(sourceEndpoint) || sourceBase;
  const keyReady = Boolean(sourceApiKey.trim() || config?.sourceApiKeyConfigured);

  async function runReconciliation() {
    setError("");
    const start = sourceDate(startTime);
    const end = sourceDate(endTime);
    if (!start || !end) {
      setError("Enter a start and end time.");
      return;
    }
    if (!activeEndpoint) {
      setError("Enter the source base URL.");
      return;
    }
    if (!sourceApiKey.trim() && !config?.sourceApiKeyConfigured) {
      setError("Enter the source x-api-key.");
      return;
    }
    setLoading(true);
    try {
      const next = await api.reconcile({
        startTime: start,
        endTime: end,
        associatedFirmId,
        correlationId,
        orderBy,
        sortOrder,
        offset,
        limit,
        sourceApiKey,
        sourceBaseUrl: activeEndpoint
      });
      setResult(next);
      if (next.sourceStatus < 200 || next.sourceStatus >= 300) {
        setError(next.message || `Source API returned ${next.sourceStatus}`);
      }
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Reconciliation failed");
    } finally {
      setLoading(false);
    }
  }

  async function loadByEventId() {
    const eventId = lookupEventId.trim();
    if (!eventId) {
      setError("Enter an event id.");
      return;
    }
    if (!activeEndpoint) {
      setError("Enter the source base URL.");
      return;
    }
    if (!sourceApiKey.trim() && !config?.sourceApiKeyConfigured) {
      setError("Enter the source x-api-key.");
      return;
    }
    setLookupEventId(eventId);
    await loadPayload({ eventId, stored: false, portalEventId: null });
  }

  async function loadPayload(event: ReconciliationEvent) {
    if (!event.eventId) {
      return;
    }
    if (!activeEndpoint) {
      setError("Enter the source base URL.");
      return;
    }
    if (!sourceApiKey.trim() && !config?.sourceApiKeyConfigured) {
      setError("Enter the source x-api-key.");
      return;
    }
    setLookupEventId(event.eventId);
    setDetailError("");
    setLoadingEventId(event.eventId);
    try {
      const payload = await api.fetchSourceEvent(event.eventId, correlationId, sourceApiKey, activeEndpoint);
      setSelected(payload);
      if (payload.sourceStatus < 200 || payload.sourceStatus >= 300) {
        setDetailError(payload.message || `Source API returned ${payload.sourceStatus}`);
      }
    } catch (err) {
      setSelected(null);
      setDetailError(err instanceof Error ? err.message : "Could not load the source payload");
    } finally {
      setLoadingEventId("");
    }
  }

  return (
    <section className="card panel">
      <div className="panel-header">
        <h3>Reconcile</h3>
      </div>
      {error ? <div className="flash error">{error}</div> : null}
      <div className="reconcile-credentials">
        <label className="field">
          Source base URL
          <input
            value={sourceEndpoint}
            autoComplete="off"
            onChange={(event) => setSourceEndpoint(event.target.value)}
            placeholder={sourceBase || "https://host/api"}
          />
        </label>
        <label className="field">
          Source x-api-key
          <input
            type="password"
            value={sourceApiKey}
            autoComplete="off"
            onChange={(event) => setSourceApiKey(event.target.value)}
            placeholder={config?.sourceApiKeyConfigured ? "Using the key configured for this environment" : "Required"}
          />
        </label>
      </div>
      <div className="reconcile-split">
        <div className="reconcile-pane">
          <h4>Reconciliation</h4>
      <p className="help">Calls GET /v2/application-notifications/reconciliation on the source.</p>
      <div className="reconcile-filters">
        <label className="field">
          Start
          <input type="date" value={startTime} onChange={(event) => setStartTime(event.target.value)} />
        </label>
        <label className="field">
          End
          <input type="date" value={endTime} onChange={(event) => setEndTime(event.target.value)} />
        </label>
        <label className="field">
          Associated firm ID
          <input
            value={associatedFirmId}
            onChange={(event) => setAssociatedFirmId(event.target.value)}
            placeholder="Optional"
          />
        </label>
        <label className="field">
          Correlation ID
          <input
            value={correlationId}
            onChange={(event) => setCorrelationId(event.target.value)}
            placeholder="Optional header"
          />
        </label>
        <label className="field">
          Order by
          <input
            value={orderBy}
            onChange={(event) => setOrderBy(event.target.value)}
            placeholder="Optional"
          />
        </label>
        <label className="field">
          Sort
          <select value={sortOrder} onChange={(event) => setSortOrder(event.target.value)}>
            <option value="">Default</option>
            <option value="asc">asc</option>
            <option value="desc">desc</option>
          </select>
        </label>
        <label className="field">
          Offset
          <input
            type="number"
            min="0"
            value={offset}
            onChange={(event) => setOffset(event.target.value)}
            placeholder="Optional"
          />
        </label>
        <label className="field">
          Limit
          <input
            type="number"
            min="1"
            value={limit}
            onChange={(event) => setLimit(event.target.value)}
            placeholder="Optional"
          />
        </label>
        <label className="field">
          &nbsp;
          <button className="btn" type="button" disabled={!activeEndpoint || !keyReady || loading} onClick={() => void runReconciliation()}>
            {loading ? "Calling source…" : "Run reconciliation"}
          </button>
        </label>
      </div>
      {result ? (
        <>
          <p className="help">
            {`Source returned ${result.totalEvents} event${result.totalEvents === 1 ? "" : "s"} (HTTP ${result.sourceStatus}). ${result.storedCount} already stored, ${result.missingCount} missing.`}
          </p>
          {result.events.length === 0 ? (
            <div className="empty">The source returned no events for this window.</div>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Event ID</th>
                    <th>Policy</th>
                    <th>Application</th>
                    <th>Origin</th>
                    <th>Status</th>
                    <th>In portal</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {result.events.map((event, index) => (
                    <tr key={event.eventId || index} className={selected?.eventId === event.eventId ? "is-selected" : undefined}>
                      <td className="mono">{event.eventId || "—"}</td>
                      <td>{event.policyNumber || "—"}</td>
                      <td>{event.id || "—"}</td>
                      <td>{event.applicationOrigin?.platform || event.applicationOrigin?.id || "—"}</td>
                      <td>{event.status || "—"}</td>
                      <td>
                        <span className={`badge ${event.stored ? "success" : "warn"}`}>
                          {event.stored ? "Stored" : "Missing"}
                        </span>
                      </td>
                      <td>
                        <button
                          className="btn link"
                          type="button"
                          disabled={!keyReady || !event.eventId || loadingEventId === event.eventId}
                          onClick={() => void loadPayload(event)}
                        >
                          {loadingEventId === event.eventId ? "Loading…" : "Load payload"}
                        </button>
                        {event.portalEventId ? (
                          <Link to={`/events/${event.portalEventId}`} className="btn link" style={{ marginLeft: 12 }}>
                            View stored
                          </Link>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
        </div>
        <div className="reconcile-pane reconcile-detail">
          <h4>Get by event id</h4>
          <p className="help">{"Calls GET /v2/application-notifications/{eventId} on the source."}</p>
      <div className="reconcile-filters">
        <label className="field">
          Event ID
          <input
            value={lookupEventId}
            onChange={(event) => setLookupEventId(event.target.value)}
            placeholder="Source event id"
          />
        </label>
        <label className="field">
          &nbsp;
          <button
            className="btn"
            type="button"
            disabled={!activeEndpoint || !keyReady || !lookupEventId.trim() || loadingEventId === lookupEventId.trim()}
            onClick={() => void loadByEventId()}
          >
            {loadingEventId && loadingEventId === lookupEventId.trim() ? "Loading…" : "Get by event id"}
          </button>
        </label>
      </div>
          {detailError ? <div className="flash error">{detailError}</div> : null}
          {selected ? (
            <JsonViewer
              value={selected.payload}
              label={`Source payload ${selected.eventId} · HTTP ${selected.sourceStatus}`}
            />
          ) : null}
        </div>
      </div>
    </section>
  );
}
