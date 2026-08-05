"use client";

import { useState } from "react";
import type { AppState } from "@/lib/types";
import { DEFAULT_TIMEZONE } from "@/lib/types";
import { Modal } from "./Modal";

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentsPage({
  state,
  onRefresh,
  toast,
  onImportClick,
}: {
  state: AppState;
  onRefresh: () => Promise<void>;
  toast: (msg: string, error?: boolean) => void;
  onImportClick: () => void;
}) {
  const [uploading, setUploading] = useState(false);
  const folder = state.settings.driveFolder;
  const sync = state.settings.driveSync;

  async function onUpload(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true);
    try {
      const form = new FormData();
      for (const f of Array.from(files)) form.append("files", f);
      const res = await fetch("/api/documents", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Upload failed");
      if (data.errors?.length) toast(data.errors.join("; "), true);
      else toast(`Stored ${data.stored} file${data.stored === 1 ? "" : "s"}`);
      await onRefresh();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Upload failed", true);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="stack">
      <div className="grid-2">
        <div className="card">
          <h3 className="section-title">Upload documents</h3>
          <p className="section-sub">
            Receipts, statements, invoices, PDFs, images, CSVs, and spreadsheets. Max 20 MB each.
          </p>
          <label className="btn btn-primary" style={{ cursor: uploading ? "not-allowed" : "pointer" }}>
            {uploading ? "Uploading…" : "Choose files"}
            <input
              type="file"
              multiple
              hidden
              disabled={uploading}
              accept=".csv,.pdf,.png,.jpg,.jpeg,.webp,.xls,.xlsx,.heic,image/*,application/pdf,text/csv"
              onChange={(e) => onUpload(e.target.files)}
            />
          </label>
          <div className="helper" style={{ marginTop: 12 }}>
            Or use the global Import action for CSV column mapping.
            <button type="button" className="btn btn-ghost" style={{ marginLeft: 8 }} onClick={onImportClick}>
              Import
            </button>
          </div>
        </div>
        <div className="card">
          <h3 className="section-title">Google Drive inbox</h3>
          <p className="section-sub">{folder?.name || "Ledgerly Financial Inbox"}</p>
          <div className="stack" style={{ gap: 8 }}>
            <div className="helper">
              Schedule: daily at {sync.schedule?.time || "08:00"} ({sync.schedule?.timezone || DEFAULT_TIMEZONE})
            </div>
            <div>
              <span className="pill">Schedule active</span>
            </div>
            <div className="helper">
              Last sync: {sync.lastSyncedAt || "Not yet run"} · status {sync.status || "idle"}
            </div>
            <div className="helper">
              Last result — imported {sync.imported || 0}, duplicates {sync.duplicates || 0}, stored {sync.stored || 0}, review {sync.review || 0}
            </div>
            {folder?.url ? (
              <a href={folder.url} target="_blank" rel="noreferrer" className="btn btn-ghost" style={{ width: "fit-content" }}>
                View Drive folder
              </a>
            ) : (
              <p className="helper">
                Connect this folder in ChatGPT Work (name: Ledgerly Financial Inbox). Local runs store uploads in the Site vault only.
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <h3 className="section-title">Document vault</h3>
        <p className="section-sub">Original files stored by Ledgerly. Platform storage protections apply.</p>
        {state.documents.length === 0 ? (
          <div className="empty-state">No documents yet. Upload a file or add one to your Drive inbox.</div>
        ) : (
          <div className="table-wrap" style={{ border: "none" }}>
            <table className="data">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Type</th>
                  <th>Size</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Imported</th>
                </tr>
              </thead>
              <tbody>
                {state.documents.map((d) => (
                  <tr key={d.id}>
                    <td>{d.filename}</td>
                    <td>{d.mimeType}</td>
                    <td>{formatBytes(d.size)}</td>
                    <td>{d.source}</td>
                    <td><span className="pill">{d.status}</span></td>
                    <td>{new Date(d.createdAt).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export function DriveSyncModal({
  open,
  onClose,
  state,
  onRefresh,
  toast,
}: {
  open: boolean;
  onClose: () => void;
  state: AppState;
  onRefresh: () => Promise<void>;
  toast: (msg: string, error?: boolean) => void;
}) {
  const [busy, setBusy] = useState(false);
  async function runCheck() {
    setBusy(true);
    try {
      const res = await fetch("/api/drive-sync");
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Sync check failed");
      toast(
        data.lastSyncedAt
          ? `Inbox checked. Last sync ${new Date(data.lastSyncedAt).toLocaleString()}.`
          : "Inbox endpoint is live. Waiting for the daily automation or a Drive post."
      );
      await onRefresh();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Sync check failed", true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Drive sync" open={open} onClose={onClose}>
      <p style={{ marginTop: 0 }}>
        The ChatGPT Work automation reads <strong>{state.settings.driveFolder?.name || "Ledgerly Financial Inbox"}</strong> daily at 8:00 AM ({state.settings.driveSync.schedule?.timezone || DEFAULT_TIMEZONE}) and posts only new files to this Site.
      </p>
      <p className="helper">
        This Site does not browse Drive from the browser. Use the automation or a secured server post to <code>/api/drive-sync</code>.
      </p>
      <div className="modal-actions">
        <button type="button" className="btn btn-ghost" onClick={onClose}>Close</button>
        <button type="button" className="btn btn-primary" disabled={busy} onClick={runCheck}>
          {busy ? "Checking…" : "Check sync status"}
        </button>
      </div>
    </Modal>
  );
}
