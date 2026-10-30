import { NextResponse } from "next/server";
import { formatDateRange } from "@/lib/dates";
import { getCurrentSession } from "@/server/auth/session";
import { listLeaveRequests } from "@/server/services/leave";

function cell(value: string) {
  if (/[",\n]/.test(value)) return `"${value.replaceAll('"', '""')}"`;
  return value;
}

export async function GET() {
  const session = await getCurrentSession();
  if (!session || session.user.role !== "ADMINISTRATOR") {
    return NextResponse.json({ error: "You do not have permission to export reports." }, { status: 403 });
  }
  const requests = await listLeaveRequests({});
  const lines = [
    ["Employee", "Employee ID", "Leave type", "Dates", "Days", "Status"].join(","),
    ...requests.map((request) =>
      [
        request.employeeName,
        request.employeeCode,
        request.leaveTypeName,
        formatDateRange(request.startIso, request.endIso),
        String(request.requestedDays),
        request.status,
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
