import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { JsonViewer } from "../components/JsonViewer";
import { StatusBadge } from "../components/StatusBadge";
import { api } from "../services/api";
import type { WebhookEvent } from "../types";

export function EventDetailPage() {
  const { id } = useParams();
  const [event, setEvent] = useState<WebhookEvent | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) {
      return;
    }
    void api
      .getWebhookEvent(id)
      .then(setEvent)
      .catch((err: Error) => setError(err.message));
  }, [id]);

  if (error) {
    return <div className="flash error">{error}</div>;
  }
  if (!event) {
    return <div className="empty">Loading event…</div>;
  }

  return (
    <div>
      <div className="panel-header">
        <h2>Event detail</h2>
        <Link to="/events" className="btn secondary">
          Back to events
        </Link>
      </div>
      <div className="detail-grid">
        <section className="card panel">
          <h3>Event information</h3>
          <dl className="kv" style={{ marginTop: 16 }}>
            <dt>Event ID</dt>
            <dd className="mono">{event.id}</dd>
            <dt>Event Type</dt>
            <dd className="mono">{event.eventType ?? "unknown"}</dd>
            <dt>Display name</dt>
            <dd>
              {event.displayName}
              {!event.knownEvent ? <span className="badge warn">Unknown/Future Event</span> : null}
            </dd>
            <dt>Policy Number</dt>
            <dd>{event.policyNumber ?? "—"}</dd>
            <dt>Received Time</dt>
            <dd>{new Date(event.receivedAt).toLocaleString()}</dd>
            <dt>HTTP Status</dt>
            <dd>
              <StatusBadge status={event.responseStatus} />
            </dd>
            <dt>Processing Time</dt>
            <dd>{event.processingTimeMs}ms</dd>
            <dt>Source IP</dt>
            <dd className="mono">{event.sourceIp ?? "—"}</dd>
            <dt>Method / Path</dt>
            <dd className="mono">
              {event.requestMethod} {event.requestPath}
            </dd>
          </dl>
        </section>
        <section className="card panel">
          <h3>Response</h3>
          <dl className="kv" style={{ marginTop: 16 }}>
            <dt>HTTP Status</dt>
            <dd>
              <StatusBadge status={event.responseStatus} />
            </dd>
            <dt>Processing Time</dt>
            <dd>{event.processingTimeMs}ms</dd>
          </dl>
          <div style={{ marginTop: 16 }}>
            <JsonViewer value={event.responseBody} label="Response body" />
          </div>
        </section>
      </div>
      <section className="card panel" style={{ marginTop: 16 }}>
        <h3>Request headers</h3>
        <p className="help">Authorization, API keys, tokens, and secrets are masked.</p>
        <div style={{ marginTop: 12 }}>
          <JsonViewer value={event.headers} label="Headers" />
        </div>
      </section>
      <section className="card panel" style={{ marginTop: 16 }}>
        <h3>Request payload</h3>
        <div style={{ marginTop: 12 }}>
          <JsonViewer value={event.payload} label="Payload" />
        </div>
      </section>
    </div>
  );
}
