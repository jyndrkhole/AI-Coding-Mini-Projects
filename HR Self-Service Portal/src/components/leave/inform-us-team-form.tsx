"use client";

import { useActionState } from "react";
import { setInformUsTeamAction, type ActionState } from "@/server/actions/portal";
import { Button } from "@/components/ui/button";

const initial: ActionState = { error: "" };

export function InformUsTeamForm({ requestId, informed }: { requestId: string; informed: boolean }) {
  const [state, action, pending] = useActionState(setInformUsTeamAction, initial);
  return (
    <form action={action} className="mt-3 flex flex-wrap items-center gap-3">
      <input type="hidden" name="requestId" value={requestId} />
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" name="informUsTeam" value="true" defaultChecked={informed} className="h-4 w-4 accent-info" />
        Informed to US Team
      </label>
      <Button type="submit" size="sm" variant="secondary" disabled={pending}>
        {pending ? "Saving…" : "Save"}
      </Button>
      {state.error ? <p className="text-xs text-danger">{state.error}</p> : null}
    </form>
  );
}
