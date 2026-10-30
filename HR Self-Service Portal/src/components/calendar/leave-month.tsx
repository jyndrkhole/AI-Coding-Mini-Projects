import Link from "next/link";
import { dateOnly, isoFromDateOnly } from "@/lib/dates";
import { prisma } from "@/server/db";

export type CalendarScope = "employee" | "admin";

function monthStart(year: number, month: number) {
  return `${year}-${String(month).padStart(2, "0")}-01`;
}

function shiftMonth(year: number, month: number, delta: number) {
  const date = new Date(Date.UTC(year, month - 1 + delta, 1));
  return { year: date.getUTCFullYear(), month: date.getUTCMonth() + 1 };
}

export async function LeaveMonth({
  year,
  month,
  scope,
  viewerEmployeeId,
  basePath,
}: {
  year: number;
  month: number;
  scope: CalendarScope;
  viewerEmployeeId: string | null;
  basePath: string;
}) {
  const start = monthStart(year, month);
  const endDate = new Date(Date.UTC(year, month, 0));
  const end = endDate.toISOString().slice(0, 10);
  const days = await prisma.leaveRequestDay.findMany({
    where: {
      leaveDate: { gte: dateOnly(start), lte: dateOnly(end) },
      leaveRequest: { status: { in: ["PENDING", "APPROVED"] } },
    },
    include: { leaveRequest: { include: { employee: true, leaveType: true } } },
    orderBy: { leaveDate: "asc" },
  });

  const byDate = new Map<string, Array<{ id: string; label: string }>>();
  for (const day of days) {
    const iso = isoFromDateOnly(day.leaveDate);
    const own = day.leaveRequest.employeeId === viewerEmployeeId;
    const label =
      scope === "admin" || own
        ? `${day.leaveRequest.employee.fullName.split(" ")[0]} · ${day.leaveRequest.leaveType.name}`
        : `${day.leaveRequest.employee.fullName.split(" ")[0]} · ${day.leaveRequest.leaveType.name}`;
    const list = byDate.get(iso) ?? [];
    list.push({ id: day.id, label });
    byDate.set(iso, list);
  }

  const lead = (new Date(Date.UTC(year, month - 1, 1)).getUTCDay() + 6) % 7;
  const cells: Array<string | null> = Array.from({ length: lead }, () => null);
  for (let day = 1; day <= endDate.getUTCDate(); day += 1) {
    cells.push(`${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`);
  }
  const previous = shiftMonth(year, month, -1);
  const next = shiftMonth(year, month, 1);
  const title = new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric", timeZone: "UTC" }).format(
    new Date(Date.UTC(year, month - 1, 1)),
  );

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">{title}</h2>
        <div className="flex gap-2 text-sm">
          <Link className="rounded-lg border border-line bg-white px-3 py-1.5" href={`${basePath}?year=${previous.year}&month=${previous.month}`}>
            Previous
          </Link>
          <Link className="rounded-lg border border-line bg-white px-3 py-1.5" href={`${basePath}?year=${next.year}&month=${next.month}`}>
            Next
          </Link>
        </div>
      </div>
      <div className="grid grid-cols-7 gap-px overflow-hidden rounded-xl border border-line bg-line">
        {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((label) => (
          <div key={label} className="bg-canvas px-2 py-2 text-xs font-medium text-muted">
            {label}
          </div>
        ))}
        {cells.map((iso, index) => (
          <div key={iso ?? `empty-${index}`} className="min-h-24 bg-white p-2">
            {iso ? <p className="text-xs text-muted">{Number(iso.slice(-2))}</p> : null}
            <ul className="mt-1 space-y-1">
              {(iso ? byDate.get(iso) : [])?.map((event) => (
                <li key={event.id} className="truncate rounded bg-brand/10 px-1 py-0.5 text-[11px] text-brand">
                  {event.label}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-muted">
        {scope === "employee"
          ? "Other people’s leave shows a name, type, and dates. Reasons stay private."
          : "Approved and pending leave for the organization."}
      </p>
    </div>
  );
}
