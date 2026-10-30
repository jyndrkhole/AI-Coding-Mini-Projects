import Link from "next/link";
import { EmployeeForm } from "@/components/admin/admin-forms";
import { PageHeader } from "@/components/layout/page-header";
import { requireAdmin } from "@/server/auth/guard";
import { prisma } from "@/server/db";

export const metadata = { title: "Employees" };

export default async function EmployeesPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  await requireAdmin();
  const { q = "" } = await searchParams;
  const query = q.trim();
  const employees = await prisma.employee.findMany({
    where: query
      ? {
          OR: [
            { fullName: { contains: query, mode: "insensitive" } },
            { employeeCode: { contains: query, mode: "insensitive" } },
            { user: { email: { contains: query, mode: "insensitive" } } },
          ],
        }
      : {},
    include: { user: true },
    orderBy: { fullName: "asc" },
  });

  return (
    <div className="space-y-8">
      <PageHeader title="Employees" description="Accounts are created here. There is no public registration." />
      <form className="flex gap-2">
        <input
          name="q"
          defaultValue={query}
          placeholder="Search name, email, or employee ID"
          className="h-10 w-full max-w-md rounded-lg border border-line bg-white px-3 text-sm"
        />
        <button className="h-10 rounded-lg border border-line bg-white px-4 text-sm" type="submit">
          Search
        </button>
      </form>
      <div className="overflow-x-auto rounded-xl border border-line bg-white">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-line text-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Employee ID</th>
              <th className="px-4 py-3 font-medium">Email</th>
              <th className="px-4 py-3 font-medium">Department</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {employees.map((employee) => (
              <tr key={employee.id} className="border-b border-line last:border-0">
                <td className="px-4 py-3">
                  <Link href={`/admin/employees/${employee.id}`} className="font-medium text-brand">
                    {employee.fullName}
                  </Link>
                </td>
                <td className="px-4 py-3">{employee.employeeCode}</td>
                <td className="px-4 py-3">{employee.user.email}</td>
                <td className="px-4 py-3">{employee.department}</td>
                <td className="px-4 py-3">{employee.employmentStatus === "ACTIVE" ? "Active" : "Inactive"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <section>
        <h2 className="mb-3 text-lg font-semibold">Add an employee</h2>
        <EmployeeForm />
      </section>
    </div>
  );
}
