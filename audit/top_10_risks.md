# Top 10 Risks Summary

1. **No automated regression coverage (S0, 1–2w)** — Core extraction flow lacks tests, so defects ship unnoticed. Owner: QA Lead.
2. **Monolithic architecture blocks scaling (S1, 1–2w)** — Single file couples GUI and logic; any change risks cascading failures. Owner: Tech Lead.
3. **Asyncio/Tkinter interop unstable (S1, 1–2w)** — Cancellation may hang or crash; prevents reliable long runs. Owner: Backend Lead.
4. **Fixed 700×700 layout breaks accessibility (S1, 1–2d)** — Users on small displays cannot operate the app comfortably. Owner: Front-end Lead.
5. **Double filesystem traversal halves throughput (S1, 1–2d)** — Current performance scales poorly for large repositories. Owner: Backend Lead.
6. **Config schema missing validation (S2, 1–2d)** — Corrupt config leads to undefined behavior without user guidance. Owner: Tech Lead.
7. **Large file buffering spikes memory (S2, ≤2h)** — Memory usage can exceed limits during big-file extraction. Owner: Backend Lead.
8. **Queue polling causes stale progress (S2, ≤2h)** — UI lags under load, eroding user trust. Owner: Front-end Lead.
9. **Logging configured at import time (S3, ≤2h)** — Embedding or testing resets logging unexpectedly. Owner: Tech Lead.
10. **Theme contrast unverified (S1, 1–2d)** — Potential WCAG AA violations expose legal/accessibility risk. Owner: Front-end Lead.

All severities derived from backlog.csv.
