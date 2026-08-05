# Ledgerly

Private personal finance dashboard. Durable state lives in D1 (SQLite locally under `.data/`); original uploads live in R2 (local filesystem under `.data/r2/`).

## Local development

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## ChatGPT Sites deploy

This project is Sites-ready:

- `.openai/hosting.json` binds `DB` (D1) and `BUCKET` (R2)
- APIs: `/api/state`, `/api/transactions`, `/api/preferences`, `/api/documents`, `/api/drive-sync`, `/api/import/csv`, `/api/rules`, `/api/tags`

Publish from **ChatGPT Work** with Sites connected (this Cursor workspace cannot provision Sites, Drive, or Work automations).

### One-time ChatGPT Work setup

1. Open this folder in ChatGPT Work / Codex with **Sites** and **Google Drive** connected.
2. Ask it to publish this Site privately (reuse one Site; do not create copies).
3. Ensure Drive folder **`Ledgerly Financial Inbox`** exists (reuse if present).
4. Create automation **Sync Ledgerly Inbox** daily at **08:00 Asia/Kolkata** posting to `/api/drive-sync`.

See `CHATGPT_WORK_HANDOFF.md` for the exact automation instructions.
