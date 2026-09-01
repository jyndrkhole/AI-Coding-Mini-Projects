import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { StatCard } from "../components/StatCard";
import { StatusBadge } from "../components/StatusBadge";
import { useWebhookStream } from "../hooks/useWebhookStream";
import { api } from "../services/api";
import type { DashboardStats, WebhookEvent } from "../types";

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString();
}

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [events, setEvents] = useState<WebhookEvent[]>([]);

  const refresh = useCallback(async () => {
    const [nextStats, list] = await Promise.all([api.getStats(), api.listWebhookEvents()]);
    setStats(nextStats);
    setEvents(list.events.slice(0, 12));
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useWebhookStream(() => {
    void refresh();
  });

  return (
    <div>
      <div className="grid-stats">
        <StatCard label="Total Events" value={stats?.totalEvents ?? 0} />
        <StatCard label="Successful" value={stats?.successful ?? 0} />
        <StatCard label="Failed" value={stats?.failed ?? 0} />
        <StatCard label="Events Today" value={stats?.eventsToday ?? 0} />
        <StatCard label="Event Types" value={stats?.eventTypes ?? 0} />
      </div>
      <section className="card panel">
        <div className="panel-header">
          <h3>Recent Events</h3>
          <Link to="/events" className="btn secondary">
            View all
          </Link>
        </div>
        {events.length === 0 ? (
          <div className="empty">No webhooks received yet. POST to /webhooks/iri or send a test notification.</div>
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
                    <td className="mono">{formatTime(event.receivedAt)}</td>
                    <td>
                      <div className="mono">{event.eventType ?? "unknown"}</div>
                      {!event.knownEvent ? <span className="badge warn">Unknown/Future Event</span> : null}
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
    </div>
  );
}
