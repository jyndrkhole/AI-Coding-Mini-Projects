# How the pieces fit

The API loads a survey CSV into SQLite, builds one deterministic bundle, and serves that bundle to the dashboard. A separate run sends the bundle through five specialists.

Phase 1 runs the score, voice, and churn specialists together. Phase 2 starts the action planner only after those three finish. Phase 3 writes the leadership brief and checks every stored number, quote, theme, and callback id against the bundle. A failed check is kept. The writer gets one correction pass. If that also fails, the brief is rebuilt from the tools and marked rejected.

The dashboard reads the same calculations. It does not recompute NPS in the browser.

No specialist is allowed to invent a count, a rupee amount, or a customer quotation. Keyword themes and the churn model are code. An optional note can be attached later by a configured model; the claims list stays the numerical source.
