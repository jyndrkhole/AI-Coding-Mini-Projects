"use client";

import { useActionState } from "react";
import { reviewLeaveAction, type ActionState } from "@/server/actions/portal";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/field";

const initial: ActionState = { error: "" };

export function ReviewForm({ requestId, informUsTeam }: { requestId: string; informUsTeam: boolean }) {
  const [state, action, pending] = useActionState(reviewLeaveAction, initial);
  return (
    <form action={action} className="mt-2 space-y-2">
      <input type="hidden" name="requestId" value={requestId} />
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          name="informUsTeam"
          value="true"
          defaultChecked={informUsTeam}
          className="h-4 w-4 accent-info"
        />
        Informed to US Team
      </label>
      <Textarea name="comment" placeholder="Comment, required when rejecting" />
      {state.error ? <p className="text-xs text-danger">{state.error}</p> : null}
      <div className="flex gap-2">
        <Button type="submit" name="decision" value="APPROVED" size="sm" disabled={pending}>
          Approve
        </Button>
        <Button type="submit" name="decision" value="REJECTED" size="sm" variant="danger" disabled={pending}>
          Reject
        </Button>
      </div>
    </form>
  );
}
