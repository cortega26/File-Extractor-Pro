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
- **Q-002 (S1 · Architecture)** — Status: *Done*
  - Notes: `ExtractorService` now powers a reusable headless CLI, enabling automation without Tkinter dependencies.
  - Next Action: Document CLI workflows and identify additional service endpoints for automation.
- **Q-003 (S1 · Performance/Concurrency)** — Status: *Done*
  - Notes: Extraction now runs synchronously with a cancellation event, avoiding Tkinter event loop coupling.
  - Next Action: Monitor cancellation responsiveness under heavy filesystem loads.
- **Q-004 (S1 · UX/UI)** — Status: *Done*
  - Notes: Responsive layout profiles adapt widget grids for compact screens and high-DPI scaling.
  - Next Action: Validate the refreshed layout against accessibility heuristics and gather user feedback.
- **Q-005 (S1 · Performance)** — Status: *Done*
  - Notes: Traversal now streams matching files and processes them in a single `os.walk` pass.
  - Next Action: Monitor progress reporting accuracy on very large directory trees.

## Should Have (Severity S2)
- **Q-006 (S2 · Maintainability)** — Status: *Done*
  - Notes: Bulk updates now flow through `Config.update_settings`, ensuring atomic validation and persistence via the typed schema.
  - Next Action: Monitor telemetry for unexpected configuration validation failures.
- **Q-007 (S2 · Performance)** — Status: *Not Started*
  - Notes: Large files buffered fully before streaming to output file.
  - Next Action: Implement chunked write-through to avoid memory spikes.
- **Q-008 (S2 · UX/Performance)** — Status: *Done*
  - Notes: Status queue now bounded with adaptive polling to keep the UI responsive under sustained load.
  - Next Action: Monitor queue saturation metrics during stress runs.

## Nice to Have (Severity S3)
- **Q-009 (S3 · Maintainability)** — Status: *Done*
  - Notes: Logging configuration is now opt-in and supports dependency injection for custom consumers.
  - Next Action: Monitor usage patterns from non-GUI consumers to ensure handler expectations remain consistent.

## Recently Completed
- **Q-001** — Added regression coverage for cancellation queue messaging and reset behaviour.
