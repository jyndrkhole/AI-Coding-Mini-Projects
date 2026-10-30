import { PageHeader } from "@/components/layout/page-header";
import { requireAdmin } from "@/server/auth/guard";
import { prisma } from "@/server/db";

export const metadata = { title: "Audit Log" };

export default async function AuditPage() {
  await requireAdmin();
  const entries = await prisma.auditLog.findMany({
    orderBy: { createdAt: "desc" },
    take: 100,
    include: { actor: true },
  });

  return (
    <div>
      <PageHeader title="Audit Log" description="Administrative changes and leave decisions." />
      <ul className="divide-y divide-line rounded-xl border border-line bg-white">
        {entries.map((entry) => (
          <li key={entry.id} className="px-4 py-3 text-sm">
            <p className="font-medium">{entry.action}</p>
            <p className="text-muted">
              {entry.actor?.email ?? "System"} · {entry.entityType} · {entry.createdAt.toISOString()}
            </p>
          </li>
        ))}
        {entries.length === 0 ? <li className="px-4 py-6 text-muted">No audit events yet.</li> : null}
      </ul>
    </div>
  );
}
