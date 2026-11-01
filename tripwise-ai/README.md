# TripWise AI

A travel advisor that keeps prices, notes, memory, and local tips in different places.

- **SQLite** is the record of destinations, stays, sample prices, users, trips, chats, lasting facts, and planning rules.
- **ChromaDB** holds two collections. `trip_knowledge` is the travel notebook (world knowledge). `trip_episodes` is past trips for one signed-in traveller. Neither collection is the source of prices or bookings.
- **The MCP server** is the only path the advisor uses for `db_lookup`, `list_destinations`, and `compute_trip_cost`. Python does the arithmetic with exact rounding. The model does not invent prices or redo the maths.
- **The host** runs Groq when `GROQ_API_KEY` is set, otherwise OpenAI. It also retrieves notebook passages, runs the catalogue tools, and runs the two budget chains.
- **Long-term memory** belongs to the signed-in traveller. The current chat keeps the last 10 messages. Ending a chat files facts, past trips, and planning rules. Another traveller cannot read them.
- **The Local Guide** is a separate process. The advisor asks it over A2A for things to do, one local food, and a weather note. It does not quote prices. If it is stopped, the advisor says the guide is offline and can still answer costs.

The budget page runs three steps in order: the MCP cost tool, an explanation that must not recompute those numbers, then a GO or NOT YET decision.

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

Startup applies the database migrations, including the traveller memory tables.

In a second terminal, start the Local Guide and leave it running:

```bash
cd backend
source .venv/bin/activate
python -m app.a2a.guide
```

It listens at http://127.0.0.1:9999. `GUIDE_URL` in `.env` points the advisor there.

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173

## Sign in

Chat is stored on the signed-in account. Local demo accounts:

- `traveler@example.com` / `Tripwise#Travel1` (Asha)
- `admin@example.com` / `Tripwise#Admin1`

## Pages

- **Discover** filters the catalogue by audience, season, and sort, and opens a destination with stays, attractions, tips, and nearby places.
- **Advisor** is the chat. Saved conversations stay separate from the starter questions.
- **Budget** shows the tool total, the explanation, and GO or NOT YET. It also has a category planner. Amounts are demonstration estimates, not live fares.
- **Compare** lines up catalogue costs and fit labels. The cheaper option is chosen from the tool totals.
- **Itinerary** builds a day plan from stored stops. Titles can be edited and the plan can be exported as Markdown.
- **Trips** keeps saved trip plans for the signed-in traveller.
- **Profile** renames the account.
- **Admin** is limited to the admin account: knowledge upload, catalogue edits, and user roles.

## Advisor

Sign in, then ask in plain language. `list` reads the catalogue without calling the model. `/plan Hampi 5 2 6000` fills place, people, nights, and budget per person.

A reply ends with a short line such as “Checked the catalogue.” It does not dump the raw tool JSON.

**End chat and save to memory** reads that conversation and keeps what will help a later trip: group size, budget, home city, food needs, a past trip, or a planning rule. The next chat starts clean and the advisor is told what it already remembers, so it should not ask for those facts again. **Forget everything** deletes only that account’s memory. Passwords, card numbers, phone numbers, and ID numbers are not stored.

Questions about things to do, local food, or weather in a month go to the Local Guide. Example: `What should we do in Hampi in December?`

## Try these

- `list`
- `We are 4 friends with ₹12,000 each. Can we do Goa for 3 nights?`
- `/plan Hampi 5 2 6000`
- `Is Manali a good idea in July?`
- `Plan a 5-day family trip to Kerala under ₹60,000.`
- `Suggest destinations near Pune for a 3-day weekend.`
- `What should we do in Hampi in December?`

## Tests

```bash
cd backend
pytest
```

The tests cover the cost checks, the MCP handshake over stdio, catalogue filters, and memory. Memory tests check that a fact can be updated, a duplicate rule is skipped, one traveller cannot see another’s memory, and sensitive details are dropped. The Local Guide test checks stored notes and the offline message. These tests do not call Groq.
