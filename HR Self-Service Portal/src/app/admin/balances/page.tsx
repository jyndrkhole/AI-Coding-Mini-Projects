import { AdjustmentForm } from "@/components/admin/admin-forms";
import { Notice } from "@/components/feedback/notice";
import { PageHeader } from "@/components/layout/page-header";
import { formatDays } from "@/lib/dates";
import { requireAdmin } from "@/server/auth/guard";
import { prisma } from "@/server/db";
import { getBalanceCards } from "@/server/services/leave";

export const metadata = { title: "Leave Balances" };

export default async function BalancesPage({
  searchParams,
}: {
  searchParams: Promise<{ notice?: string; error?: string }>;
}) {
  await requireAdmin();
  const params = await searchParams;
  const [employees, leaveTypes] = await Promise.all([
    prisma.employee.findMany({ where: { employmentStatus: "ACTIVE" }, orderBy: { fullName: "asc" } }),
    prisma.leaveType.findMany({ where: { tracksBalance: true, isActive: true }, orderBy: { name: "asc" } }),
  ]);
  const rows = [];
  for (const employee of employees) {
    const cards = await getBalanceCards(employee.id);
    for (const card of cards) rows.push({ employee, card });
  }

  return (
    <div className="space-y-8">
      <PageHeader title="Leave Balances" description="Available leave is calculated from entitlements, adjustments, and approved requests." />
      <Notice notice={params.notice} error={params.error} />
      <div className="overflow-x-auto rounded-xl border border-line bg-white">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Employee</th>
              <th className="px-4 py-3 font-medium">Leave type</th>
              <th className="px-4 py-3 font-medium">Available</th>
              <th className="px-4 py-3 font-medium">Pending</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.employee.id}-${row.card.leaveTypeId}`} className="border-b border-line last:border-0">
                <td className="px-4 py-3">{row.employee.fullName}</td>
                <td className="px-4 py-3">{row.card.name}</td>
                <td className="px-4 py-3">{row.card.available == null ? "—" : formatDays(row.card.available)}</td>
                <td className="px-4 py-3">{formatDays(row.card.pending)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {employees.length > 0 && leaveTypes.length > 0 ? (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Adjust a balance</h2>
          <AdjustmentForm
            employees={employees.map((employee) => ({ id: employee.id, label: employee.fullName }))}
            leaveTypes={leaveTypes.map((type) => ({ id: type.id, label: type.name }))}
          />
        </section>
      ) : null}
    </div>
  );
}
