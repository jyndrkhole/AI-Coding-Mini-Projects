const messages: Record<string, string> = {
  submitted: "Leave request submitted.",
  cancelled: "Leave request cancelled.",
  approved: "Leave request approved.",
  rejected: "Leave request rejected.",
  "leave-type": "Leave type saved. Active employees received this year's entitlement.",
  holiday: "Holiday saved.",
  employee: "Employee account created.",
  status: "Employment status updated.",
  balance: "Leave balance adjustment saved.",
};

export function Notice({ notice, error }: { notice?: string; error?: string }) {
  if (error) {
    return (
      <p role="alert" className="mb-4 rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-sm text-danger">
        {error}
      </p>
    );
  }
  const message = notice ? messages[notice] : undefined;
  if (!message) return null;
  return (
    <p role="status" className="mb-4 rounded-lg border border-success/20 bg-success/5 px-3 py-2 text-sm text-success">
      {message}
      {notice === "submitted" ? "" : ""}
    </p>
  );
}
