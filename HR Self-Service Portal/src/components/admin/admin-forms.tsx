"use client";

import { useActionState } from "react";
import {
  adjustBalanceAction,
  createEmployeeAction,
  createHolidayAction,
  createLeaveTypeAction,
  type ActionState,
} from "@/server/actions/portal";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";

const initial: ActionState = { error: "" };

export function EmployeeForm() {
  const [state, action, pending] = useActionState(createEmployeeAction, initial);
  return (
    <form action={action} className="grid gap-4 rounded-xl border border-line bg-white p-5 md:grid-cols-2">
      <Field label="Full name"><Input name="fullName" required /></Field>
      <Field label="Employee ID"><Input name="employeeCode" required /></Field>
      <Field label="Work email"><Input name="email" type="email" required /></Field>
      <Field label="Temporary password" hint="At least 10 characters. Share it securely."><Input name="password" type="text" required minLength={10} /></Field>
      <Field label="Department"><Input name="department" required /></Field>
      <Field label="Designation"><Input name="designation" required /></Field>
      <Field label="Joining date"><Input name="joiningDate" type="date" required /></Field>
      <Field label="Role">
        <Select name="role" defaultValue="EMPLOYEE">
          <option value="EMPLOYEE">Employee</option>
          <option value="ADMINISTRATOR">Administrator</option>
        </Select>
      </Field>
      {state.error ? <p className="text-sm text-danger md:col-span-2">{state.error}</p> : null}
      <div className="md:col-span-2"><Button type="submit" disabled={pending}>Add employee</Button></div>
    </form>
  );
}

export function LeaveTypeForm() {
  const [state, action, pending] = useActionState(createLeaveTypeAction, initial);
  return (
    <form action={action} className="grid gap-4 rounded-xl border border-line bg-white p-5">
      <Field label="Name"><Input name="name" required /></Field>
      <Field label="Description"><Textarea name="description" /></Field>
      <Field label="Annual entitlement" hint="Granted to active employees for the current leave year. Later edits do not rewrite existing entitlements.">
        <Input name="defaultAnnualEntitlement" type="number" min="0" step="0.5" defaultValue="0" required />
      </Field>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="isPaid" defaultChecked /> Paid leave</label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="tracksBalance" defaultChecked /> Track a balance</label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="allowsHalfDay" /> Allow half days</label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="allowsNegativeBalance" /> Allow a negative balance</label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="requiresReason" /> Require a reason</label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="carryForwardEligible" /> Eligible for carry-forward</label>
      <Field label="Maximum carry-forward days" hint="Stored for when a new leave year is opened. That step is not automated yet.">
        <Input name="maxCarryForwardDays" type="number" min="0" step="0.5" />
      </Field>
      {state.error ? <p className="text-sm text-danger">{state.error}</p> : null}
      <Button type="submit" disabled={pending}>Save leave type</Button>
    </form>
  );
}

export function HolidayForm() {
  const [state, action, pending] = useActionState(createHolidayAction, initial);
  return (
    <form action={action} className="grid gap-4 rounded-xl border border-line bg-white p-5 sm:grid-cols-[1fr_180px_auto] sm:items-end">
      <Field label="Holiday name"><Input name="name" required /></Field>
      <Field label="Date"><Input name="holidayDate" type="date" required /></Field>
      <Button type="submit" disabled={pending}>Add holiday</Button>
      {state.error ? <p className="text-sm text-danger sm:col-span-3">{state.error}</p> : null}
    </form>
  );
}

export function AdjustmentForm({
  employees,
  leaveTypes,
}: {
  employees: Array<{ id: string; label: string }>;
  leaveTypes: Array<{ id: string; label: string }>;
}) {
  const [state, action, pending] = useActionState(adjustBalanceAction, initial);
  return (
    <form action={action} className="grid gap-4 rounded-xl border border-line bg-white p-5">
      <Field label="Employee">
        <Select name="employeeId" required defaultValue={employees[0]?.id}>
          {employees.map((employee) => (
            <option key={employee.id} value={employee.id}>{employee.label}</option>
          ))}
        </Select>
      </Field>
      <Field label="Leave type">
        <Select name="leaveTypeId" required defaultValue={leaveTypes[0]?.id}>
          {leaveTypes.map((type) => (
            <option key={type.id} value={type.id}>{type.label}</option>
          ))}
        </Select>
      </Field>
      <Field label="Adjustment" hint="Use a negative number to reduce the balance. This is added to the ledger and does not erase history.">
        <Input name="adjustmentDays" type="number" step="0.5" required />
      </Field>
      <Field label="Reason"><Textarea name="reason" required /></Field>
      {state.error ? <p className="text-sm text-danger">{state.error}</p> : null}
      <Button type="submit" disabled={pending}>Save adjustment</Button>
    </form>
  );
}
