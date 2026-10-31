# TripWise AI

A travel advisor that keeps three jobs apart:

- **SQLite** holds destinations, stays, sample prices, users, trips, and chats.
- **ChromaDB** holds the travel notebook. It is not the source of prices.
- **The MCP server** is the only process the advisor uses for `db_lookup`, `list_destinations`, and `compute_trip_cost`.
- **The host** runs Groq (or OpenAI), retrieval, and the two budget chains.

The multi-chain path is: MCP cost tool, then an explanation chain, then a GO / NOT YET chain. The explanation is told not to recompute the tool's numbers.

## Run locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Put GROQ_API_KEY in .env. Do not commit it.
python -m app.seed
python -m app.ingest
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173

Local demo accounts:

- `traveler@example.com` / `Tripwise#Travel1`
- `admin@example.com` / `Tripwise#Admin1`

## Try these

- `list`
- `We are 4 friends with ₹12,000 each. Can we do Goa for 3 nights?`
- `/plan Hampi 5 2 6000`
- `Is Manali a good idea in July?`

The budget page shows the tool result and both chains. Sample prices are demonstration estimates, not live fares.

## Tests

```bash
cd backend
pytest
```

The MCP test speaks to the server over stdio: handshake, tool call, a rejected `people=0`, the Hampi resource, and the `plan_trip` prompt. It does not call the language model.
