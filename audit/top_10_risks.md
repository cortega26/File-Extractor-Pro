# Top 10 Risks Summary

1. **Headless extraction processes zero files by default (S1, ≤2h)** — CLI
   defaults to inclusion mode with no extensions, so automation silently fails.
   Owner: Backend Lead. (Q-101)
2. **Progress UI misrepresents work (S1, 1–2d)** — Progress jumps to 100%
   immediately, undermining trust during long runs. Owner: Front-end Lead. (Q-102)
3. **GUI monolith slows iteration (S1, 1–2w)** — `ui.py` is ~1 000 lines mixing
   layout, theming, and orchestration, increasing regression risk. Owner:
   Front-end Lead. (Q-103)
4. **Type checking cannot gate releases (S1, 1–2w)** — `mypy --strict .` fails
   with 62 errors, so static analysis is ineffective. Owner: Tech Lead. (Q-104)
5. **Large files skipped outright (S2, ≤2h)** — Hard 100 MB ceiling raises
   `MemoryError`, leaving gaps in extraction output. Owner: Backend Lead. (Q-105)
6. **Queue backpressure drops completion messages (S2, 1–2d)** — Full queues may
   evict terminal state payloads, so automation can’t detect completion. Owner:
   Backend Lead. (Q-106)
7. **Keyboard navigation lacks shortcuts (S2, 1–2d)** — No mnemonics or focus
   guidance makes accessibility compliance questionable. Owner: Front-end Lead.
   (Q-107)
8. **No operational telemetry (S2, 1–2d)** — Throughput/latency metrics absent,
   leaving performance tuning guesswork. Owner: Tech Lead. (Q-108)
9. **CLI usage undocumented (S3, ≤2h)** — README omits headless instructions,
   confusing operators. Owner: Product Owner. (Q-109)
10. **Coverage policy unenforced (S3, ≤2h)** — No pytest-cov/thresholds despite
    R3 targets. Owner: QA Lead. (Q-110)

All severities sourced from `backlog.csv`.
