# ChatGPT Work handoff — Ledgerly

This Cursor workspace built the full Ledgerly application locally. **Sites publishing, Google Drive folder creation, and Work automations are not available in Cursor.** Complete these steps once in ChatGPT Work.

## Timezone

Detected local timezone for scheduling: **Asia/Kolkata (IST)**. Daily run at **08:00**.

## 1. Publish the Site

1. Open this project in ChatGPT Work / Codex with the **Sites** connector authorized.
2. Ask: publish **Ledgerly** as one private/owner-only Site (reuse; do not create copies).
3. Confirm D1 binding `DB` and R2 binding `BUCKET` from `.openai/hosting.json`.
4. Verify `GET /api/drive-sync` on the published URL returns JSON (folder/schedule metadata).

## 2. Google Drive folder

1. Search Drive for a folder named exactly **`Ledgerly Financial Inbox`**.
2. If one exists, reuse it. If none, create it once. If multiple, pick one manually.
3. Save folder ID, name, and URL into Site settings via `PUT /api/preferences` with:

```json
{
  "driveFolder": {
    "id": "<FOLDER_ID>",
    "name": "Ledgerly Financial Inbox",
    "url": "<FOLDER_URL>"
  }
}
```

## 3. Automation — Sync Ledgerly Inbox

Create **one** daily exact schedule (not an approximate cadence):

```text
BEGIN:VEVENT
DTSTART:<next 8:00 AM Asia/Kolkata>
RRULE:FREQ=DAILY
END:VEVENT
```

`timing_mode`: exact schedule · timezone: **Asia/Kolkata**

### Run instructions (replace placeholders)

You maintain the private Ledgerly financial Site at `<EXACT_SITE_URL>` using the dedicated Google Drive folder `Ledgerly Financial Inbox` with ID `<EXACT_DRIVE_FOLDER_ID>`.

1. Verify Google Drive and Sites access with harmless reads. Resolve the exact existing Site. Obtain a temporary Site authorization/bypass bearer for this run through the Sites connection. Never display, persist, log, or place the token in source code.
2. Call `GET <EXACT_SITE_URL>/api/drive-sync` with `OAI-Sites-Authorization: Bearer <temporary-token>`. Treat `processedFileIds` as the authoritative Drive duplicate ledger. Read `resetAt`; ignore every Drive file whose modified time is at or before `resetAt`.
3. List only direct children of the dedicated Drive folder. Process only file IDs that are absent from `processedFileIds` and whose modified time is after `resetAt`. Do not move, rename, edit, share, trash, or delete Drive files.
4. For CSV statements, parse real rows into date, merchant, positive magnitude amount, income/expense type, account when grounded, category only when supported, tags, `receipt=false`, and `source=google-drive`. Preserve the statement's actual debit/credit meaning. Never invent missing values.
5. For receipts, invoices, PDFs, images, spreadsheets, and supported documents, extract merchant/payee, date, total, type, and category only when grounded. Set `receipt=true` for receipt/invoice-backed transactions. When material fields are uncertain, set file status to `review` and do not invent a transaction.
6. Download original file bytes when available. Post each new file or a small safe batch to `<EXACT_SITE_URL>/api/drive-sync` with Drive file ID, filename, MIME type, modified time, base64 content, status, grounded transactions, and the temporary authorization header. The Site endpoint owns durable storage and duplicate detection.
7. If a file cannot be read or transferred, include a concise error and leave its file ID unprocessed so a later run retries it.
8. Verify the Site response. Notify me with counts for new transactions, stored files, duplicates, and items needing review. If there were no new files, say the inbox was checked and is up to date. Include the Site link and any concise failures.

Never expose financial document contents, full account numbers, tokens, or secrets. Never change Site access, Drive sharing, or external data beyond importing it into the private Site.

## 4. Empty-start contract

Delivered app starts with empty financial datasets (no sample transactions). Starter categories/accounts are configuration only. Net Worth shows **Not set** until saved. Period defaults to **All time**.
