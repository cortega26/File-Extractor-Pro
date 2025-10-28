# Delivery Scoreboard

This scoreboard tracks progress against the audit backlog so future contributors
can quickly see what has been addressed and what remains.

## Legend
- **Status** — `Not Started`, `In Progress`, `Done`, or `Blocked`.
- **Next Action** — concrete step to move the item forward.

## Must Have (Severity S0–S1)
- **Q-001 (S0 · Testing)** — Status: *Done*
  - Notes: Pytest suite now covers extraction flow, progress reporting, and queue cancellation messaging.
  - Next Action: Monitor queue behaviours during future async refactors.
- **Q-002 (S1 · Architecture)** — Status: *Not Started*
  - Notes: Modules remain tightly coupled between UI, config, and processor layers.
  - Next Action: Draft refactoring plan splitting UI and core services.
- **Q-003 (S1 · Performance/Concurrency)** — Status: *Not Started*
  - Notes: Asyncio worker still intertwined with Tkinter thread lifecycle.
  - Next Action: Investigate cancellation behaviour and design a managed runner.
- **Q-004 (S1 · UX/UI)** — Status: *Not Started*
  - Notes: Layout constraints still assume large displays; needs responsive resizing.
  - Next Action: Prototype responsive layout adjustments.
- **Q-005 (S1 · Performance)** — Status: *Not Started*
  - Notes: `os.walk` invoked twice for counting and processing, doubling I/O.
  - Next Action: Profile traversal and design single-pass strategy.

## Should Have (Severity S2)
- **Q-006 (S2 · Maintainability)** — Status: *Not Started*
  - Notes: Configuration lacks schema validation and helpful errors.
  - Next Action: Evaluate pydantic/attrs or lightweight custom validators.
- **Q-007 (S2 · Performance)** — Status: *Not Started*
  - Notes: Large files buffered fully before streaming to output file.
  - Next Action: Implement chunked write-through to avoid memory spikes.
- **Q-008 (S2 · UX/Performance)** — Status: *Done*
  - Notes: Status queue now bounded with adaptive polling to keep the UI responsive under sustained load.
  - Next Action: Monitor queue saturation metrics during stress runs.

## Nice to Have (Severity S3)
- **Q-009 (S3 · Maintainability)** — Status: *Not Started*
  - Notes: Logging config still initializes handlers on import, limiting flexibility.
  - Next Action: Move logging setup to entry point and allow injection.

## Recently Completed
- **Q-001** — Added regression coverage for cancellation queue messaging and reset behaviour.
