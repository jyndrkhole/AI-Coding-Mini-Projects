import { PageHeader } from "@/components/layout/page-header";
import { requireUser } from "@/server/auth/guard";
import { formatDisplayDate } from "@/lib/dates";

export const metadata = { title: "My Profile" };

export default async function ProfilePage() {
  const session = await requireUser();
  const employee = session.user.employee;
  const rows = [
    ["Name", employee?.fullName ?? "—"],
    ["Employee ID", employee?.employeeCode ?? "—"],
    ["Email", session.user.email],
    ["Department", employee?.department ?? "—"],
    ["Designation", employee?.designation ?? "—"],
    ["Joining date", employee ? formatDisplayDate(employee.joiningDate.toISOString().slice(0, 10)) : "—"],
    ["Status", employee?.employmentStatus === "ACTIVE" ? "Active" : "Inactive"],
    ["Role", session.user.role === "ADMINISTRATOR" ? "Administrator" : "Employee"],
  ];

  return (
    <div>
      <PageHeader title="My Profile" description="Employment details are maintained by an administrator." />
      <dl className="max-w-xl divide-y divide-line rounded-xl border border-line bg-white">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-2 gap-4 px-4 py-3 text-sm">
            <dt className="text-muted">{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
