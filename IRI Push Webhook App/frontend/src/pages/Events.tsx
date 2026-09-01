import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { StatusBadge } from "../components/StatusBadge";
import { useWebhookStream } from "../hooks/useWebhookStream";
import { api } from "../services/api";
import type { CatalogEvent, EventListQuery, WebhookEvent } from "../types";

export function EventsPage() {
  const [catalog, setCatalog] = useState<CatalogEvent[]>([]);
  const [events, setEvents] = useState<WebhookEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<EventListQuery>({});
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    const list = await api.listWebhookEvents(filters);
    setEvents(list.events);
    setTotal(list.total);
  }, [filters]);

  useEffect(() => {
    void api.getCatalog().then((catalogResult) => setCatalog(catalogResult.events));
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useWebhookStream(() => {
    void refresh();
  });

  async function clearAll() {
    if (!window.confirm("Delete all stored webhook events?")) {
      return;
    }
    const result = await api.clearWebhookEvents();
    setMessage(`Deleted ${result.deleted} events`);
    await refresh();
  }

  return (
    <section className="card panel">
      <div className="panel-header">
        <div>
          <h3>Webhook Events</h3>
          <p className="help">{total} stored request{total === 1 ? "" : "s"}</p>
        </div>
        <button className="btn danger" type="button" onClick={() => void clearAll()}>
          Clear all
        </button>
      </div>
      {message ? <div className="flash">{message}</div> : null}
      <div className="filters">
        <label className="field">
          Event Type
          <select
            value={filters.eventType ?? ""}
            onChange={(event) => setFilters((current) => ({ ...current, eventType: event.target.value }))}
          >
            <option value="">All events</option>
            {catalog.map((item) => (
              <option key={item.eventType} value={item.eventType}>
                {item.displayName}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          Policy Number
          <input
            value={filters.policyNumber ?? ""}
            onChange={(event) => setFilters((current) => ({ ...current, policyNumber: event.target.value }))}
            placeholder="P987654321"
          />
        </label>
        <label className="field">
          HTTP Status
          <input
            value={filters.status ?? ""}
            onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}
            placeholder="200"
          />
        </label>
        <label className="field">
          Search
          <input
            value={filters.search ?? ""}
            onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
            placeholder="event, policy, payload"
          />
        </label>
        <label className="field">
          Date
          <input
            type="date"
            value={filters.from?.slice(0, 10) ?? ""}
            onChange={(event) =>
              setFilters((current) => ({
                ...current,
                from: event.target.value ? `${event.target.value}T00:00:00.000Z` : ""
              }))
            }
          />
        </label>
      </div>
      {events.length === 0 ? (
        <div className="empty">No matching webhook events.</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Event</th>
                <th>Policy Number</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id}>
                  <td className="mono">{new Date(event.receivedAt).toLocaleString()}</td>
                  <td>
                    <div className="mono">{event.eventType ?? "unknown"}</div>
                    <div className="help">{event.displayName}</div>
                  </td>
                  <td>{event.policyNumber ?? "—"}</td>
                  <td>
                    <StatusBadge status={event.responseStatus} />
                  </td>
                  <td>{event.processingTimeMs}ms</td>
                  <td>
                    <Link to={`/events/${event.id}`} className="btn link">
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
