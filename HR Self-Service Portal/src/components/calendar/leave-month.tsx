import Link from "next/link";
import { CalendarMonthYear } from "@/components/calendar/calendar-month-year";
import { dateOnly, isoFromDateOnly, todayIso } from "@/lib/dates";
import { prisma } from "@/server/db";
import { getOrganization } from "@/server/services/organization";

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
  viewerEmployeeId: _viewerEmployeeId,
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
  const [days, holidays] = await Promise.all([
    prisma.leaveRequestDay.findMany({
      where: {
        leaveDate: { gte: dateOnly(start), lte: dateOnly(end) },
        leaveRequest: { status: { in: ["PENDING", "APPROVED"] } },
      },
      include: { leaveRequest: { include: { employee: true, leaveType: true } } },
      orderBy: { leaveDate: "asc" },
    }),
    prisma.holiday.findMany({
      where: {
        isActive: true,
        holidayDate: { gte: dateOnly(start), lte: dateOnly(end) },
      },
      orderBy: { holidayDate: "asc" },
    }),
  ]);

  const holidaysByDate = new Map<string, Array<{ id: string; name: string }>>();
  for (const holiday of holidays) {
    const iso = isoFromDateOnly(holiday.holidayDate);
    const list = holidaysByDate.get(iso) ?? [];
    list.push({ id: holiday.id, name: holiday.name });
    holidaysByDate.set(iso, list);
  }

  const byDate = new Map<string, Array<{ id: string; label: string; informUsTeam: boolean }>>();
  for (const day of days) {
    const iso = isoFromDateOnly(day.leaveDate);
    const label = `${day.leaveRequest.employee.fullName.split(" ")[0]} · ${day.leaveRequest.leaveType.name}`;
    const list = byDate.get(iso) ?? [];
    list.push({ id: day.id, label, informUsTeam: day.leaveRequest.informUsTeam });
    byDate.set(iso, list);
  }

  const lead = (new Date(Date.UTC(year, month - 1, 1)).getUTCDay() + 6) % 7;
  const cells: Array<string | null> = Array.from({ length: lead }, () => null);
  for (let day = 1; day <= endDate.getUTCDate(); day += 1) {
    cells.push(`${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`);
  }
  const previous = shiftMonth(year, month, -1);
  const next = shiftMonth(year, month, 1);
  const organization = await getOrganization();
  const todayYear = Number(todayIso(organization.timezone).slice(0, 4));
  const firstYear = Math.min(todayYear - 1, year);
  const lastYear = Math.max(todayYear + 2, year);
  const years = Array.from({ length: lastYear - firstYear + 1 }, (_, index) => firstYear + index);
  const monthName = new Intl.DateTimeFormat("en-GB", { month: "long", timeZone: "UTC" }).format(
    new Date(Date.UTC(year, month - 1, 1)),
  );

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <CalendarMonthYear basePath={basePath} year={year} month={month} monthName={monthName} years={years} />
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
              {(iso ? holidaysByDate.get(iso) : [])?.map((holiday) => (
                <li key={holiday.id} className="truncate rounded bg-warning/15 px-1 py-0.5 text-[11px] text-warning">
                  {holiday.name}
                </li>
              ))}
              {(iso ? byDate.get(iso) : [])?.map((event) => (
                <li
                  key={event.id}
                  className={
                    event.informUsTeam
                      ? "truncate rounded bg-info/15 px-1 py-0.5 text-[11px] text-info"
                      : "truncate rounded bg-brand/10 px-1 py-0.5 text-[11px] text-brand"
                  }
                >
                  {event.label}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm bg-warning/80" />
          Holiday
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm bg-info/80" />
          Informed to US Team
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm bg-brand/60" />
          Not informed to US team
        </span>
        <span>
          {scope === "employee"
            ? "Other people’s leave shows a name and type. Reasons stay private."
            : "Approved and pending leave for the organization."}
        </span>
      </div>
    </div>
  );
}
