"use client";

import Link from "next/link";
import { useActionState, useMemo, useState } from "react";
import { countLeaveDays, type DayPortion } from "@/lib/leave-days";
import { formatDays } from "@/lib/dates";
import { submitLeaveAction, updateLeaveAction, type ActionState } from "@/server/actions/portal";
import { Button } from "@/components/ui/button";
import { Field, Input, Select, Textarea } from "@/components/ui/field";

type LeaveTypeOption = {
  id: string;
  name: string;
  allowsHalfDay: boolean;
  requiresReason: boolean;
  available: number | null;
};

const initialState: ActionState = { error: "" };

export type LeaveDraft = {
  requestId: string;
  leaveTypeId: string;
  startDate: string;
  endDate: string;
  startPortion: DayPortion;
  endPortion: DayPortion;
  reason: string;
  informUsTeam: boolean;
};

export function LeaveForm({
  leaveTypes,
  weekendDays,
  holidayIsos,
  draft,
}: {
  leaveTypes: LeaveTypeOption[];
  weekendDays: number[];
  holidayIsos: string[];
  draft?: LeaveDraft;
}) {
  const [state, action, pending] = useActionState(draft ? updateLeaveAction : submitLeaveAction, initialState);
  const [leaveTypeId, setLeaveTypeId] = useState(draft?.leaveTypeId ?? leaveTypes[0]?.id ?? "");
  const [startDate, setStartDate] = useState(draft?.startDate ?? "");
  const [endDate, setEndDate] = useState(draft?.endDate ?? "");
  const [startPortion, setStartPortion] = useState<DayPortion>(draft?.startPortion ?? "FULL");
  const [endPortion, setEndPortion] = useState<DayPortion>(draft?.endPortion ?? "FULL");
  const idempotencyKey = useMemo(() => crypto.randomUUID(), []);
  const selected = leaveTypes.find((type) => type.id === leaveTypeId);

  const preview =
    startDate && endDate
      ? countLeaveDays({
          startIso: startDate,
          endIso: endDate,
          startPortion,
          endPortion,
          weekendDays,
          holidayIsos,
          allowsHalfDay: selected?.allowsHalfDay ?? false,
        })
      : null;

  return (
    <form action={action} className="max-w-xl space-y-4 rounded-xl border border-line bg-white p-5">
      {draft ? <input type="hidden" name="requestId" value={draft.requestId} /> : <input type="hidden" name="idempotencyKey" value={idempotencyKey} />}
      <Field label="Leave type">
        <Select name="leaveTypeId" value={leaveTypeId} onChange={(event) => setLeaveTypeId(event.target.value)}>
          {leaveTypes.map((type) => (
            <option key={type.id} value={type.id}>
              {type.name}
            </option>
          ))}
        </Select>
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Start date">
          <Input name="startDate" type="date" required value={startDate} onChange={(event) => setStartDate(event.target.value)} />
        </Field>
        <Field label="End date">
          <Input name="endDate" type="date" required value={endDate} onChange={(event) => setEndDate(event.target.value)} />
        </Field>
      </div>
      {selected?.allowsHalfDay ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Start day">
            <Select name="startPortion" value={startPortion} onChange={(event) => setStartPortion(event.target.value as DayPortion)}>
              <option value="FULL">Full day</option>
              <option value="AM">Morning</option>
              <option value="PM">Afternoon</option>
            </Select>
          </Field>
          <Field label="End day">
            <Select name="endPortion" value={endPortion} onChange={(event) => setEndPortion(event.target.value as DayPortion)}>
              <option value="FULL">Full day</option>
              <option value="AM">Morning</option>
              <option value="PM">Afternoon</option>
            </Select>
          </Field>
        </div>
      ) : (
        <>
          <input type="hidden" name="startPortion" value="FULL" />
          <input type="hidden" name="endPortion" value="FULL" />
        </>
      )}
      <Field label="Reason" hint={selected?.requiresReason ? "Required for this leave type." : "Optional"}>
        <Textarea name="reason" required={selected?.requiresReason} defaultValue={draft?.reason ?? ""} />
      </Field>
      <label className="flex items-start gap-2 text-sm">
        <input
          type="checkbox"
          name="informUsTeam"
          value="true"
          defaultChecked={draft?.informUsTeam ?? false}
          className="mt-0.5 h-4 w-4 accent-info"
        />
        <span>
          <span className="font-medium">Informed to US Team</span>
          <span className="mt-0.5 block text-xs text-muted">
            An administrator can change this before the leave is included in the US team sheet.
          </span>
        </span>
      </label>
      <div className="rounded-lg bg-canvas px-3 py-3 text-sm">
        <p>
          Working days requested:{" "}
          <span className="font-medium">{preview?.ok ? formatDays(preview.requestedDays) : "—"}</span>
        </p>
        <p className="mt-1 text-muted">
          Available balance:{" "}
          {selected?.available == null ? "Not tracked" : `${formatDays(selected.available)} days`}
        </p>
        {preview && !preview.ok ? <p className="mt-1 text-danger">{preview.error}</p> : null}
      </div>
      {state.error ? <p role="alert" className="text-sm text-danger">{state.error}</p> : null}
      <div className="flex items-center gap-3">
        <Button type="submit" disabled={pending}>
          {pending ? (draft ? "Saving…" : "Submitting…") : draft ? "Save changes" : "Submit request"}
        </Button>
        {draft ? (
          <Link href="/leave" className="text-sm font-medium text-muted">
            Cancel
          </Link>
        ) : null}
      </div>
    </form>
  );
}
