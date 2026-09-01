export function StatusBadge({ status }: { status: number }) {
  const ok = status >= 200 && status < 300;
  return <span className={`badge ${ok ? "success" : "danger"}`}>{status}</span>;
}
