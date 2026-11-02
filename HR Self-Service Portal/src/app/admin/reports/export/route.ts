import { NextResponse } from "next/server";
import { formatDays } from "@/lib/dates";
import { getCurrentSession } from "@/server/auth/session";
import { listLeaveDaysForExport, resolveReportScope } from "@/server/services/leave";

function cell(value: string) {
  if (/[",\n]/.test(value)) return `"${value.replaceAll('"', '""')}"`;
  return value;
}

export async function GET(request: Request) {
  const session = await getCurrentSession();
  if (!session || session.user.role !== "ADMINISTRATOR") {
    return NextResponse.json({ error: "You do not have permission to export reports." }, { status: 403 });
  }

  const url = new URL(request.url);
  const scope = await resolveReportScope({
    employee: url.searchParams.get("employee") ?? undefined,
    from: url.searchParams.get("from") ?? undefined,
    to: url.searchParams.get("to") ?? undefined,
  });
  const days = await listLeaveDaysForExport(scope);
  const lines = [
    ["Date", "Employee", "Employee ID", "Leave type", "Days", "Status", "Informed to US Team"].join(","),
    ...days.map((day) =>
      [
        day.dateIso,
        day.employeeName,
        day.employeeCode,
        day.leaveTypeName,
        formatDays(day.portion),
        day.status,
        day.informUsTeam ? "Yes" : "No",
      ]
        .map(cell)
        .join(","),
    ),
  ];

  return new NextResponse(lines.join("\n"), {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": "attachment; filename=\"peoplehub-leave.csv\"",
    },
  });
}
