export function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <article className="card stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
